"""Protocol and metric checks use synthetic data, never the research holdout."""

import json

import numpy as np
import pandas as pd
import pytest

from scripts import evaluate_frozen_creditcard as evaluation
from scripts.evaluate_frozen_creditcard import evaluate, run


def test_metrics_use_legitimate_denominator_and_inclusive_threshold():
    metrics = evaluate(np.array([0, 0, 0, 1, 1]), np.array([0.1, 0.2, 0.5, 0.5, 0.9]), 0.5)
    assert (metrics["tn"], metrics["fp"], metrics["fn"], metrics["tp"]) == (2, 1, 0, 2)
    assert metrics["false_alarms_per_1000_legitimate"] == pytest.approx(1000 / 3)
    assert metrics["false_alarms_per_1000_all"] == 200
    assert metrics["recall"] == 1
    assert metrics["f1"] == pytest.approx(0.8)
    assert metrics["pr_auc_ap"] == pytest.approx(5 / 6)
    assert metrics["roc_auc"] == pytest.approx(11 / 12)


def test_no_alerts_has_zero_f1():
    metrics = evaluate(np.array([0, 1]), np.array([0.1, 0.2]), 0.9)
    assert metrics["f1"] == metrics["recall"] == metrics["precision"] == 0


@pytest.mark.parametrize("scores", [[float("nan"), 0.5], [0.1, 1.1]])
def test_rejects_invalid_scores(scores):
    with pytest.raises(ValueError, match="finite probabilities"):
        evaluate(np.array([0, 1]), np.array(scores), 0.5)


def test_repeat_run_stops_before_reading_data(tmp_path):
    (tmp_path / "reports/final").mkdir(parents=True)
    with pytest.raises(FileExistsError, match="Do not rescore"):
        run(tmp_path)


def test_single_pass_writes_reusable_outputs_and_hashes(tmp_path, monkeypatch):
    data = tmp_path / "data/processed"
    data.mkdir(parents=True)
    (tmp_path / "reports").mkdir()
    splits = {"train": {"max_time": 1}, "validation": {"min_time": 2, "max_time": 3},
              "test": {"rows": 4, "fraud_count": 2, "min_time": 4, "max_time": 7}}
    (data / "creditcard_split_metadata.json").write_text(json.dumps({"splits": splits, "scaler_fit_split": "train"}))
    (data / "creditcard_leakage_audit.json").write_text(json.dumps({"split_order_check": {"ordered": True}}))
    pd.DataFrame({"Time": [4, 5, 6, 7], "Class": [0, 0, 1, 1], "x": [0.1, 0.5, 0.5, 0.9]}).to_parquet(data / "creditcard_test_features.parquet")
    calls = []

    class FrozenModel:
        classes_ = np.array([0, 1])

        def predict_proba(self, frame):
            # The freeze record must exist before any prediction.
            manifest = json.loads((tmp_path / "reports/final/frozen_manifest.json").read_text())
            assert manifest["models"][0]["threshold"] == 0.5
            calls.append(len(frame))
            scores = frame["x"].to_numpy()
            return np.column_stack([1 - scores, scores])

    specs = [{"model": "synthetic", "artifact": "synthetic.joblib", "threshold": 0.5,
              "threshold_source": "saved_validation_calibration"}]
    monkeypatch.setattr(evaluation, "frozen_spec", lambda root: (specs, [data / "creditcard_test_features.parquet"]))
    monkeypatch.setattr(evaluation.joblib, "load", lambda path: {"model": FrozenModel(), "features": ["x"]})
    result = run(tmp_path)
    assert calls == [4]
    assert result["models"][0]["tp"] == 2
    output = tmp_path / "reports/final"
    with np.load(output / "predictions.npz") as saved:
        assert saved["synthetic"].tolist() == [0.1, 0.5, 0.5, 0.9]
    receipt = json.loads((output / "receipt.json").read_text())
    assert receipt["status"] == "complete"
    for name, digest in receipt["output_sha256"].items():
        assert evaluation.file_hash(output / name) == digest
    with pytest.raises(FileExistsError):
        run(tmp_path)
    assert calls == [4]
