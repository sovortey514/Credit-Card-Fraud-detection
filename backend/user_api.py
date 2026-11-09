"""FastAPI authentication and User Management service."""

import logging
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.user_database import (
    authenticate,
    create_reset_token,
    create_user,
    delete_user,
    init_user_db,
    list_users,
    reset_password,
    revoke_token,
    set_password,
    update_user,
    user_for_token,
)


app = FastAPI(title="TransferGuard User Management API", version="1.0.0")
logger = logging.getLogger("transferguard.user_api")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_user_db()


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=8)


class UserCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str
    role: str = Field(pattern="^(admin|administrator|risk_manager|analyst|customer|compliance)$")
    password: str = Field(min_length=8)


class UserUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    role: Optional[str] = Field(default=None, pattern="^(admin|administrator|risk_manager|analyst|customer|compliance)$")
    is_active: Optional[bool] = None


class AdminResetPasswordRequest(BaseModel):
    password: str = Field(min_length=8)


def current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    user = user_for_token(authorization[7:].strip())
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
    return user


def admin_only(user: dict = Depends(current_user)) -> dict:
    if user.get("role") not in {"admin", "administrator", "risk_manager"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    return user


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "user-api"}


@app.get("/")
def root() -> dict:
    return {
        "service": "TransferGuard User Management API",
        "docs": "/docs",
        "health": "/health",
    }


@app.post("/api/v1/auth/login")
def login(payload: LoginRequest) -> dict:
    try:
        result = authenticate(str(payload.email), payload.password)
    except Exception as exc:
        logger.exception("Login failed while accessing the user database")
        raise HTTPException(status_code=503, detail="User database authentication failed") from exc
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return result


@app.post("/api/v1/auth/logout")
def logout(user: dict = Depends(current_user), authorization: Optional[str] = Header(default=None)) -> dict:
    revoke_token(authorization[7:].strip())
    return {"message": "Signed out"}


@app.post("/api/v1/auth/forgot-password")
def forgot_password(payload: ForgotPasswordRequest) -> dict:
    token = create_reset_token(str(payload.email))
    # In production, send this token through an email provider instead.
    response = {"message": "If the account exists, reset instructions were created."}
    if token:
        response["development_reset_token"] = token
    return response


@app.post("/api/v1/auth/reset-password")
def reset_password_endpoint(payload: ResetPasswordRequest) -> dict:
    if not reset_password(payload.token, payload.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    return {"message": "Password reset successfully"}


@app.get("/api/v1/users")
def users(_: dict = Depends(admin_only)) -> list[dict]:
    return list_users()


@app.post("/api/v1/users", status_code=status.HTTP_201_CREATED)
def add_user(payload: UserCreateRequest, _: dict = Depends(admin_only)) -> dict:
    try:
        return create_user(payload.name, str(payload.email), payload.role, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@app.patch("/api/v1/users/{user_id}")
def edit_user(user_id: int, payload: UserUpdateRequest, _: dict = Depends(admin_only)) -> dict:
    result = update_user(user_id, payload.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return result


@app.delete("/api/v1/users/{user_id}")
def remove_user(user_id: int, _: dict = Depends(admin_only)) -> dict:
    if not delete_user(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"message": "User deleted"}


@app.post("/api/v1/users/{user_id}/reset-password")
def admin_reset_password(user_id: int, payload: AdminResetPasswordRequest, _: dict = Depends(admin_only)) -> dict:
    if not set_password(user_id, payload.password):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"message": "Password updated"}
