"""Authentication routes — JWT logic stays here, CRUD goes to user~backend-api."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import bcrypt

from app.config import settings
from app.infrastructure.clients.user_client import user_client
from app.presentation.schemas.auth_schemas import (
    UserRegisterRequest, UserLoginRequest, TokenResponse,
    RefreshTokenRequest, UserResponse, SetActiveOrgRequest,
)

router = APIRouter(prefix="/api/v1/auth")
security = HTTPBearer()
rate_limit_storage: dict[str, list[datetime]] = {}


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def verify_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


def is_rate_limited(identifier: str) -> bool:
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=settings.rate_limit_window_minutes)
    if identifier not in rate_limit_storage:
        return False
    rate_limit_storage[identifier] = [a for a in rate_limit_storage[identifier] if a > window_start]
    return len(rate_limit_storage[identifier]) >= settings.rate_limit_max_attempts


def add_failed_attempt(identifier: str) -> None:
    rate_limit_storage.setdefault(identifier, []).append(datetime.now(timezone.utc))


async def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    payload = verify_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_data = await user_client.get_by_id(user_id, forward_headers=request.headers)
    if not user_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    roles = await user_client.get_user_roles(user_id, forward_headers=request.headers)
    permissions = await user_client.get_user_permissions(user_id, forward_headers=request.headers)

    return {
        "user_id": user_id,
        "email": payload.get("email"),
        "tenant_id": user_data.get("tenant_id", "default"),
        "active_organization_id": user_data.get("active_organization_id"),
        "roles": [r.get("name") for r in roles],
        "permissions": permissions,
    }


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegisterRequest, request: Request):
    existing = await user_client.get_by_email(user_data.email.lower())
    if existing:
        raise HTTPException(status_code=400, detail="A user with this email already exists")
    created = await user_client.create({
        "email": user_data.email,
        "password": user_data.password,
        "first_name": user_data.first_name,
        "last_name": user_data.last_name,
    })
    return created


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLoginRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if is_rate_limited(client_ip):
        raise HTTPException(status_code=429, detail="Too many login attempts")

    user_data = await user_client.get_by_email(credentials.email.lower())
    if not user_data:
        add_failed_attempt(client_ip)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    from shared.services import create_service_client
    client = create_service_client("user~backend-api")
    verify_resp = await client.post("/api/v1/users/verify-password", json={
        "email": credentials.email.lower(),
        "password": credentials.password,
    })
    if verify_resp.status_code != 200 or not verify_resp.json().get("valid"):
        add_failed_attempt(client_ip)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(data={"sub": user_data["id"], "email": user_data["email"], "tenant_id": user_data.get("tenant_id")})
    refresh_token = create_refresh_token(data={"sub": user_data["id"]})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(token_data: RefreshTokenRequest, request: Request):
    payload = verify_token(token_data.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user_data = await user_client.get_by_id(payload.get("sub"), forward_headers=request.headers)
    if not user_data:
        raise HTTPException(status_code=401, detail="User not found")
    access_token = create_access_token(data={"sub": user_data["id"], "email": user_data["email"], "tenant_id": user_data.get("tenant_id")})
    refresh_token = create_refresh_token(data={"sub": user_data["id"]})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(request: Request, current_user: dict = Depends(get_current_user)):
    user_data = await user_client.get_by_id(current_user["user_id"], forward_headers=request.headers)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    return user_data


@router.put("/me/active-organization", response_model=UserResponse)
async def set_active_organization(body: SetActiveOrgRequest, request: Request, current_user: dict = Depends(get_current_user)):
    updated = await user_client.update(
        current_user["user_id"],
        {"active_organization_id": body.organization_id},
        forward_headers=request.headers,
    )
    return updated
