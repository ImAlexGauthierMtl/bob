"""Local storage clients for email provider workflows.

These adapters keep provider orchestration code decoupled from persistence
without making this Backend call its own HTTP routes.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from sqlalchemy import inspect
from sqlalchemy.exc import NoInspectionAvailable

from app.application.use_cases.integration_settings_use_cases import IntegrationSettingsUseCases
from app.application.use_cases.membrane_crud_use_cases import MembraneCrudUseCases
from app.application.use_cases.ms365_core_use_cases import MS365CoreUseCases
from app.domain.exceptions import (
    ConnectionAlreadyExistsError,
    ConnectionNotFoundError,
    EmailNotFoundError,
    EventNotFoundError,
    IntegrationSettingNotFoundError,
)
from app.events.publishers import publish_email_received
from app.infrastructure.database import get_db
from app.infrastructure.persistence.integration_settings_repository import IntegrationSettingsRepository
from app.infrastructure.persistence.membrane_repository import MembraneRepository
from app.infrastructure.persistence.ms365_repository import MS365Repository
from app.middleware.auth import settings


def _header_value(headers: Any, name: str) -> Optional[str]:
    if not headers:
        return None
    if hasattr(headers, "get"):
        return headers.get(name) or headers.get(name.lower()) or headers.get(name.title())
    return None


def _tenant_id(forward_headers: Any = None, explicit: Optional[str] = None) -> str:
    if explicit:
        return explicit

    authorization = _header_value(forward_headers, "authorization")
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            return payload.get("tenant_id") or "default"
        except JWTError:
            return "default"

    return "default"


def _user_from_headers(forward_headers: Any = None, explicit_tenant_id: Optional[str] = None) -> dict[str, Any]:
    authorization = _header_value(forward_headers, "authorization")
    payload: dict[str, Any] = {}
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        except JWTError:
            payload = {}

    return {
        "user_id": payload.get("sub") or "system",
        "email": payload.get("email") or "system",
        "tenant_id": explicit_tenant_id or payload.get("tenant_id") or "default",
        "role": (payload.get("role") or "").lower(),
        "is_super_admin": bool(payload.get("is_super_admin")),
    }


def _parse_datetime(value: Any) -> Any:
    if isinstance(value, datetime) or value is None:
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return value
    return value


def _entity_dict(entity: Any) -> dict[str, Any]:
    if entity is None:
        return {}
    if isinstance(entity, dict):
        return dict(entity)

    try:
        mapper = inspect(entity).mapper
        return {attr.key: getattr(entity, attr.key) for attr in mapper.column_attrs}
    except (NoInspectionAvailable, AttributeError):
        return {
            key: value
            for key, value in vars(entity).items()
            if not key.startswith("_")
        }


@contextmanager
def _db_session():
    generator = get_db()
    db = next(generator)
    try:
        yield db
    finally:
        try:
            next(generator)
        except StopIteration:
            pass


def _ms365_use_cases(db: Any) -> MS365CoreUseCases:
    return MS365CoreUseCases(
        repo=MS365Repository(db),
        publish_email_received=publish_email_received,
    )


def _membrane_use_cases(db: Any) -> MembraneCrudUseCases:
    return MembraneCrudUseCases(repo=MembraneRepository(db))


def _integration_settings_use_cases(db: Any) -> IntegrationSettingsUseCases:
    return IntegrationSettingsUseCases(repo=IntegrationSettingsRepository(db))


class IntegrationSettingsClient:
    """Local client for integration settings CRUD."""

    async def list(self, forward_headers: Any = None, tenant_id: Optional[str] = None) -> list[dict[str, Any]]:
        with _db_session() as db:
            use_cases = _integration_settings_use_cases(db)
            items = await use_cases.list_settings(_tenant_id(forward_headers, tenant_id))
            return [_entity_dict(item) for item in items]

    async def upsert(self, data: dict, forward_headers: Any = None, tenant_id: Optional[str] = None) -> dict:
        with _db_session() as db:
            use_cases = _integration_settings_use_cases(db)
            item = await use_cases.create_or_update_setting(data, _tenant_id(forward_headers, tenant_id))
            return _entity_dict(item)

    async def get(self, integration_key: str, forward_headers: Any = None, tenant_id: Optional[str] = None) -> Optional[dict]:
        for item in await self.list(forward_headers=forward_headers, tenant_id=tenant_id):
            if item.get("integration_key") == integration_key:
                return item
        return None

    async def update(self, integration_key: str, data: dict, forward_headers: Any = None, tenant_id: Optional[str] = None) -> dict:
        with _db_session() as db:
            use_cases = _integration_settings_use_cases(db)
            item = await use_cases.update_setting(integration_key, data, _tenant_id(forward_headers, tenant_id))
            return _entity_dict(item)

    async def delete(self, integration_key: str, forward_headers: Any = None, tenant_id: Optional[str] = None) -> bool:
        with _db_session() as db:
            use_cases = _integration_settings_use_cases(db)
            try:
                await use_cases.delete_setting(integration_key, _tenant_id(forward_headers, tenant_id))
            except IntegrationSettingNotFoundError:
                return False
            return True


class ConnectionClient:
    """Local client for MS365 connection CRUD."""

    async def get_by_user(self, user_id: str, forward_headers: Any = None, tenant_id: Optional[str] = None) -> Optional[dict]:
        with _db_session() as db:
            conn = await _ms365_use_cases(db).get_connection_by_user(
                user_id,
                _tenant_id(forward_headers, tenant_id),
            )
            return _entity_dict(conn) if conn else None

    async def get(self, conn_id: str, forward_headers: Any = None, tenant_id: Optional[str] = None) -> Optional[dict]:
        with _db_session() as db:
            try:
                conn = await _ms365_use_cases(db).get_connection(conn_id, _tenant_id(forward_headers, tenant_id))
            except ConnectionNotFoundError:
                return None
            return _entity_dict(conn)

    async def list_active(self, forward_headers: Any = None) -> list[dict[str, Any]]:
        with _db_session() as db:
            conns = await _ms365_use_cases(db).list_active_connections()
            return [_entity_dict(conn) for conn in conns]

    async def create(self, data: dict, forward_headers: Any = None, tenant_id: Optional[str] = None) -> dict:
        with _db_session() as db:
            try:
                conn = await _ms365_use_cases(db).create_connection(data, _tenant_id(forward_headers, tenant_id))
            except ConnectionAlreadyExistsError:
                existing = await _ms365_use_cases(db).get_connection_by_user(
                    data["user_id"],
                    _tenant_id(forward_headers, tenant_id),
                )
                return _entity_dict(existing)
            return _entity_dict(conn)

    async def update(self, conn_id: str, data: dict, forward_headers: Any = None, tenant_id: Optional[str] = None) -> dict:
        with _db_session() as db:
            conn = await _ms365_use_cases(db).update_connection(
                conn_id,
                data,
                _tenant_id(forward_headers, tenant_id),
            )
            return _entity_dict(conn)

    async def delete(self, conn_id: str, forward_headers: Any = None, tenant_id: Optional[str] = None) -> bool:
        with _db_session() as db:
            try:
                await _ms365_use_cases(db).delete_connection(
                    conn_id,
                    _user_from_headers(forward_headers, tenant_id),
                )
            except ConnectionNotFoundError:
                return False
            return True


class EmailCrudClient:
    """Local client for synced email CRUD."""

    async def list(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        folder: Optional[str] = None,
        search: Optional[str] = None,
        smart_label: Optional[str] = None,
        linked_contact_id: Optional[str] = None,
        forward_headers: Any = None,
        tenant_id: Optional[str] = None,
    ) -> dict:
        with _db_session() as db:
            result = await _ms365_use_cases(db).list_emails(
                user_id,
                _tenant_id(forward_headers, tenant_id),
                skip,
                limit,
                folder,
                search,
                linked_contact_id,
                smart_label,
            )
            return {
                "items": [_entity_dict(item) for item in result.items],
                "total": result.total,
                "skip": result.skip,
                "limit": result.limit,
            }

    async def get(self, email_id: str, user_id: str, forward_headers: Any = None, tenant_id: Optional[str] = None) -> Optional[dict]:
        with _db_session() as db:
            try:
                email = await _ms365_use_cases(db).get_email(email_id, user_id, _tenant_id(forward_headers, tenant_id))
            except EmailNotFoundError:
                return None
            return _entity_dict(email)

    async def upsert(self, data: dict, forward_headers: Any = None, tenant_id: Optional[str] = None) -> dict:
        with _db_session() as db:
            email = await _ms365_use_cases(db).upsert_email(data, _tenant_id(forward_headers, tenant_id))
            return _entity_dict(email)

    async def update(self, email_id: str, data: dict, user_id: str, forward_headers: Any = None, tenant_id: Optional[str] = None) -> dict:
        with _db_session() as db:
            email = await _ms365_use_cases(db).update_email(
                email_id,
                user_id,
                _tenant_id(forward_headers, tenant_id),
                data,
            )
            return _entity_dict(email)

    async def delete(self, email_id: str, user_id: str, forward_headers: Any = None, tenant_id: Optional[str] = None) -> bool:
        with _db_session() as db:
            try:
                await _ms365_use_cases(db).delete_email(email_id, user_id, _tenant_id(forward_headers, tenant_id))
            except EmailNotFoundError:
                return False
            return True


class EventCrudClient:
    """Local client for synced event CRUD."""

    async def list(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        from_date: Any = None,
        to_date: Any = None,
        forward_headers: Any = None,
        tenant_id: Optional[str] = None,
    ) -> dict:
        with _db_session() as db:
            result = await _ms365_use_cases(db).list_events(
                user_id,
                _tenant_id(forward_headers, tenant_id),
                skip,
                limit,
                _parse_datetime(from_date),
                _parse_datetime(to_date),
            )
            return {
                "items": [_entity_dict(item) for item in result.items],
                "total": result.total,
                "skip": result.skip,
                "limit": result.limit,
            }

    async def get(self, event_id: str, user_id: str, forward_headers: Any = None, tenant_id: Optional[str] = None) -> Optional[dict]:
        with _db_session() as db:
            try:
                event = await _ms365_use_cases(db).get_event(event_id, user_id, _tenant_id(forward_headers, tenant_id))
            except EventNotFoundError:
                return None
            return _entity_dict(event)

    async def upsert(self, data: dict, forward_headers: Any = None, tenant_id: Optional[str] = None) -> dict:
        with _db_session() as db:
            event = await _ms365_use_cases(db).upsert_event(data, _tenant_id(forward_headers, tenant_id))
            return _entity_dict(event)

    async def update(self, event_id: str, data: dict, user_id: str, forward_headers: Any = None, tenant_id: Optional[str] = None) -> dict:
        with _db_session() as db:
            event = await _ms365_use_cases(db).update_event(
                event_id,
                user_id,
                _tenant_id(forward_headers, tenant_id),
                data,
            )
            return _entity_dict(event)

    async def delete(self, event_id: str, user_id: str, forward_headers: Any = None, tenant_id: Optional[str] = None) -> bool:
        with _db_session() as db:
            try:
                await _ms365_use_cases(db).delete_event(event_id, user_id, _tenant_id(forward_headers, tenant_id))
            except EventNotFoundError:
                return False
            return True


class MembraneCrudClient:
    """Local client for Membrane-backed CRUD."""

    async def upsert_connection(self, data: dict, forward_headers: Any = None, tenant_id: Optional[str] = None) -> dict:
        with _db_session() as db:
            conn = await _membrane_use_cases(db).create_connection(data, _tenant_id(forward_headers, tenant_id))
            return _entity_dict(conn)

    async def get_connection(self, connection_id: str, forward_headers: Any = None, tenant_id: Optional[str] = None) -> Optional[dict]:
        with _db_session() as db:
            try:
                conn = await _membrane_use_cases(db).get_connection(connection_id, _tenant_id(forward_headers, tenant_id))
            except ConnectionNotFoundError:
                return None
            return _entity_dict(conn)

    async def upsert_email(self, data: dict, forward_headers: Any = None, tenant_id: Optional[str] = None) -> dict:
        with _db_session() as db:
            email = await _membrane_use_cases(db).upsert_email(data, _tenant_id(forward_headers, tenant_id))
            return _entity_dict(email)

    async def upsert_event(self, data: dict, forward_headers: Any = None, tenant_id: Optional[str] = None) -> dict:
        with _db_session() as db:
            event = await _membrane_use_cases(db).upsert_event(data, _tenant_id(forward_headers, tenant_id))
            return _entity_dict(event)

    async def get_connection_by_user(
        self,
        user_id: str,
        integration_key: Optional[str] = None,
        forward_headers: Any = None,
        tenant_id: Optional[str] = None,
    ) -> Optional[dict]:
        with _db_session() as db:
            try:
                conn = await _membrane_use_cases(db).get_connection_by_user(
                    user_id,
                    integration_key,
                    _tenant_id(forward_headers, tenant_id),
                )
            except ConnectionNotFoundError:
                return None
            return _entity_dict(conn)

    async def list_emails(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        folder: Optional[str] = None,
        search: Optional[str] = None,
        forward_headers: Any = None,
        tenant_id: Optional[str] = None,
    ) -> dict:
        with _db_session() as db:
            result = await _membrane_use_cases(db).list_emails(
                user_id,
                _tenant_id(forward_headers, tenant_id),
                skip,
                limit,
                folder,
                search,
            )
            return {
                "items": [_entity_dict(item) for item in result.items],
                "total": result.total,
                "skip": result.skip,
                "limit": result.limit,
            }

    async def get_email(self, email_id: str, user_id: str, forward_headers: Any = None, tenant_id: Optional[str] = None) -> Optional[dict]:
        with _db_session() as db:
            try:
                email = await _membrane_use_cases(db).get_email(
                    email_id,
                    user_id,
                    _tenant_id(forward_headers, tenant_id),
                )
            except EmailNotFoundError:
                return None
            return _entity_dict(email)

    async def list_events(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        from_date: Any = None,
        to_date: Any = None,
        forward_headers: Any = None,
        tenant_id: Optional[str] = None,
    ) -> dict:
        with _db_session() as db:
            result = await _membrane_use_cases(db).list_events(
                user_id,
                _tenant_id(forward_headers, tenant_id),
                skip,
                limit,
                _parse_datetime(from_date),
                _parse_datetime(to_date),
            )
            return {
                "items": [_entity_dict(item) for item in result.items],
                "total": result.total,
                "skip": result.skip,
                "limit": result.limit,
            }

    async def get_event(self, event_id: str, user_id: str, forward_headers: Any = None, tenant_id: Optional[str] = None) -> Optional[dict]:
        with _db_session() as db:
            try:
                event = await _membrane_use_cases(db).get_event(
                    event_id,
                    user_id,
                    _tenant_id(forward_headers, tenant_id),
                )
            except EventNotFoundError:
                return None
            return _entity_dict(event)


integration_settings_client = IntegrationSettingsClient()
connection_client = ConnectionClient()
email_crud_client = EmailCrudClient()
event_crud_client = EventCrudClient()
membrane_crud_client = MembraneCrudClient()
