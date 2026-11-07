"""Verify Stage 1 rules and Stage 2 ML scoring for the Flask API."""

from __future__ import annotations

from app import app


PAYLOAD_NORMAL = {
    "Time": 3600,
    "Amount": 45.50,
    "V1": -1.3598,
    "V2": -0.0727,
    "V3": 2.5363,
    "V4": 1.3781,
    "V5": -0.3383,
    "V6": 0.4624,
    "V7": 0.2395,
    "V8": 0.0987,
    "V9": 0.3637,
    "V10": 0.0908,
    "V11": -0.5516,
    "V12": -0.6178,
    "V13": -0.9913,
    "V14": -0.3111,
    "V15": 1.4681,
    "V16": -0.4704,
    "V17": 0.2079,
    "V18": 0.0257,
    "V19": 0.4039,
    "V20": 0.2514,
    "V21": -0.0183,
    "V22": 0.2778,
    "V23": -0.1104,
    "V24": 0.0669,
    "V25": 0.1285,
    "V26": -0.1891,
    "V27": 0.1335,
    "V28": -0.0210,
}

PAYLOAD_RULE_FLAG = {**PAYLOAD_NORMAL, "Amount": 7500.00}


def main() -> None:
    client = app.test_client()

    print("Testing Normal Transaction...")
    normal_response = client.post("/api/v1/predict", json=PAYLOAD_NORMAL)
    print("Response:", normal_response.get_json())
    assert normal_response.status_code == 200
    assert normal_response.get_json()["tier_triggered"].startswith("Stage 2")

    print("\nTesting Rule-Flagged Transaction...")
    rule_response = client.post("/api/v1/predict", json=PAYLOAD_RULE_FLAG)
    print("Response:", rule_response.get_json())
    assert rule_response.status_code == 200
    assert rule_response.get_json()["decision"] == "FLAGGED_BY_RULES"
    assert "CRITICAL_HIGH_AMOUNT" in rule_response.get_json()["reasons"]

    print("\nStep 5 verification passed.")


if __name__ == "__main__":
    main()
