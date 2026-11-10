"""End-to-end API tests: real FastAPI app, real trained model, temporary SQLite DB + storage.

Skipped when no trained model is present.
"""
import importlib
import json
import os
import sys

import cv2
import numpy as np
import pandas as pd
import pytest

from ml.utils.config import resolve

MODEL_DIR = "models/custom_cnn/v1"
pytestmark = pytest.mark.skipif(not resolve(f"{MODEL_DIR}/model.keras").exists(), reason="train the custom CNN first")


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("api")
    os.environ.update({
        "SURFACECHECK_DB_URL": f"sqlite:///{(tmp / 'test.db').as_posix()}",
        "SURFACECHECK_STORAGE_DIR": str(tmp / "storage"),
        "SURFACECHECK_MODEL_DIRS": MODEL_DIR,
        "SURFACECHECK_DEFAULT_MODEL": "custom_cnn:v1",
    })
    for m in [m for m in sys.modules if m.startswith("backend")]:
        del sys.modules[m]
    main = importlib.import_module("backend.main")
    from fastapi.testclient import TestClient
    with TestClient(main.app) as c:
        yield c


@pytest.fixture(scope="module")
def test_rows():
    return pd.read_csv(resolve("dataset/splits/test.csv"))


def _upload(client, data: bytes, name="img.png", **form):
    return client.post("/api/inspections", files={"file": (name, data, "image/png")}, data=form)


def test_health(client):
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["models"] == ["custom_cnn:v1"]


def test_single_inspection_has_all_required_fields(client, test_rows):
    row = test_rows.iloc[0]
    r = _upload(client, resolve(row["filepath"]).read_bytes(), name=row["filepath"].split("/")[-1],
                product_id="COIL-001", batch_id="MANUAL-1")
    assert r.status_code == 200, r.text
    d = r.json()
    for key in ("inspection_id", "product_id", "batch_id", "image_reference", "predicted_class", "confidence",
                "model_version", "timestamp", "decision", "review_status", "gradcam_url", "gradcam_caveat"):
        assert d[key] not in (None, ""), key
    assert d["product_id"] == "COIL-001" and d["batch_id"] == "MANUAL-1"
    assert d["model_version"] == "custom_cnn:v1"
    assert abs(sum(d["probabilities"].values()) - 1) < 1e-4
    assert d["input_flags"] == []
    assert client.get(d["gradcam_url"]).status_code == 200
    assert client.get(d["image_url"]).status_code == 200


def test_prediction_and_decision_stored_in_separate_tables(client, test_rows):
    d = _upload(client, resolve(test_rows.iloc[1]["filepath"]).read_bytes()).json()
    from backend.database.models import Decision, Prediction
    from backend.database.session import SessionLocal
    with SessionLocal() as db:
        p = db.query(Prediction).filter_by(inspection_id=d["inspection_id"]).one()
        dec = db.query(Decision).filter_by(inspection_id=d["inspection_id"]).one()
    assert p.predicted_class == d["predicted_class"] and dec.decision == d["decision"]
    assert dec.policy_version == d["policy_version"] and dec.policy_snapshot["class_actions"]


def test_off_contract_inputs_route_to_manual_review(client):
    uniform = cv2.imencode(".png", np.full((200, 200), 120, np.uint8))[1].tobytes()
    d = _upload(client, uniform).json()
    assert d["decision"] == "MANUAL_REVIEW" and d["rule_fired"] == "input_flag"
    big = cv2.imencode(".png", np.random.default_rng(0).integers(0, 255, (400, 640), dtype=np.uint8))[1].tobytes()
    d = _upload(client, big).json()
    assert "resized_from_640x400" in d["input_flags"] and d["decision"] == "MANUAL_REVIEW"


def test_bad_upload_and_unknown_model(client, test_rows):
    assert _upload(client, b"definitely not an image").status_code == 422
    assert _upload(client, resolve(test_rows.iloc[0]["filepath"]).read_bytes(), model="nope:v9").status_code == 400


