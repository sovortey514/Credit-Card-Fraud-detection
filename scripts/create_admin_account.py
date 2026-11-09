"""Create or update the requested administrator account."""

import getpass
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.user_database import _connection, init_user_db, list_users, set_password


ADMIN_EMAIL = "admin@transferguard"


def main() -> None:
    init_user_db()
    password = getpass.getpass("Enter password for admin@transferguard: ")
    confirmation = getpass.getpass("Confirm password: ")
    if len(password) < 8:
        raise SystemExit("Password must contain at least 8 characters.")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    users = list_users()
    existing = next((user for user in users if user["email"] == ADMIN_EMAIL), None)
    if existing:
        set_password(existing["id"], password)
        print("Administrator password updated.")
        return

    configured_admin = next((user for user in users if user.get("role") in {"admin", "administrator", "risk_manager", "Risk Manager", "Administrator"}), None)
    if not configured_admin:
        raise SystemExit("No existing administrator role was found in the database.")
    set_password(configured_admin["id"], password)
    with _connection(True) as connection:
        cursor = connection.cursor()
        cursor.execute("UPDATE users SET email = %s WHERE id = %s", (ADMIN_EMAIL, configured_admin["id"]))
        connection.commit()
    print("Administrator email and password updated.")


if __name__ == "__main__":
    main()
