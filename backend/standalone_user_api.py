"""Standalone JWT/RBAC user-management API.

This service is deliberately independent from the frontend and the legacy
``backend.user_api`` service. It uses the project MySQL database with isolated
``auth_*`` tables, Argon2 passwords,
short-lived JWT access tokens, rotating refresh tokens, RBAC, account
lifecycle endpoints, reset tokens, login lockout, and audit logs.

Run:
    uvicorn backend.standalone_user_api:app --host 127.0.0.1 --port 8001

Production settings:
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE,
    AUTH_JWT_SECRET, AUTH_BOOTSTRAP_EMAIL,
    AUTH_BOOTSTRAP_PASSWORD, AUTH_ACCESS_TOKEN_MINUTES,
    AUTH_REFRESH_TOKEN_DAYS, AUTH_BOOTSTRAP_ROLE,
    AUTH_ALLOW_PUBLIC_REGISTRATION
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Callable

import jwt
import mysql.connector
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from dotenv import load_dotenv


load_dotenv()
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "fraud_detection")
JWT_SECRET = os.getenv("AUTH_JWT_SECRET", "development-only-change-me")
ACCESS_MINUTES = int(os.getenv("AUTH_ACCESS_TOKEN_MINUTES", "15"))
REFRESH_DAYS = int(os.getenv("AUTH_REFRESH_TOKEN_DAYS", "7"))
RESET_MINUTES = int(os.getenv("AUTH_PASSWORD_RESET_MINUTES", "30"))
MAX_LOGIN_ATTEMPTS = int(os.getenv("AUTH_LOGIN_MAX_ATTEMPTS", "5"))
LOCK_MINUTES = int(os.getenv("AUTH_LOGIN_LOCK_MINUTES", "15"))
ALLOW_PUBLIC_REGISTRATION = os.getenv("AUTH_ALLOW_PUBLIC_REGISTRATION", "false").lower() in {"1", "true", "yes", "on"}
hash_password = PasswordHasher()
ROLES = {"super_admin", "admin", "user"}
ROLE_PERMISSIONS = {
    "super_admin": {"create", "read", "update", "delete"},
    "admin": {"create", "read", "update", "delete"},
    "user": {"read"},
}
bearer_scheme = HTTPBearer(auto_error=False)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp() -> str:
    return utc_now().isoformat()


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class MySQLCursor:
    def __init__(self, cursor: Any):
        self._cursor = cursor

    @property
    def lastrowid(self) -> int | None:
        return self._cursor.lastrowid

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    def fetchone(self) -> dict[str, Any] | None:
        return self._cursor.fetchone()

    def fetchall(self) -> list[dict[str, Any]]:
        return self._cursor.fetchall()

    def close(self) -> None:
        self._cursor.close()


class MySQLConnection:
    def __init__(self, include_database: bool = True):
        settings: dict[str, Any] = {
            "host": MYSQL_HOST,
            "port": MYSQL_PORT,
            "user": MYSQL_USER,
            "password": MYSQL_PASSWORD,
        }
        if include_database:
            settings["database"] = MYSQL_DATABASE
        self._connection = mysql.connector.connect(**settings)

    def __enter__(self) -> "MySQLConnection":
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        if exc_type:
            self._connection.rollback()
        else:
            self._connection.commit()
        self._connection.close()

    def execute(self, sql: str, values: tuple[Any, ...] | list[Any] = ()) -> MySQLCursor:
        sql = re.sub(r"\busers\b", "auth_users", sql, flags=re.IGNORECASE)
        sql = re.sub(r"\brefresh_tokens\b", "auth_refresh_tokens", sql, flags=re.IGNORECASE)
        sql = re.sub(r"\brevoked_access_tokens\b", "auth_revoked_access_tokens", sql, flags=re.IGNORECASE)
        sql = re.sub(r"\bpassword_reset_tokens\b", "auth_password_reset_tokens", sql, flags=re.IGNORECASE)
        sql = re.sub(r"\baudit_logs\b", "auth_audit_logs", sql, flags=re.IGNORECASE)
        sql = sql.replace("INSERT OR REPLACE", "REPLACE")
        cursor = self._connection.cursor(dictionary=True)
        cursor.execute(sql.replace("?", "%s"), tuple(values))
        return MySQLCursor(cursor)

    def executescript(self, statements: str) -> None:
        for statement in statements.split(";"):
            statement = statement.strip()
            if statement:
                self.execute(statement)


def connection(include_database: bool = True) -> MySQLConnection:
    return MySQLConnection(include_database)


def init_db() -> None:
    with connection(False) as conn:
        conn.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    with connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS auth_users (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(120) NOT NULL,
                email VARCHAR(254) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                role ENUM('super_admin','admin','user') NOT NULL DEFAULT 'user',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                failed_attempts INT NOT NULL DEFAULT 0,
                locked_until VARCHAR(40),
                created_at VARCHAR(40) NOT NULL,
                updated_at VARCHAR(40) NOT NULL,
                last_login_at VARCHAR(40)
            ) ENGINE=InnoDB;
            CREATE TABLE IF NOT EXISTS auth_refresh_tokens (
                token_hash CHAR(64) PRIMARY KEY,
                user_id BIGINT NOT NULL,
                jti VARCHAR(100) NOT NULL UNIQUE,
                expires_at VARCHAR(40) NOT NULL,
                revoked_at VARCHAR(40),
                created_at VARCHAR(40) NOT NULL,
                CONSTRAINT fk_auth_refresh_user FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB;
            CREATE TABLE IF NOT EXISTS auth_revoked_access_tokens (
                jti VARCHAR(100) PRIMARY KEY,
                expires_at VARCHAR(40) NOT NULL,
                revoked_at VARCHAR(40) NOT NULL
            ) ENGINE=InnoDB;
            CREATE TABLE IF NOT EXISTS auth_password_reset_tokens (
                token_hash CHAR(64) PRIMARY KEY,
                user_id BIGINT NOT NULL,
                expires_at VARCHAR(40) NOT NULL,
                used_at VARCHAR(40),
                created_at VARCHAR(40) NOT NULL,
                CONSTRAINT fk_auth_reset_user FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB;
            CREATE TABLE IF NOT EXISTS auth_audit_logs (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                actor_user_id BIGINT,
                action VARCHAR(100) NOT NULL,
                target_user_id BIGINT,
                metadata TEXT,
                created_at VARCHAR(40) NOT NULL,
                CONSTRAINT fk_auth_audit_actor FOREIGN KEY (actor_user_id) REFERENCES auth_users(id) ON DELETE SET NULL
            ) ENGINE=InnoDB;
            """
        )
        email = os.getenv("AUTH_BOOTSTRAP_EMAIL", "").strip().lower()
        password = os.getenv("AUTH_BOOTSTRAP_PASSWORD", "")
        bootstrap_role = os.getenv("AUTH_BOOTSTRAP_ROLE", "super_admin").strip().lower()
        if bootstrap_role not in ROLES:
            raise RuntimeError("AUTH_BOOTSTRAP_ROLE must be super_admin, admin, or user")
        if email and password and not conn.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            conn.execute(
                "INSERT INTO users(name,email,password_hash,role,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                (os.getenv("AUTH_BOOTSTRAP_NAME", "Super Administrator"), email, hash_password.hash(password), bootstrap_role, timestamp(), timestamp()),
            )