def test_review_does_not_modify_prediction(client, test_rows):
    d = _upload(client, resolve(test_rows.iloc[2]["filepath"]).read_bytes()).json()
    r = client.post(f"/api/inspections/{d['inspection_id']}/review",
                    json={"reviewer": "QA-7", "final_disposition": "HOLD", "corrected_class": "Scratches", "notes": "t"})
    assert r.status_code == 200, r.text
    after = r.json()
    assert after["review_status"] == "REVIEWED"
    assert after["predicted_class"] == d["predicted_class"] and after["confidence"] == d["confidence"]
    assert after["decision"] == d["decision"]
    assert after["reviews"][-1]["reviewer"] == "QA-7"
    bad = client.post(f"/api/inspections/{d['inspection_id']}/review",
                      json={"reviewer": "x", "final_disposition": "PASS", "corrected_class": "Rust"})
    assert bad.status_code == 422


def _read_sse(text):
    events = []
    for block in text.strip().split("\n\n"):
        lines = dict(l.split(": ", 1) for l in block.splitlines() if ": " in l)
        events.append((lines.get("event"), json.loads(lines.get("data", "{}"))))
    return events


def test_simulated_line_processes_sequentially(client):
    b = client.post("/api/batches/simulate", json={"n_images": 6, "seed": 3, "pacing_ms": 0}).json()
    assert b["n_items"] == 6 and "No camera" in b["notice"]
    events = _read_sse(client.get(f"/api/batches/{b['batch_id']}/run").text)
    kinds = [k for k, _ in events]
    assert kinds[0] == "start" and kinds[-1] == "summary" and kinds.count("inspection") == 6
    seqs = [p["sequence_no"] for k, p in events if k == "inspection"]
    assert seqs == sorted(seqs) == list(range(1, 7))
    summary = events[-1][1]
    assert summary["n_inspected"] == 6 and sum(summary["decision_counts"].values()) == 6
    assert summary["ground_truth_agreement"]["n"] == 6
    detail = client.get(f"/api/batches/{b['batch_id']}").json()
    assert detail["status"] == "completed" and detail["n_done"] == 6
    # running a completed batch again processes nothing new
    again = _read_sse(client.get(f"/api/batches/{b['batch_id']}/run").text)
    assert [k for k, _ in again].count("inspection") == 0


def test_upload_batch_with_one_bad_file_keeps_going(client, test_rows):
    good = resolve(test_rows.iloc[3]["filepath"]).read_bytes()
    files = [("files", ("a.png", good, "image/png")), ("files", ("bad.png", b"xx", "image/png")),
             ("files", ("c.png", good, "image/png"))]
    b = client.post("/api/batches", files=files, data={"product_line": "L1"}).json()
    events = _read_sse(client.get(f"/api/batches/{b['batch_id']}/run").text)
    kinds = [k for k, _ in events]
    assert kinds.count("inspection") == 2 and kinds.count("item_error") == 1
    assert events[-1][1]["n_failed"] == 1


def test_history_filters_analytics_and_exports(client):
    all_ = client.get("/api/inspections", params={"limit": 500}).json()
    assert all_["total"] >= 10
    rev = client.get("/api/inspections", params={"review_status": "REVIEWED"}).json()
    assert rev["total"] >= 1 and all(i["review_status"] == "REVIEWED" for i in rev["items"])
    ov = client.get("/api/analytics/overview").json()
    assert ov["totals"]["inspections"] == all_["total"]
    assert sum(ov["decision_counts"].values()) == all_["total"]
    an = client.get("/api/analytics/defects").json()
    assert an["n"] == all_["total"]
    csv_text = client.get("/api/reports/inspections.csv").text
    assert csv_text.splitlines()[0].startswith("inspection_id,timestamp,product_id")
    assert len(csv_text.strip().splitlines()) == all_["total"] + 1
    iid = all_["items"][0]["inspection_id"]
    assert client.get(f"/api/reports/inspections/{iid}.pdf").content[:4] == b"%PDF"
    bid = client.get("/api/batches").json()[0]["batch_id"]
    assert client.get(f"/api/reports/batches/{bid}.pdf").content[:4] == b"%PDF"


def test_model_endpoints_serve_real_artifacts(client):
    models = client.get("/api/models").json()
    assert models[0]["key"] == "custom_cnn:v1"
    detail = client.get("/api/models/custom_cnn/v1").json()
    assert len(detail["history"]) == detail["train_meta"]["stages"][0]["epochs_run"]
    if detail["evaluation"]:
        assert detail["evaluation"]["test"]["n"] == 270
    assert client.get("/api/policy").json()["version"]
