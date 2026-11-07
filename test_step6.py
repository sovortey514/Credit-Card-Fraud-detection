"""Verify explainable fraud predictions through the running Flask API."""

import requests


API_URL = "http://localhost:5000/api/v1/predict"

PAYLOAD_SUSPICIOUS = {
    "Time": 7200,
    "Amount": 1250.00,
    "V1": -4.3598,
    "V2": 3.0727,
    "V3": -5.5363,
    "V4": 4.3781,
    "V5": -2.3383,
    "V6": -1.4624,
    "V7": -4.2395,
    "V8": 1.0987,
    "V9": -2.3637,
    "V10": -5.0908,
    "V11": 3.5516,
    "V12": -6.6178,
    "V13": 0.9913,
    "V14": -7.3111,
    "V15": -0.4681,
    "V16": -3.4704,
    "V17": -5.2079,
    "V18": -2.0257,
    "V19": 1.4039,
    "V20": 0.5514,
    "V21": 0.8183,
    "V22": -0.2778,
    "V23": 0.3104,
    "V24": -0.1669,
    "V25": -0.1285,
    "V26": 0.4891,
    "V27": 0.6335,
    "V28": 0.2210,
}


def main() -> None:
    response = requests.post(API_URL, json=PAYLOAD_SUSPICIOUS, timeout=30)
    response.raise_for_status()
    result = response.json()

    print("\n--- API Response with SHAP Explanations ---")
    print(f"Status: {result['status']}")
    print(f"Risk Score: {result['risk_score']}")
    print("Explanations / Feature Drivers:")
    for reason in result.get("reasons", []):
        print(f" - {reason}")


if __name__ == "__main__":
    main()
