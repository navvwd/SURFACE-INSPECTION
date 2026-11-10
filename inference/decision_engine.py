"""Configurable inspection decision engine.

Turns a model Prediction into an inspection *candidate* decision:
    PASS_CANDIDATE | REJECT_CANDIDATE | MANUAL_REVIEW

Rules are evaluated in order; the first that fires determines the decision:
    1. input_flag            input deviated from the training contract  -> MANUAL_REVIEW
    2. low_confidence        confidence < min_confidence                 -> MANUAL_REVIEW
    3. ambiguous_top2        top1 - top2 < min_margin                    -> MANUAL_REVIEW
    4. high_entropy          normalised entropy > max                    -> MANUAL_REVIEW
    5. unknown_class         class missing from policy                   -> MANUAL_REVIEW
    6. class_policy:<action>
         reject  -> REJECT_CANDIDATE only if confidence >= reject_min_confidence,
                    else MANUAL_REVIEW (rule "reject_needs_higher_confidence")
         review  -> MANUAL_REVIEW
         accept  -> PASS_CANDIDATE

The decision is stored separately from the prediction (database table `decisions`), together with
the rule that fired and the policy version, so a policy change never rewrites model outputs.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

PASS, REJECT, REVIEW = "PASS_CANDIDATE", "REJECT_CANDIDATE", "MANUAL_REVIEW"
ACTIONS = {"reject", "review", "accept"}


@dataclass(frozen=True)
class DecisionPolicy:
    version: str
    class_actions: dict
    min_confidence: float
    min_margin: float
    max_normalized_entropy: float
    reject_min_confidence: float
    input_flags_require_review: bool = True

    @classmethod
    def from_dict(cls, d: dict) -> "DecisionPolicy":
        g = d["uncertainty_gates"]
        p = cls(version=str(d["policy_version"]), class_actions=dict(d["class_actions"]),
                min_confidence=float(g["min_confidence"]), min_margin=float(g["min_margin"]),
                max_normalized_entropy=float(g["max_normalized_entropy"]),
                reject_min_confidence=float(d["reject_min_confidence"]),
                input_flags_require_review=bool(d.get("input_flags_require_review", True)))
        p.validate()
        return p

    @classmethod
    def from_yaml(cls, path: str | Path) -> "DecisionPolicy":
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(yaml.safe_load(f))

    def validate(self, classes: list[str] | None = None) -> None:
        bad = {c: a for c, a in self.class_actions.items() if a not in ACTIONS}
        if bad:
            raise ValueError(f"Invalid class actions {bad}; allowed: {sorted(ACTIONS)}")
        for name in ("min_confidence", "min_margin", "max_normalized_entropy", "reject_min_confidence"):
            v = getattr(self, name)
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name}={v} must be within [0, 1]")
        if self.reject_min_confidence < self.min_confidence:
            raise ValueError("reject_min_confidence must be >= min_confidence")
        if classes is not None:
            missing = set(classes) - set(self.class_actions)
            if missing:
                raise ValueError(f"Policy has no action for classes: {sorted(missing)}")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Decision:
    decision: str
    rule_fired: str
    reasons: list[str] = field(default_factory=list)
    policy_version: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class DecisionEngine:
    def __init__(self, policy: DecisionPolicy):
        self.policy = policy

    def decide(self, predicted_class: str, confidence: float, margin: float,
               normalized_entropy: float, input_flags: list[str] | None = None) -> Decision:
        p = self.policy
        d = lambda dec, rule, *why: Decision(dec, rule, list(why), p.version)  # noqa: E731

        if input_flags and p.input_flags_require_review:
            return d(REVIEW, "input_flag", f"Input deviates from training data: {', '.join(input_flags)}")
        if confidence < p.min_confidence:
            return d(REVIEW, "low_confidence", f"Confidence {confidence:.3f} < {p.min_confidence}")
        if margin < p.min_margin:
            return d(REVIEW, "ambiguous_top2", f"Top-1/top-2 margin {margin:.3f} < {p.min_margin}")
        if normalized_entropy > p.max_normalized_entropy:
            return d(REVIEW, "high_entropy",
                     f"Normalised entropy {normalized_entropy:.3f} > {p.max_normalized_entropy}")
        action = p.class_actions.get(predicted_class)
        if action is None:
            return d(REVIEW, "unknown_class", f"No policy action for class '{predicted_class}'")
        if action == "reject":
            if confidence < p.reject_min_confidence:
                return d(REVIEW, "reject_needs_higher_confidence",
                         f"'{predicted_class}' is a reject class but confidence {confidence:.3f} "
                         f"< {p.reject_min_confidence}")
            return d(REJECT, "class_policy:reject",
                     f"'{predicted_class}' is configured as reject; prediction passed all reliability gates")
        if action == "review":
            return d(REVIEW, "class_policy:review", f"'{predicted_class}' is configured for human review")
        return d(PASS, "class_policy:accept",
                 f"'{predicted_class}' is configured as acceptable; prediction passed all reliability gates")

    def decide_prediction(self, pred) -> Decision:
        return self.decide(pred.predicted_class, pred.confidence, pred.margin,
                           pred.normalized_entropy, pred.input_flags)
