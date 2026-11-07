"""Create the fraud_detection MySQL schema and seed demo users."""

from src.user_database import init_user_db


if __name__ == "__main__":
    init_user_db()
    print("MySQL schema initialized successfully.")
    print("Tables: users, auth_sessions, password_reset_tokens")