def row_user(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {"id": row["id"], "name": row["name"], "email": row["email"], "role": row["role"], "is_active": bool(row["is_active"]), "created_at": row["created_at"], "updated_at": row["updated_at"], "last_login_at": row["last_login_at"]}


def get_user(user_id: int) -> dict[str, Any] | None:
    with connection() as conn:
        return conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()


def find_email(email: str) -> dict[str, Any] | None:
    with connection() as conn:
        return conn.execute("SELECT * FROM users WHERE email=?", (email.strip().lower(),)).fetchone()


def write_audit(actor: int | None, action: str, target: int | None = None, metadata: str = "") -> None:
    with connection() as conn:
        conn.execute("INSERT INTO audit_logs(actor_user_id,action,target_user_id,metadata,created_at) VALUES(?,?,?,?,?)", (actor, action, target, metadata, timestamp()))


def issue_token(user: dict[str, Any], kind: str, lifetime: timedelta) -> tuple[str, str, datetime]:
    jti = secrets.token_urlsafe(18)
    expires = utc_now() + lifetime
    payload = {"sub": str(user["id"]), "role": user["role"], "type": kind, "jti": jti, "iat": utc_now(), "exp": expires}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256"), jti, expires


def authorize(authorization: str | None) -> tuple[dict[str, Any], str]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Bearer access token required")
    raw = authorization[7:].strip()
    try:
        payload = jwt.decode(raw, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError as error:
        raise HTTPException(401, "Invalid or expired access token") from error
    if payload.get("type") != "access" or not payload.get("sub") or not payload.get("jti"):
        raise HTTPException(401, "Invalid access token")
    with connection() as conn:
        if conn.execute("SELECT 1 FROM revoked_access_tokens WHERE jti=?", (payload["jti"],)).fetchone():
            raise HTTPException(401, "Access token has been revoked")
    user = row_user(get_user(int(payload["sub"])))
    if not user or not user["is_active"]:
        raise HTTPException(401, "User is inactive or no longer exists")
    return user, payload["jti"]


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)] = None,
) -> dict[str, Any]:
    authorization = f"Bearer {credentials.credentials}" if credentials else None
    return authorize(authorization)[0]


