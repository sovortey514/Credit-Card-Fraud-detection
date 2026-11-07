import pandas as pd

from src.fraud_detection.audit import audit_dataset


def test_audit_records_hash_and_distribution(tmp_path):
    path = tmp_path / "sample.csv"
    pd.DataFrame({
        "amount": [1, 10, 100],
        "type": ["TRANSFER", "CASH_OUT", "PAYMENT"],
        "isFraud": [0, 1, 0],
    }).to_csv(path, index=False)
    result = audit_dataset(path)
    assert len(result["sha256"]) == 64
    assert result["fraud_count"] == 1
    assert "amount_skewness" in result
