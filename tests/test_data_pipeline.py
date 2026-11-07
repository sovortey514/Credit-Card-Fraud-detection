import pandas as pd

from src.fraud_detection.data_pipeline import load_dataset


def test_load_dataset_keeps_both_fraud_bearing_transaction_types(tmp_path):
    path = tmp_path / "paysim.csv"
    pd.DataFrame([
        {"step": 1, "type": "TRANSFER", "amount": 10, "oldbalanceOrg": 20, "isFraud": 1,
         "newbalanceOrig": 10, "newbalanceDest": 10},
        {"step": 2, "type": "CASH_OUT", "amount": 5, "oldbalanceOrg": 8, "isFraud": 0,
         "newbalanceOrig": 3, "newbalanceDest": 5},
        {"step": 3, "type": "PAYMENT", "amount": 1, "oldbalanceOrg": 2, "isFraud": 0,
         "newbalanceOrig": 1, "newbalanceDest": 1},
    ]).to_csv(path, index=False)
    result = load_dataset(path)
    assert set(result["type"]) == {"TRANSFER", "CASH_OUT"}
    assert "newbalanceDest" not in result.columns