def permission(name: str) -> Callable[..., dict[str, Any]]:
    def dependency(user: Annotated[dict[str, Any], Depends(current_user)]) -> dict[str, Any]:
        if name not in ROLE_PERMISSIONS[user["role"]]:
            raise HTTPException(403, f"Permission required: {name}")
        return user
    return dependency


User = Annotated[dict[str, Any], Depends(current_user)]
CanCreate = Annotated[dict[str, Any], Depends(permission("create"))]
CanRead = Annotated[dict[str, Any], Depends(permission("read"))]
CanUpdate = Annotated[dict[str, Any], Depends(permission("update"))]
CanDelete = Annotated[dict[str, Any], Depends(permission("delete"))]


def admin_only(user: User) -> dict[str, Any]:
    if user["role"] not in {"super_admin", "admin"}:
        raise HTTPException(403, "Administrator access required")
    return user


CanManageUsers = Annotated[dict[str, Any], Depends(admin_only)]


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Register(APIModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=200)


class Login(APIModel):
    email: str
    password: str


class Refresh(APIModel):
    refresh_token: str = Field(min_length=20)


class Password(APIModel):
    password: str = Field(min_length=12, max_length=200)


class ChangePassword(APIModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=12, max_length=200)


class ForgotPassword(APIModel):
    email: str = Field(min_length=5, max_length=254)


class Reset(Password):
    token: str = Field(min_length=20)


class ManagedUser(Register):
    role: str = Field(default="user", pattern="^(super_admin|admin|user)$")


