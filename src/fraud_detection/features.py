import pandas as pd

# Only fields plausibly available before a transfer completes.
FEATURES = ["amount", "step", "type_TRANSFER", "type_CASH_OUT", "oldbalanceOrg"]


def make_features(df: pd.DataFrame) -> pd.DataFrame:
    required = {"amount", "step", "type", "oldbalanceOrg"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    x = pd.DataFrame(index=df.index)
    x["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    x["step"] = pd.to_numeric(df["step"], errors="coerce").fillna(0)
    x["type_TRANSFER"] = (df["type"] == "TRANSFER").astype(int)
    x["type_CASH_OUT"] = (df["type"] == "CASH_OUT").astype(int)
    x["oldbalanceOrg"] = pd.to_numeric(df["oldbalanceOrg"], errors="coerce").fillna(0)
    return x[FEATURES]
