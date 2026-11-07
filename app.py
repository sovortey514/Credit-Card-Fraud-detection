"""Flask REST API for the two-tier Credit Card fraud pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from flask import Flask, jsonify, request
from mysql.connector import IntegrityError
from sklearn.preprocessing import RobustScaler

from src.database import init_db, load_transactions, log_transaction, update_analyst_feedback
from src.explainability import FraudExplainer
from src.features import engineer_features_creditcard
from src.rules import evaluate_rules
from src.user_database import authenticate, create_reset_token, create_user, delete_user, init_user_db, list_users, reset_password, revoke_token, set_password, update_user, user_for_token

ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "models" / "catboost_fraud_model.joblib"
DATA_PATH = ROOT / "data" / "raw" / "creditcard.csv"
RISK_THRESHOLD = 0.50

app = Flask(__name__)

if not MODEL_PATH.exists():
    raise FileNotFoundError(f"Trained CatBoost model not found: {MODEL_PATH}")
model = joblib.load(MODEL_PATH)
explainer = FraudExplainer(model)

if not DATA_PATH.exists():
    raise FileNotFoundError(f"Credit Card dataset not found: {DATA_PATH}")
scaler_data = pd.read_csv(DATA_PATH, usecols=["Amount", "Time"])
amount_scaler = RobustScaler().fit(scaler_data[["Amount"]])
time_scaler = RobustScaler().fit(scaler_data[["Time"]])
init_db()
init_user_db()


@app.after_request
def add_cors_headers(response):
    """Allow the local Vite dashboard to call this local API."""
    response.headers["Access-Control-Allow-Origin"] = "http://localhost:5173"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
    return response


def _token() -> str | None:
    return request.headers.get("Authorization", "").removeprefix("Bearer ").strip() or None


def _require_user(roles: set[str] | None = None):
    user = user_for_token(_token())
    if not user:
        return None, (jsonify({"error": "Authentication required"}), 401)
    if roles and user["role"] not in roles:
        return None, (jsonify({"error": "Insufficient permissions"}), 403)
    return user, None


@app.post("/api/v1/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    result = authenticate(str(data.get("email", "")), str(data.get("password", "")))
    if not result:
        return jsonify({"error": "Invalid email, password, or inactive account"}), 401
    user, token = result
    return jsonify({"token": token, "user": user})


@app.post("/api/v1/auth/logout")
def logout():
    revoke_token(_token())
    return jsonify({"status": "logged_out"})


@app.post("/api/v1/auth/forgot-password")
def forgot_password():
    data = request.get_json(silent=True) or {}
    token = create_reset_token(str(data.get("email", "")))
    response = {"status": "If the account exists, a reset token has been created"}
    if token:
        response["reset_token"] = token
        response["development_only"] = True
    return jsonify(response)


@app.post("/api/v1/auth/reset-password")
def reset_password_endpoint():
    data = request.get_json(silent=True) or {}
    try:
        reset_password(str(data.get("token", "")), str(data.get("password", "")))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"status": "password_reset"})


@app.get("/api/v1/users")
def get_users():
    _, error = _require_user({"admin"})
    if error:
        return error
    return jsonify(list_users())


@app.post("/api/v1/users")
def add_user():
    _, error = _require_user({"admin"})
    if error:
        return error
    data = request.get_json(silent=True) or {}
    try:
        user = create_user(str(data.get("name", "")), str(data.get("email", "")), str(data.get("password", "")), str(data.get("role", "analyst")))
        return jsonify(user), 201
    except (ValueError, IntegrityError) as exc:
        return jsonify({"error": str(exc)}), 400


@app.patch("/api/v1/users/<int:user_id>")
def edit_user(user_id: int):
    current, error = _require_user({"admin"})
    if error:
        return error
    data = request.get_json(silent=True) or {}
    if user_id == current["id"] and data.get("active") is False:
        return jsonify({"error": "You cannot deactivate your own account"}), 400
    try:
        return jsonify(update_user(user_id, data))
    except (ValueError, IntegrityError) as exc:
        return jsonify({"error": str(exc)}), 400


@app.delete("/api/v1/users/<int:user_id>")
def remove_user(user_id: int):
    current, error = _require_user({"admin"})
    if error:
        return error
    if user_id == current["id"]:
        return jsonify({"error": "You cannot delete your own account"}), 400
    try:
        delete_user(user_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify({"status": "deleted", "id": user_id})


@app.post("/api/v1/users/<int:user_id>/reset-password")
def admin_reset_password(user_id: int):
    _, error = _require_user({"admin"})
    if error:
        return error
    data = request.get_json(silent=True) or {}
    try:
        set_password(user_id, str(data.get("password", "")))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"status": "password_updated", "id": user_id})

@app.get("/health")
def health():
    return jsonify({"status": "healthy", "model": MODEL_PATH.name})


@app.get("/api/v1/transactions")
def transactions():
    records = load_transactions().to_dict(orient="records")
    for record in records:
        record["reasons"] = json.loads(record["reasons"] or "[]")
    return jsonify(records)


@app.post("/api/v1/transactions/<int:transaction_id>/feedback")
def transaction_feedback(transaction_id: int):
    data = request.get_json(silent=True) or {}
    label = data.get("confirmed_label")
    if label not in (0, 1):
        return jsonify({"error": "confirmed_label must be 0 or 1"}), 400
    update_analyst_feedback(transaction_id, int(label))
    return jsonify({"status": "updated", "transaction_id": transaction_id, "confirmed_label": label})


def _save_prediction(data: dict, result: dict) -> dict:
    result["transaction_id"] = log_transaction(
        amount=float(data.get("Amount", 0)),
        status=result["status"],
        decision=result["decision"],
        risk_score=result["risk_score"],
        reasons=result["reasons"],
    )
    return result


@app.post("/api/v1/predict")
def predict_fraud():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No transaction payload provided"}), 400

    rule_flagged, rule_reasons = evaluate_rules(data)
    if rule_flagged:
        return jsonify(_save_prediction(data, {
            "status": "REJECTED",
            "decision": "FLAGGED_BY_RULES",
            "tier_triggered": "Stage 1 (Rule Engine)",
            "risk_score": 1.0,
            "threshold": RISK_THRESHOLD,
            "reasons": rule_reasons,
            "explanations": [],
        }))

    required_columns = {"Time", "Amount"} | {f"V{i}" for i in range(1, 29)}
    missing = sorted(required_columns - data.keys())
    if missing:
        return jsonify({"error": f"Missing required columns: {missing}"}), 422

    df_features = engineer_features_creditcard(
        pd.DataFrame([data]), amount_scaler=amount_scaler, time_scaler=time_scaler
    ).drop(columns=["Class"], errors="ignore")
    expected_features = getattr(model, "feature_names_", None)
    if expected_features:
        df_features = df_features.reindex(columns=expected_features)

    fraud_prob = float(model.predict_proba(df_features)[0, 1])
    is_fraud_ml = fraud_prob >= RISK_THRESHOLD
    near_threshold = abs(fraud_prob - RISK_THRESHOLD) <= 0.10
    shap_reasons = []
    if is_fraud_ml or near_threshold:
        try:
            shap_reasons = explainer.explain_transaction(df_features, top_n=3)
        except Exception as exc:
            shap_reasons = [f"Explanation unavailable: {type(exc).__name__}"]

    return jsonify(_save_prediction(data, {
        "status": "REJECTED" if is_fraud_ml else "APPROVED",
        "decision": "FLAGGED_BY_ML" if is_fraud_ml else "CLEARED",
        "tier_triggered": "Stage 2 (CatBoost ML Engine)",
        "risk_score": round(fraud_prob, 4),
        "threshold": RISK_THRESHOLD,
        "reasons": shap_reasons if is_fraud_ml else ["NORMAL_TRANSACTION_PATTERN"],
        "explanations": shap_reasons if near_threshold else [],
    }))


if __name__ == "__main__":
    print("Starting Hybrid Fraud Detection API on http://localhost:5000 ...")
    app.run(host="0.0.0.0", port=5000, debug=False)