class UserPatch(APIModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    email: str | None = Field(default=None, min_length=5, max_length=254)
    role: str | None = Field(default=None, pattern="^(super_admin|admin|user)$")
    is_active: bool | None = None


class ProfilePatch(APIModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    email: str | None = Field(default=None, min_length=5, max_length=254)


app = FastAPI(title="Standalone User Management API", version="1.0.0", description="JWT authentication, Argon2 passwords, RBAC, account management, and audit logs")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
        "http://127.0.0.1:8001",
        "http://localhost:8001",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "standalone-user-api"}


@app.post("/api/v1/auth/register", status_code=201)
def register(payload: Register) -> dict[str, Any]:
    if not ALLOW_PUBLIC_REGISTRATION:
        raise HTTPException(403, "Public registration is disabled. Ask an administrator to create your account.")
    try:
        with connection() as conn:
            user_id = conn.execute("INSERT INTO users(name,email,password_hash,role,created_at,updated_at) VALUES(?,?,?,?,?,?)", (payload.name.strip(), payload.email.strip().lower(), hash_password.hash(payload.password), "user", timestamp(), timestamp())).lastrowid
    except mysql.connector.IntegrityError as error:
        raise HTTPException(409, "Email address is already registered") from error
    write_audit(None, "user_registered", user_id)
    return {"user": row_user(get_user(user_id))}


@app.post("/api/v1/auth/login")
def login(payload: Login) -> dict[str, Any]:
    row = find_email(payload.email)
    if not row:
        raise HTTPException(401, "Invalid email or password")
    locked = datetime.fromisoformat(row["locked_until"]) if row["locked_until"] else None
    if locked and locked > utc_now():
        raise HTTPException(423, "Account temporarily locked after repeated failed logins")
    if not row["is_active"]:
        raise HTTPException(403, "Account is deactivated")
    try:
        valid = hash_password.verify(row["password_hash"], payload.password)
    except (InvalidHashError, VerifyMismatchError):
        valid = False
    if not valid:
        attempts = row["failed_attempts"] + 1
        locked_until = (utc_now() + timedelta(minutes=LOCK_MINUTES)).isoformat() if attempts >= MAX_LOGIN_ATTEMPTS else None
        with connection() as conn:
            conn.execute("UPDATE users SET failed_attempts=?,locked_until=?,updated_at=? WHERE id=?", (attempts, locked_until, timestamp(), row["id"]))
        write_audit(row["id"], "login_failed", row["id"])
        raise HTTPException(401, "Invalid email or password")
    with connection() as conn:
        conn.execute("UPDATE users SET failed_attempts=0,locked_until=NULL,last_login_at=?,updated_at=? WHERE id=?", (timestamp(), timestamp(), row["id"]))
    user = row_user(get_user(row["id"]))
    access, _, access_expiry = issue_token(user, "access", timedelta(minutes=ACCESS_MINUTES))
    refresh, refresh_jti, refresh_expiry = issue_token(user, "refresh", timedelta(days=REFRESH_DAYS))
    with connection() as conn:
        conn.execute("INSERT INTO refresh_tokens(token_hash,user_id,jti,expires_at,created_at) VALUES(?,?,?,?,?)", (digest(refresh), row["id"], refresh_jti, refresh_expiry.isoformat(), timestamp()))
    write_audit(row["id"], "login_success", row["id"])
    return {"token_type": "bearer", "access_token": access, "refresh_token": refresh, "expires_in": ACCESS_MINUTES * 60, "user": user}


@app.post("/api/v1/auth/refresh")
def refresh(payload: Refresh) -> dict[str, Any]:
    try:
        claims = jwt.decode(payload.refresh_token, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError as error:
        raise HTTPException(401, "Invalid or expired refresh token") from error
    if claims.get("type") != "refresh":
        raise HTTPException(401, "Invalid refresh token")
    with connection() as conn:
        stored = conn.execute("SELECT * FROM refresh_tokens WHERE token_hash=? AND jti=? AND revoked_at IS NULL", (digest(payload.refresh_token), claims.get("jti"))).fetchone()
        if not stored:
            raise HTTPException(401, "Refresh token has been revoked")
        conn.execute("UPDATE refresh_tokens SET revoked_at=? WHERE token_hash=?", (timestamp(), digest(payload.refresh_token)))
    user = row_user(get_user(int(claims["sub"])))
    if not user or not user["is_active"]:
        raise HTTPException(401, "User is inactive or no longer exists")
    access, _, _ = issue_token(user, "access", timedelta(minutes=ACCESS_MINUTES))
    new_refresh, refresh_jti, refresh_expiry = issue_token(user, "refresh", timedelta(days=REFRESH_DAYS))
    with connection() as conn:
        conn.execute("INSERT INTO refresh_tokens(token_hash,user_id,jti,expires_at,created_at) VALUES(?,?,?,?,?)", (digest(new_refresh), user["id"], refresh_jti, refresh_expiry.isoformat(), timestamp()))
    write_audit(user["id"], "token_refreshed", user["id"])
    return {"token_type": "bearer", "access_token": access, "refresh_token": new_refresh, "expires_in": ACCESS_MINUTES * 60, "user": user}


@app.post("/api/v1/auth/logout")
def logout(user: User, authorization: Annotated[str | None, Header()] = None, payload: Refresh | None = None) -> dict[str, str]:
    _, jti = authorize(authorization)
    with connection() as conn:
        conn.execute("INSERT OR REPLACE INTO revoked_access_tokens(jti,expires_at,revoked_at) VALUES(?,?,?)", (jti, (utc_now() + timedelta(minutes=ACCESS_MINUTES)).isoformat(), timestamp()))
        if payload:
            conn.execute("UPDATE refresh_tokens SET revoked_at=? WHERE token_hash=?", (timestamp(), digest(payload.refresh_token)))
    write_audit(user["id"], "logout", user["id"])
    return {"message": "Signed out"}


@app.post("/api/v1/auth/forgot-password")
def forgot_password(payload: ForgotPassword) -> dict[str, Any]:
    row = find_email(payload.email)
    response: dict[str, Any] = {"message": "If the account exists, reset instructions were created."}
    if row:
        raw = secrets.token_urlsafe(32)
        with connection() as conn:
            conn.execute("INSERT INTO password_reset_tokens(token_hash,user_id,expires_at,created_at) VALUES(?,?,?,?)", (digest(raw), row["id"], (utc_now() + timedelta(minutes=RESET_MINUTES)).isoformat(), timestamp()))
        response["development_reset_token"] = raw
        write_audit(row["id"], "password_reset_requested", row["id"])
    return response


@app.post("/api/v1/auth/reset-password")
def reset_password(payload: Reset) -> dict[str, str]:
    with connection() as conn:
        row = conn.execute("SELECT * FROM password_reset_tokens WHERE token_hash=? AND used_at IS NULL", (digest(payload.token),)).fetchone()
        if not row or datetime.fromisoformat(row["expires_at"]) <= utc_now():
            raise HTTPException(400, "Invalid or expired reset token")
        conn.execute("UPDATE users SET password_hash=?,failed_attempts=0,locked_until=NULL,updated_at=? WHERE id=?", (hash_password.hash(payload.password), timestamp(), row["user_id"]))
        conn.execute("UPDATE password_reset_tokens SET used_at=? WHERE token_hash=?", (timestamp(), digest(payload.token)))
        conn.execute("UPDATE refresh_tokens SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL", (timestamp(), row["user_id"]))
    write_audit(row["user_id"], "password_reset_completed", row["user_id"])
    return {"message": "Password reset successfully"}


@app.get("/api/v1/profile")
def profile(user: User) -> dict[str, Any]:
    return {"user": user, "permissions": sorted(ROLE_PERMISSIONS[user["role"]])}


@app.patch("/api/v1/profile")
def update_profile(payload: ProfilePatch, user: User) -> dict[str, Any]:
    changes = payload.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(422, "At least one profile field is required")
    try:
        with connection() as conn:
            conn.execute(f"UPDATE users SET {','.join(f'{key}=?' for key in changes)},updated_at=? WHERE id=?", (*changes.values(), timestamp(), user["id"]))
    except mysql.connector.IntegrityError as error:
        raise HTTPException(409, "Email address is already registered") from error
    write_audit(user["id"], "profile_updated", user["id"])
    return {"user": row_user(get_user(user["id"]))}


@app.post("/api/v1/profile/change-password")
def change_password(payload: ChangePassword, user: User) -> dict[str, str]:
    row = get_user(user["id"])
    try:
        hash_password.verify(row["password_hash"], payload.current_password)
    except (InvalidHashError, VerifyMismatchError):
        raise HTTPException(400, "Current password is incorrect")
    with connection() as conn:
        conn.execute("UPDATE users SET password_hash=?,updated_at=? WHERE id=?", (hash_password.hash(payload.new_password), timestamp(), user["id"]))
    write_audit(user["id"], "password_changed", user["id"])
    return {"message": "Password changed successfully"}


@app.get("/api/v1/permissions")
def permissions(user: User) -> dict[str, Any]:
    return {"role": user["role"], "permissions": sorted(ROLE_PERMISSIONS[user["role"]])}


@app.get("/api/v1/users")
def list_users(user: CanManageUsers, skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200), role: str | None = None, is_active: bool | None = None) -> dict[str, Any]:
    clauses: list[str] = []
    values: list[Any] = []
    if role:
        if role not in ROLES:
            raise HTTPException(422, "Invalid role")
        clauses.append("role=?"); values.append(role)
    if is_active is not None:
        clauses.append("is_active=?"); values.append(int(is_active))
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    with connection() as conn:
        total = conn.execute(f"SELECT COUNT(*) AS n FROM users{where}", values).fetchone()["n"]
        rows = conn.execute(f"SELECT * FROM users{where} ORDER BY id LIMIT ? OFFSET ?", (*values, limit, skip)).fetchall()
    return {"items": [row_user(row) for row in rows], "total": total, "skip": skip, "limit": limit}


@app.post("/api/v1/users", status_code=201)
def create_user(payload: ManagedUser, user: CanManageUsers) -> dict[str, Any]:
    if payload.role == "super_admin" and user["role"] != "super_admin":
        raise HTTPException(403, "Only a super admin can create another super admin")
    try:
        with connection() as conn:
            user_id = conn.execute("INSERT INTO users(name,email,password_hash,role,created_at,updated_at) VALUES(?,?,?,?,?,?)", (payload.name.strip(), payload.email.strip().lower(), hash_password.hash(payload.password), payload.role, timestamp(), timestamp())).lastrowid
    except mysql.connector.IntegrityError as error:
        raise HTTPException(409, "Email address is already registered") from error
    write_audit(user["id"], "user_created", user_id, payload.role)
    return {"user": row_user(get_user(user_id))}


@app.patch("/api/v1/users/{user_id}")
def update_user(user_id: int, payload: UserPatch, user: CanManageUsers) -> dict[str, Any]:
    target = get_user(user_id)
    if not target:
        raise HTTPException(404, "User not found")
    changes = payload.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(422, "At least one user field is required")
    if changes.get("role") == "super_admin" and user["role"] != "super_admin":
        raise HTTPException(403, "Only a super admin can assign the super admin role")
    if user_id == user["id"] and changes.get("is_active") is False:
        raise HTTPException(400, "You cannot deactivate your own account")
    try:
        with connection() as conn:
            conn.execute(f"UPDATE users SET {','.join(f'{key}=?' for key in changes)},updated_at=? WHERE id=?", (*changes.values(), timestamp(), user_id))
    except mysql.connector.IntegrityError as error:
        raise HTTPException(409, "Email address is already registered") from error
    write_audit(user["id"], "user_updated", user_id)
    return {"user": row_user(get_user(user_id))}


@app.post("/api/v1/users/{user_id}/activate")
def activate_user(user_id: int, user: CanManageUsers) -> dict[str, Any]:
    if not get_user(user_id):
        raise HTTPException(404, "User not found")
    with connection() as conn:
        conn.execute("UPDATE users SET is_active=1,updated_at=? WHERE id=?", (timestamp(), user_id))
    write_audit(user["id"], "user_activated", user_id)
    return {"user": row_user(get_user(user_id))}


@app.post("/api/v1/users/{user_id}/deactivate")
def deactivate_user(user_id: int, user: CanManageUsers) -> dict[str, Any]:
    if user_id == user["id"]:
        raise HTTPException(400, "You cannot deactivate your own account")
    if not get_user(user_id):
        raise HTTPException(404, "User not found")
    with connection() as conn:
        conn.execute("UPDATE users SET is_active=0,updated_at=? WHERE id=?", (timestamp(), user_id))
        conn.execute("UPDATE refresh_tokens SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL", (timestamp(), user_id))
    write_audit(user["id"], "user_deactivated", user_id)
    return {"user": row_user(get_user(user_id))}


@app.post("/api/v1/users/{user_id}/reset-password")
def admin_reset_password(user_id: int, payload: Password, user: CanManageUsers) -> dict[str, str]:
    if not get_user(user_id):
        raise HTTPException(404, "User not found")
    with connection() as conn:
        conn.execute("UPDATE users SET password_hash=?,updated_at=? WHERE id=?", (hash_password.hash(payload.password), timestamp(), user_id))
        conn.execute("UPDATE refresh_tokens SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL", (timestamp(), user_id))
    write_audit(user["id"], "admin_password_reset", user_id)
    return {"message": "Password updated successfully"}


@app.delete("/api/v1/users/{user_id}")
def delete_user(user_id: int, user: CanManageUsers) -> dict[str, str]:
    if user_id == user["id"]:
        raise HTTPException(400, "You cannot delete your own account")
    target = get_user(user_id)
    if not target:
        raise HTTPException(404, "User not found")
    if target["role"] == "super_admin":
        with connection() as conn:
            active_admins = conn.execute("SELECT COUNT(*) AS n FROM users WHERE role='super_admin' AND is_active=1").fetchone()["n"]
        if active_admins <= 1:
            raise HTTPException(400, "The last active super admin cannot be deleted")
    with connection() as conn:
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    write_audit(user["id"], "user_deleted", user_id)
    return {"message": "User deleted successfully"}


@app.get("/api/v1/audit-logs")
def audit_logs(user: CanManageUsers, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)) -> dict[str, Any]:
    with connection() as conn:
        rows = conn.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ? OFFSET ?", (limit, skip)).fetchall()
    return {"items": [dict(row) for row in rows], "skip": skip, "limit": limit}
