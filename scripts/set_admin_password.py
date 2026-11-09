"""Set the password for the seeded TransferGuard administrator."""

import getpass
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.user_database import init_user_db, list_users, set_password


ADMIN_EMAIL = "admin@transferguard.demo"


def main() -> None:
    init_user_db()
    password = getpass.getpass("Enter the new admin password: ")
    confirmation = getpass.getpass("Confirm the new admin password: ")

    if len(password) < 8:
        raise SystemExit("Password must contain at least 8 characters.")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    admin = next((user for user in list_users() if user["email"] == ADMIN_EMAIL), None)
    if not admin:
        raise SystemExit(f"Admin account not found: {ADMIN_EMAIL}")

    if not set_password(admin["id"], password):
        raise SystemExit("Unable to update the admin password.")

    print(f"Admin password updated successfully for {ADMIN_EMAIL}.")


if __name__ == "__main__":
    main()
