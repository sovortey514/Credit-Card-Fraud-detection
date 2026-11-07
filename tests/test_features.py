import pandas as pd
from src.fraud_detection.features import make_features, FEATURES


def test_features_use_pretransfer_fields_only():
    df = pd.DataFrame(
        [
            {
                "step": 1,
                "type": "TRANSFER",
                "amount": 100,
                "oldbalanceOrg": 200,
                "newbalanceOrig": 100,
                "isFraud": 1,
            }
        ]
    )
    x = make_features(df)
    assert list(x.columns) == FEATURES
    assert "newbalanceOrig" not in x.columns
    assert "isFraud" not in x.columns
    assert x.iloc[0]["type_TRANSFER"] == 1
