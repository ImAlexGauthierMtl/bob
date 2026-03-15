"""Standardized domain event schemas."""

from typing import Dict, Any, Optional
from . import Event


def _make_event(domain: str, action: str, entity_id: str, payload: Dict[str, Any], source: str = "") -> Event:
    return Event(
        event_type=f"{domain}.{action}",
        payload={"entity_id": entity_id, **payload},
        source=source,
    )


def user_created(user_id: str, data: Dict[str, Any], source: str = "user~backend-api") -> Event:
    return _make_event("user", "created", user_id, data, source)

def user_updated(user_id: str, data: Dict[str, Any], source: str = "user~backend-api") -> Event:
    return _make_event("user", "updated", user_id, data, source)

def user_deleted(user_id: str, data: Optional[Dict[str, Any]] = None, source: str = "user~backend-api") -> Event:
    return _make_event("user", "deleted", user_id, data or {}, source)


def contact_created(contact_id: str, data: Dict[str, Any], source: str = "contact~backend-api") -> Event:
    return _make_event("contact", "created", contact_id, data, source)

def contact_updated(contact_id: str, data: Dict[str, Any], source: str = "contact~backend-api") -> Event:
    return _make_event("contact", "updated", contact_id, data, source)

def contact_deleted(contact_id: str, data: Optional[Dict[str, Any]] = None, source: str = "contact~backend-api") -> Event:
    return _make_event("contact", "deleted", contact_id, data or {}, source)


def org_created(org_id: str, data: Dict[str, Any], source: str = "org~backend-api") -> Event:
    return _make_event("organization", "created", org_id, data, source)

def org_updated(org_id: str, data: Dict[str, Any], source: str = "org~backend-api") -> Event:
    return _make_event("organization", "updated", org_id, data, source)

def org_deleted(org_id: str, data: Optional[Dict[str, Any]] = None, source: str = "org~backend-api") -> Event:
    return _make_event("organization", "deleted", org_id, data or {}, source)


def opportunity_created(opp_id: str, data: Dict[str, Any], source: str = "opportunity~backend-api") -> Event:
    return _make_event("opportunity", "created", opp_id, data, source)

def opportunity_updated(opp_id: str, data: Dict[str, Any], source: str = "opportunity~backend-api") -> Event:
    return _make_event("opportunity", "updated", opp_id, data, source)

def opportunity_won(opp_id: str, data: Dict[str, Any], source: str = "opportunity~backend-api") -> Event:
    return _make_event("opportunity", "won", opp_id, data, source)

def opportunity_lost(opp_id: str, data: Dict[str, Any], source: str = "opportunity~backend-api") -> Event:
    return _make_event("opportunity", "lost", opp_id, data, source)


def activity_created(activity_id: str, data: Dict[str, Any], source: str = "activity~backend-api") -> Event:
    return _make_event("activity", "created", activity_id, data, source)

def activity_updated(activity_id: str, data: Dict[str, Any], source: str = "activity~backend-api") -> Event:
    return _make_event("activity", "updated", activity_id, data, source)


def product_created(product_id: str, data: Dict[str, Any], source: str = "product~backend-api") -> Event:
    return _make_event("product", "created", product_id, data, source)

def product_updated(product_id: str, data: Dict[str, Any], source: str = "product~backend-api") -> Event:
    return _make_event("product", "updated", product_id, data, source)


def email_received(email_id: str, data: Dict[str, Any], source: str = "email~backend-api") -> Event:
    return _make_event("email", "received", email_id, data, source)

def email_synced(email_id: str, data: Dict[str, Any], source: str = "email~backend-api") -> Event:
    return _make_event("email", "synced", email_id, data, source)


def agent_config_updated(config_id: str, data: Dict[str, Any], source: str = "agent~backend-api") -> Event:
    return _make_event("agent", "config_updated", config_id, data, source)

def agent_training_completed(training_id: str, data: Dict[str, Any], source: str = "agent~backend-api") -> Event:
    return _make_event("agent", "training_completed", training_id, data, source)


def workflow_created(workflow_id: str, data: Dict[str, Any], source: str = "workflow~backend-api") -> Event:
    return _make_event("workflow", "created", workflow_id, data, source)

def workflow_executed(execution_id: str, data: Dict[str, Any], source: str = "workflow~backend-api") -> Event:
    return _make_event("workflow", "executed", execution_id, data, source)


def kb_article_created(article_id: str, data: Dict[str, Any], source: str = "kb~backend-api") -> Event:
    return _make_event("kb", "article_created", article_id, data, source)

def kb_article_updated(article_id: str, data: Dict[str, Any], source: str = "kb~backend-api") -> Event:
    return _make_event("kb", "article_updated", article_id, data, source)


def usage_recorded(log_id: str, data: Dict[str, Any], source: str = "usage~backend-api") -> Event:
    return _make_event("usage", "recorded", log_id, data, source)
