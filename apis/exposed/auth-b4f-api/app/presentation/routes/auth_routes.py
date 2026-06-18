"""Authentication routes."""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.application.use_cases.auth_use_cases import AuthError, AuthUseCases
from app.config import settings
from app.infrastructure.clients.user_client import user_client
from app.presentation.schemas.auth_schemas import (
    UserRegisterRequest, UserLoginRequest, TokenResponse,
    RefreshTokenRequest, UserResponse, SetActiveOrgRequest,
)

router = APIRouter(prefix="/auth")
security = HTTPBearer()
rate_limit_storage: dict[str, list[datetime]] = {}


async def _verify_password(email: str, password: str) -> bool:
    from shared.services import create_service_client

    client = create_service_client("user~backend-api")
    verify_resp = await client.post(
        "/api/v1/users/verify-password",
        json={"email": email, "password": password},
    )
    return verify_resp.status_code == 200 and bool(verify_resp.json().get("valid"))


def get_auth_use_cases() -> AuthUseCases:
    return AuthUseCases(
        user_client=user_client,
        verify_password=_verify_password,
        jwt_secret_key=settings.jwt_secret_key,
        jwt_algorithm=settings.jwt_algorithm,
        access_token_expire_minutes=settings.access_token_expire_minutes,
        refresh_token_expire_days=settings.refresh_token_expire_days,
        rate_limit_max_attempts=settings.rate_limit_max_attempts,
        rate_limit_window_minutes=settings.rate_limit_window_minutes,
        rate_limit_storage=rate_limit_storage,
    )


def _raise_http(exc: AuthError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    return get_auth_use_cases().create_access_token(data, expires_delta)


def create_refresh_token(data: dict) -> str:
    return get_auth_use_cases().create_refresh_token(data)


def verify_token(token: str) -> Optional[dict]:
    return get_auth_use_cases().verify_token(token)


def is_rate_limited(identifier: str) -> bool:
    return get_auth_use_cases().is_rate_limited(identifier)


def add_failed_attempt(identifier: str) -> None:
    get_auth_use_cases().add_failed_attempt(identifier)


async def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        return await get_auth_use_cases().current_user(credentials.credentials, forward_headers=request.headers)
    except AuthError as exc:
        _raise_http(exc)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegisterRequest, request: Request):
    try:
        return await get_auth_use_cases().register(user_data.model_dump())
    except AuthError as exc:
        _raise_http(exc)


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLoginRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    try:
        return TokenResponse(**await get_auth_use_cases().login(credentials.email, credentials.password, client_ip))
    except AuthError as exc:
        _raise_http(exc)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(token_data: RefreshTokenRequest, request: Request):
    try:
        return TokenResponse(**await get_auth_use_cases().refresh(token_data.refresh_token, forward_headers=request.headers))
    except AuthError as exc:
        _raise_http(exc)


@router.get("/me", response_model=UserResponse)
async def get_me(request: Request, current_user: dict = Depends(get_current_user)):
    try:
        return await get_auth_use_cases().get_me(current_user["user_id"], forward_headers=request.headers)
    except AuthError as exc:
        _raise_http(exc)


@router.put("/me/active-organization", response_model=UserResponse)
async def set_active_organization(body: SetActiveOrgRequest, request: Request, current_user: dict = Depends(get_current_user)):
    return await get_auth_use_cases().set_active_organization(
        current_user["user_id"],
        body.organization_id,
        forward_headers=request.headers,
    )
