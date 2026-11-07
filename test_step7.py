"""Verify SQLite logging, analyst feedback, and retraining safeguards."""

from src.database import init_db, log_transaction, update_analyst_feedback
from src.retrain import check_and_retrain


def main() -> None:
    init_db()
    transaction_id = log_transaction(
        amount=1450.00,
        status="REJECTED",
        decision="FLAGGED_BY_ML",
        risk_score=0.8842,
        reasons=["Feature 'scaled_amount' increased fraud risk"],
    )
    update_analyst_feedback(transaction_id, confirmed_label=1)
    retrained = check_and_retrain(min_new_labels=1)

    print("\n===== STEP 7 VERIFICATION =====")
    print(f"Logged transaction ID: {transaction_id}")
    print(f"Retraining performed: {retrained}")
    print("Database logging and feedback verification completed.")


if __name__ == "__main__":
    main()