import argparse
import time
import pandas as pd
import requests


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="data/raw/paysim.csv")
    p.add_argument("--limit", type=int, default=30)
    p.add_argument("--delay", type=float, default=0.5)
    a = p.parse_args()
    df = pd.read_csv(a.data)
    df = df[df.type.isin(["TRANSFER", "CASH_OUT"])].sort_values("step").head(a.limit)
    for idx, row in df.iterrows():
        tx = {
            "transaction_id": str(idx),
            "step": int(row.step),
            "type": str(row.type),
            "amount": float(row.amount),
            "oldbalanceOrg": float(row.oldbalanceOrg),
        }
        try:
            res = requests.post("http://127.0.0.1:8000/predict", json=tx, timeout=10)
            res.raise_for_status()
            print(res.json())
        except requests.RequestException as e:
            print("API error:", e)
            break
        time.sleep(a.delay)


if __name__ == "__main__":
    main()
