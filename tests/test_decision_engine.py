import pytest

from inference.decision_engine import PASS, REJECT, REVIEW, DecisionEngine, DecisionPolicy
from ml.utils.config import load_config, resolve

POLICY = {
    "policy_version": "test",
    "class_actions": {"A": "reject", "B": "review", "C": "accept"},
    "uncertainty_gates": {"min_confidence": 0.8, "min_margin": 0.3, "max_normalized_entropy": 0.5},
    "reject_min_confidence": 0.9,
}


@pytest.fixture
def engine():
    return DecisionEngine(DecisionPolicy.from_dict(POLICY))


def test_confident_reject_class_rejects(engine):
    d = engine.decide("A", 0.97, 0.95, 0.05)
    assert (d.decision, d.rule_fired) == (REJECT, "class_policy:reject")


def test_reject_class_below_reject_bar_goes_to_review(engine):
    d = engine.decide("A", 0.85, 0.75, 0.2)
    assert (d.decision, d.rule_fired) == (REVIEW, "reject_needs_higher_confidence")


def test_accept_class_passes(engine):
    assert engine.decide("C", 0.95, 0.9, 0.1).decision == PASS


def test_review_class_always_review(engine):
    assert engine.decide("B", 0.999, 0.99, 0.0).rule_fired == "class_policy:review"


@pytest.mark.parametrize("conf,margin,ent,rule", [
    (0.79, 0.7, 0.1, "low_confidence"),
    (0.85, 0.2, 0.1, "ambiguous_top2"),
    (0.85, 0.7, 0.6, "high_entropy"),
])
def test_uncertainty_gates_route_to_review(engine, conf, margin, ent, rule):
    d = engine.decide("A", conf, margin, ent)
    assert (d.decision, d.rule_fired) == (REVIEW, rule)


def test_low_confidence_never_rejects_even_reject_class(engine):
    """Requirement: no automatic rejection based on an arbitrary confidence threshold alone."""
    for conf in (0.1, 0.5, 0.79):
        assert engine.decide("A", conf, 0.5, 0.3).decision == REVIEW


def test_high_confidence_alone_cannot_reject_accept_class(engine):
    assert engine.decide("C", 0.999, 0.99, 0.0).decision == PASS


def test_input_flags_take_priority(engine):
    d = engine.decide("A", 0.99, 0.98, 0.01, ["resized_from_640x480"])
    assert (d.decision, d.rule_fired) == (REVIEW, "input_flag")


def test_unknown_class_reviews(engine):
    assert engine.decide("Z", 0.99, 0.98, 0.01).rule_fired == "unknown_class"


def test_policy_version_recorded(engine):
    assert engine.decide("C", 0.95, 0.9, 0.1).policy_version == "test"


@pytest.mark.parametrize("patch", [
    {"class_actions": {"A": "destroy"}},
    {"reject_min_confidence": 0.5},
    {"uncertainty_gates": {"min_confidence": 1.5, "min_margin": 0.3, "max_normalized_entropy": 0.5}},
])
def test_invalid_policies_rejected(patch):
    with pytest.raises(ValueError):
        DecisionPolicy.from_dict({**POLICY, **patch})


def test_project_policy_covers_all_dataset_classes():
    classes = load_config("configs/data.yaml")["dataset"]["classes"]
    DecisionPolicy.from_yaml(resolve("configs/decision_policy.yaml")).validate(classes)
