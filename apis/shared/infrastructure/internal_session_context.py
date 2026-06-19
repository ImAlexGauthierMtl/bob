"""Signed internal session context for B4F-to-Backend calls."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, Optional, Protocol
from uuid import uuid4

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from jose import JWTError, jwt


class InternalSessionContextError(ValueError):
    """Raised when an internal session context cannot be trusted."""

    def __init__(self, reason_code: str, message: str):
        super().__init__(message)
        self.reason_code = reason_code


@dataclass(frozen=True)
class InternalSessionContext:
    """Tenant/user context validated by a B4F and consumed by internal APIs."""

    tenant_id: str
    user_id: str
    session_id: str
    trace_id: str
    permissions: tuple[str, ...] = field(default_factory=tuple)
    entitlements: tuple[str, ...] = field(default_factory=tuple)
    roles: tuple[str, ...] = field(default_factory=tuple)
    jti: str = field(default_factory=lambda: f"ctx_{uuid4().hex}")

    def __post_init__(self) -> None:
        required = {
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "jti": self.jti,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise InternalSessionContextError(
                "internal_session_context_invalid",
                f"Missing required fields: {', '.join(missing)}",
            )

    @classmethod
    def from_payload(cls, payload: Dict[str, object]) -> "InternalSessionContext":
        return cls(
            tenant_id=str(payload.get("tenant_id") or ""),
            user_id=str(payload.get("user_id") or ""),
            session_id=str(payload.get("session_id") or ""),
            trace_id=str(payload.get("trace_id") or ""),
            permissions=tuple(_as_string_list(payload.get("permissions"))),
            entitlements=tuple(_as_string_list(payload.get("entitlements"))),
            roles=tuple(_as_string_list(payload.get("roles"))),
            jti=str(payload.get("jti") or ""),
        )

    def to_payload(self) -> Dict[str, object]:
        return {
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "permissions": list(self.permissions),
            "entitlements": list(self.entitlements),
            "roles": list(self.roles),
            "jti": self.jti,
        }


class ReplayStore(Protocol):
    """Storage boundary for one-time JTI replay protection."""

    def check_and_mark(self, jti: str, expires_at: int, now: int) -> bool:
        """Return True when the JTI is new and has been marked as used."""


class InMemoryReplayStore:
    """Small replay store for tests and local dev; replace with Redis in prod."""

    def __init__(self) -> None:
        self._seen: Dict[str, int] = {}

    def check_and_mark(self, jti: str, expires_at: int, now: int) -> bool:
        self._cleanup(now)
        if jti in self._seen:
            return False
        self._seen[jti] = expires_at
        return True

    def _cleanup(self, now: int) -> None:
        expired = [jti for jti, expires_at in self._seen.items() if expires_at <= now]
        for jti in expired:
            del self._seen[jti]


class InternalSessionContextSigner:
    """Issue and validate compact JWS internal session contexts."""

    def __init__(
        self,
        secret: str,
        *,
        kid: str,
        issuer: str = "cde-b4f",
        audience: str = "cde-internal-backend",
        ttl_seconds: int = 300,
        replay_store: Optional[ReplayStore] = None,
    ) -> None:
        if not secret:
            raise InternalSessionContextError(
                "internal_session_secret_missing",
                "Internal session secret is required",
            )
        if not kid:
            raise InternalSessionContextError(
                "internal_session_kid_missing",
                "Internal session key id is required",
            )
        self.secret = secret
        self.kid = kid
        self.issuer = issuer
        self.audience = audience
        self.ttl_seconds = ttl_seconds
        self.replay_store = replay_store

    def issue(self, context: InternalSessionContext, now: Optional[int] = None) -> str:
        issued_at = _now(now)
        expires_at = issued_at + self.ttl_seconds
        payload = {
            **context.to_payload(),
            "iss": self.issuer,
            "aud": self.audience,
            "iat": issued_at,
            "exp": expires_at,
        }
        return jwt.encode(
            payload,
            self.secret,
            algorithm="HS256",
            headers={"alg": "HS256", "typ": "JWT", "kid": self.kid},
        )

    def validate(self, token: str, now: Optional[int] = None) -> InternalSessionContext:
        checked_at = _now(now)
        header = self._get_header(token)
        self._validate_header(header)
        payload = self._decode_without_time_validation(token)
        self._validate_time(payload, checked_at)
        context = InternalSessionContext.from_payload(payload)
        if self.replay_store:
            expires_at = int(payload["exp"])
            if not self.replay_store.check_and_mark(context.jti, expires_at, checked_at):
                raise InternalSessionContextError(
                    "internal_session_replayed",
                    "Internal session context has already been used",
                )
        return context

    def _get_header(self, token: str) -> Dict[str, object]:
        try:
            return jwt.get_unverified_header(token)
        except JWTError as exc:
            raise InternalSessionContextError(
                "internal_session_invalid",
                "Invalid internal session token header",
            ) from exc

    def _validate_header(self, header: Dict[str, object]) -> None:
        if header.get("alg") != "HS256":
            raise InternalSessionContextError(
                "internal_session_algorithm_invalid",
                "Internal session context must use HS256",
            )
        if header.get("kid") != self.kid:
            raise InternalSessionContextError(
                "internal_session_kid_invalid",
                "Internal session key id is not accepted",
            )

    def _decode_without_time_validation(self, token: str) -> Dict[str, object]:
        try:
            return jwt.decode(
                token,
                self.secret,
                algorithms=["HS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"verify_exp": False, "verify_iat": False},
            )
        except JWTError as exc:
            raise InternalSessionContextError(
                "internal_session_invalid",
                "Internal session context signature or claims are invalid",
            ) from exc

    def _validate_time(self, payload: Dict[str, object], now: int) -> None:
        issued_at = _int_claim(payload, "iat")
        expires_at = _int_claim(payload, "exp")
        if expires_at <= now:
            raise InternalSessionContextError(
                "internal_session_expired",
                "Internal session context has expired",
            )
        if issued_at > now + 30:
            raise InternalSessionContextError(
                "internal_session_iat_invalid",
                "Internal session context is issued in the future",
            )
        if expires_at - issued_at > self.ttl_seconds:
            raise InternalSessionContextError(
                "internal_session_ttl_invalid",
                "Internal session context TTL exceeds the configured maximum",
            )


class InternalSessionContextMiddleware:
    """FastAPI middleware for internal APIs that require a signed context."""

    def __init__(
        self,
        signer: InternalSessionContextSigner,
        *,
        extra_public_paths: Optional[Iterable[str]] = None,
    ) -> None:
        self.signer = signer
        self.public_paths = {
            "/health",
            "/readiness",
            "/liveness",
            "/startup",
            "/metrics",
            *(extra_public_paths or ()),
        }

    async def __call__(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.public_paths:
            return await call_next(request)

        token = request.headers.get("x-session-context", "")
        if not token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing internal session context"},
            )

        try:
            context = self.signer.validate(token)
        except InternalSessionContextError as exc:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": exc.reason_code},
            )

        request.state.internal_session_context = context
        request.state.tenant_id = context.tenant_id
        request.state.user_id = context.user_id
        request.state.trace_id = context.trace_id
        return await call_next(request)


def _as_string_list(value: object) -> Iterable[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _int_claim(payload: Dict[str, object], claim: str) -> int:
    value = payload.get(claim)
    if not isinstance(value, int):
        raise InternalSessionContextError(
            "internal_session_claim_invalid",
            f"Internal session claim '{claim}' must be an integer",
        )
    return value


def _now(now: Optional[int]) -> int:
    return int(time.time() if now is None else now)
