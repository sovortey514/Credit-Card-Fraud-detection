"""MySQL-backed users, password hashing, sessions, and reset tokens."""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from dotenv import load_dotenv

import mysql.connector
from mysql.connector import Error, IntegrityError

load_dotenv()

ROLE_NAMES = {"admin", "analyst", "customer", "compliance"}


def _settings() -> dict[str, Any]:
    return {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "fraud_detection"),
    }


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return f"pbkdf2_sha256$120000${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, rounds, salt_hex, digest_hex = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds))
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def _connection(database: bool = True):
    settings = _settings()
    if not database:
        settings.pop("database")
    return mysql.connector.connect(**settings)


def init_user_db() -> None:
    settings = _settings()
    database = settings.pop("database")
    with _connection(False) as connection:
        cursor = connection.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.close()
    with _connection(True) as connection:
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(254) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                role ENUM('admin','analyst','customer','compliance') NOT NULL DEFAULT 'analyst',
                active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            ) ENGINE=InnoDB
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_sessions (
                token VARCHAR(128) PRIMARY KEY,
                user_id INT NOT NULL,
                expires_at DATETIME NOT NULL,
                CONSTRAINT fk_session_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                token VARCHAR(128) PRIMARY KEY,
                user_id INT NOT NULL,
                expires_at DATETIME NOT NULL,
                used BOOLEAN NOT NULL DEFAULT FALSE,
                CONSTRAINT fk_reset_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB
        """)
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            now = _now().replace(tzinfo=None)
            demo_users = [
                ("Risk Manager", "admin@transferguard.demo", "admin"),
                ("Fraud Analyst", "analyst@transferguard.demo", "analyst"),
                ("Cardholder Demo", "customer@transferguard.demo", "customer"),
                ("Compliance Officer", "compliance@transferguard.demo", "compliance"),
            ]
            cursor.executemany(
                "INSERT INTO users (name,email,password_hash,role,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s)",
                [(name, email, _hash_password("transfer-demo-2026"), role, now, now) for name, email, role in demo_users],
            )
        connection.commit()
        cursor.close()


def _public(row: tuple) -> dict:
    return {"id": int(row[0]), "name": row[1], "email": row[2], "role": row[4], "active": bool(row[5]), "created_at": row[6].isoformat() if hasattr(row[6], "isoformat") else row[6]}


def list_users() -> list[dict]:
    init_user_db()
    with _connection() as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT id,name,email,password_hash,role,active,created_at FROM users ORDER BY id")
        rows = cursor.fetchall()
        cursor.close()
    return [_public(row) for row in rows]


def authenticate(email: str, password: str):
    init_user_db()
    with _connection() as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT id,name,email,password_hash,role,active,created_at FROM users WHERE email=%s", (email.strip().lower(),))
        row = cursor.fetchone()
        if not row or not row[5] or not _verify_password(password, row[3]):
            return None
        token = secrets.token_urlsafe(32)
        cursor.execute("INSERT INTO auth_sessions (token,user_id,expires_at) VALUES (%s,%s,%s)", (token, row[0], (_now() + timedelta(hours=12)).replace(tzinfo=None)))
        connection.commit()
        cursor.close()
    return _public(row), token


def user_for_token(token: str | None):
    if not token:
        return None
    init_user_db()
    with _connection() as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT u.id,u.name,u.email,u.password_hash,u.role,u.active,u.created_at FROM users u JOIN auth_sessions s ON s.user_id=u.id WHERE s.token=%s AND s.expires_at > UTC_TIMESTAMP() AND u.active=TRUE", (token,))
        row = cursor.fetchone()
        cursor.close()
    return _public(row) if row else None


def revoke_token(token: str | None) -> None:
    if token:
        with _connection() as connection:
            cursor = connection.cursor(); cursor.execute("DELETE FROM auth_sessions WHERE token=%s", (token,)); connection.commit(); cursor.close()


def create_user(name: str, email: str, password: str, role: str) -> dict:
    if role not in ROLE_NAMES: raise ValueError("Invalid role")
    if len(password) < 12: raise ValueError("Password must be at least 12 characters")
    init_user_db(); now = _now().replace(tzinfo=None)
    with _connection() as connection:
        cursor = connection.cursor()
        cursor.execute("INSERT INTO users (name,email,password_hash,role,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s)", (name.strip(), email.strip().lower(), _hash_password(password), role, now, now))
        user_id = cursor.lastrowid; connection.commit(); cursor.execute("SELECT id,name,email,password_hash,role,active,created_at FROM users WHERE id=%s", (user_id,)); row = cursor.fetchone(); cursor.close()
    return _public(row)


def update_user(user_id: int, patch: dict) -> dict:
    allowed = {"name", "email", "role", "active"}; changes = {key: value for key, value in patch.items() if key in allowed}
    if "role" in changes and changes["role"] not in ROLE_NAMES: raise ValueError("Invalid role")
    if not changes: raise ValueError("No valid user fields supplied")
    changes["updated_at"] = _now().replace(tzinfo=None); init_user_db()
    with _connection() as connection:
        cursor = connection.cursor(); assignments = ",".join(f"{key}=%s" for key in changes); cursor.execute(f"UPDATE users SET {assignments} WHERE id=%s", (*changes.values(), user_id))
        if cursor.rowcount == 0: raise ValueError("User not found")
        connection.commit(); cursor.execute("SELECT id,name,email,password_hash,role,active,created_at FROM users WHERE id=%s", (user_id,)); row = cursor.fetchone(); cursor.close()
    return _public(row)


def delete_user(user_id: int) -> None:
    init_user_db()
    with _connection() as connection:
        cursor = connection.cursor(); cursor.execute("DELETE FROM users WHERE id=%s", (user_id,));
        if cursor.rowcount == 0: raise ValueError("User not found")
        connection.commit(); cursor.close()


def set_password(user_id: int, password: str) -> None:
    if len(password) < 12: raise ValueError("Password must be at least 12 characters")
    init_user_db()
    with _connection() as connection:
        cursor = connection.cursor(); cursor.execute("UPDATE users SET password_hash=%s,updated_at=%s WHERE id=%s", (_hash_password(password), _now().replace(tzinfo=None), user_id))
        if cursor.rowcount == 0: raise ValueError("User not found")
        connection.commit(); cursor.close()


def create_reset_token(email: str):
    init_user_db()
    with _connection() as connection:
        cursor = connection.cursor(); cursor.execute("SELECT id FROM users WHERE email=%s AND active=TRUE", (email.strip().lower(),)); row = cursor.fetchone()
        if not row: return None
        token = secrets.token_urlsafe(32); cursor.execute("INSERT INTO password_reset_tokens (token,user_id,expires_at) VALUES (%s,%s,%s)", (token, row[0], (_now()+timedelta(minutes=30)).replace(tzinfo=None))); connection.commit(); cursor.close(); return token


def reset_password(token: str, password: str) -> None:
    if len(password) < 12: raise ValueError("Password must be at least 12 characters")
    with _connection() as connection:
        cursor = connection.cursor(); cursor.execute("SELECT user_id FROM password_reset_tokens WHERE token=%s AND used=FALSE AND expires_at>UTC_TIMESTAMP()", (token,)); row = cursor.fetchone()
        if not row: raise ValueError("Reset token is invalid or expired")
        cursor.execute("UPDATE users SET password_hash=%s,updated_at=%s WHERE id=%s", (_hash_password(password), _now().replace(tzinfo=None), row[0])); cursor.execute("UPDATE password_reset_tokens SET used=TRUE WHERE token=%s", (token,)); cursor.execute("DELETE FROM auth_sessions WHERE user_id=%s", (row[0],)); connection.commit(); cursor.close()