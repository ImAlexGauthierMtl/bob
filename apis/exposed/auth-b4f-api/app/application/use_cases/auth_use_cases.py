"""Authentication use cases."""
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Optional, Protocol

from jose import JWTError, jwt


class AuthError(Exception):
    """Raised when authentication cannot continue."""

    def __init__(self, detail: str, status_code: int = 401) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class UserClientPort(Protocol):
    async def get_by_id(self, user_id: str, forward_headers: Any = None) -> Optional[dict[str, Any]]:
        ...

    async def get_by_email(self, email: str, forward_headers: Any = None) -> Optional[dict[str, Any]]:
        ...

    async def create(self, data: dict[str, Any], forward_headers: Any = None) -> dict[str, Any]:
        ...

    async def update(self, user_id: str, data: dict[str, Any], forward_headers: Any = None) -> dict[str, Any]:
        ...

    async def get_user_roles(self, user_id: str, forward_headers: Any = None) -> list[dict[str, Any]]:
        ...

    async def get_user_permissions(self, user_id: str, forward_headers: Any = None) -> list[str]:
        ...


PasswordVerifier = Callable[[str, str], Awaitable[bool]]


class AuthUseCases:
    def __init__(
        self,
        *,
        user_client: UserClientPort,
        verify_password: PasswordVerifier,
        jwt_secret_key: str,
        jwt_algorithm: str,
        access_token_expire_minutes: int,
        refresh_token_expire_days: int,
        rate_limit_max_attempts: int,
        rate_limit_window_minutes: int,
        rate_limit_storage: dict[str, list[datetime]],
    ) -> None:
        self.user_client = user_client
        self.verify_password = verify_password
        self.jwt_secret_key = jwt_secret_key
        self.jwt_algorithm = jwt_algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.rate_limit_max_attempts = rate_limit_max_attempts
        self.rate_limit_window_minutes = rate_limit_window_minutes
        self.rate_limit_storage = rate_limit_storage

    def create_access_token(self, data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=self.access_token_expire_minutes))
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, self.jwt_secret_key, algorithm=self.jwt_algorithm)

    def create_refresh_token(self, data: dict[str, Any]) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, self.jwt_secret_key, algorithm=self.jwt_algorithm)

    def verify_token(self, token: str) -> Optional[dict[str, Any]]:
        try:
            return jwt.decode(token, self.jwt_secret_key, algorithms=[self.jwt_algorithm])
        except JWTError:
            return None

    def is_rate_limited(self, identifier: str) -> bool:
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=self.rate_limit_window_minutes)
        if identifier not in self.rate_limit_storage:
            return False
        self.rate_limit_storage[identifier] = [
            attempt for attempt in self.rate_limit_storage[identifier] if attempt > window_start
        ]
        return len(self.rate_limit_storage[identifier]) >= self.rate_limit_max_attempts

    def add_failed_attempt(self, identifier: str) -> None:
        self.rate_limit_storage.setdefault(identifier, []).append(datetime.now(timezone.utc))

    async def current_user(self, token: str, forward_headers: Any = None) -> dict[str, Any]:
        payload = self.verify_token(token)
        if payload is None or payload.get("type") != "access":
            raise AuthError("Invalid or expired token")
        user_id = payload.get("sub")
        if not user_id:
            raise AuthError("Invalid token")

        user_data = await self.user_client.get_by_id(user_id, forward_headers=forward_headers)
        if not user_data:
            raise AuthError("User not found")

        roles = await self.user_client.get_user_roles(user_id, forward_headers=forward_headers)
        permissions = await self.user_client.get_user_permissions(user_id, forward_headers=forward_headers)
        return {
            "user_id": user_id,
            "email": payload.get("email"),
            "tenant_id": user_data.get("tenant_id", "default"),
            "active_organization_id": user_data.get("active_organization_id"),
            "roles": [role.get("name") for role in roles],
            "permissions": permissions,
        }

    async def register(self, user_data: dict[str, Any]) -> dict[str, Any]:
        email = user_data["email"].lower()
        existing = await self.user_client.get_by_email(email)
        if existing:
            raise AuthError("A user with this email already exists", status_code=400)
        return await self.user_client.create({**user_data, "email": email})

    async def login(self, email: str, password: str, client_ip: str) -> dict[str, str]:
        if self.is_rate_limited(client_ip):
            raise AuthError("Too many login attempts", status_code=429)

        normalized_email = email.lower()
        user_data = await self.user_client.get_by_email(normalized_email)
        if not user_data:
            self.add_failed_attempt(client_ip)
            raise AuthError("Invalid email or password")

        if not await self.verify_password(normalized_email, password):
            self.add_failed_attempt(client_ip)
            raise AuthError("Invalid email or password")

        access_token = self.create_access_token(
            data={
                "sub": user_data["id"],
                "email": user_data["email"],
                "tenant_id": user_data.get("tenant_id"),
                "active_organization_id": user_data.get("active_organization_id"),
                "role": user_data.get("role"),
                "is_super_admin": bool(user_data.get("is_super_admin")),
            }
        )
        refresh_token = self.create_refresh_token(data={"sub": user_data["id"]})
        return {"access_token": access_token, "refresh_token": refresh_token}

    async def refresh(self, refresh_token: str, forward_headers: Any = None) -> dict[str, str]:
        payload = self.verify_token(refresh_token)
        if payload is None or payload.get("type") != "refresh":
            raise AuthError("Invalid refresh token")
        user_data = await self.user_client.get_by_id(payload.get("sub"), forward_headers=forward_headers)
        if not user_data:
            raise AuthError("User not found")

        access_token = self.create_access_token(
            data={
                "sub": user_data["id"],
                "email": user_data["email"],
                "tenant_id": user_data.get("tenant_id"),
                "active_organization_id": user_data.get("active_organization_id"),
                "role": user_data.get("role"),
                "is_super_admin": bool(user_data.get("is_super_admin")),
            }
        )
        return {"access_token": access_token, "refresh_token": self.create_refresh_token(data={"sub": user_data["id"]})}

    async def get_me(self, user_id: str, forward_headers: Any = None) -> dict[str, Any]:
        user_data = await self.user_client.get_by_id(user_id, forward_headers=forward_headers)
        if not user_data:
            raise AuthError("User not found", status_code=404)
        return user_data

    async def set_active_organization(
        self,
        user_id: str,
        organization_id: str,
        forward_headers: Any = None,
    ) -> dict[str, Any]:
        return await self.user_client.update(
            user_id,
            {"active_organization_id": organization_id},
            forward_headers=forward_headers,
        )
