"""Universal Tool Executor for Bob Agent.

Maintains a single execute_bob_tool function used by both the text (Groq/REST)
and voice (Pipecat/WebSocket) pipelines, ensuring capabilities are perfectly synced.
"""

import json
import structlog
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

logger = structlog.get_logger(__name__)


async def execute_bob_tool(tool_name: str, args: Dict[str, Any], user_context: dict, db: Session) -> dict:
    """Execute a Bob CRM tool and return its standardized response.
    
    Args:
        tool_name: The name of the function/tool called by the LLM.
        args: The arguments passed by the LLM as a dictionary.
        user_context: Context dictionary containing user_id, tenant_id, session_id, etc.
        db: SQLAlchemy database session.
        
    Returns:
        dict: Standardized results object, usually containing {"status": "ok", "data": ...}
              or {"status": "error", "message": "..."}.
    """
    logger.info("execute_bob_tool_start", tool=tool_name, args=args, user=user_context.get("user_id"))
    
    # ── 1. Search APIs ──────────────────────────────────────────
    if tool_name == "search_contacts":
        from app.domain.entities.contact import Contact
        query = args.get("query", "").lower()
        limit = args.get("limit", 5)
        
        # Simple ilike filter
        contacts = db.query(Contact).filter(
            Contact.tenant_id == user_context["tenant_id"]
        ).limit(limit).all()
        
        # In-memory filter fallback
        filtered = [
            c for c in contacts 
            if query in (c.first_name + c.last_name + (c.email or "")).lower()
        ][:limit]
        
        return {
            "status": "ok",
            "results": [
                {
                    "id": str(c.id),
                    "name": f"{c.first_name} {c.last_name}",
                    "email": c.email,
                }
                for c in (filtered if query else contacts[:limit])
            ]
        }

    elif tool_name == "search_and_open_entity":
        entity_type = args.get("entity", "organization")
        query = args.get("query", "").lower()
        
        # 1. Dispatch search internally
        if entity_type == "organization":
            from app.domain.entities.organization import Organization
            items = db.query(Organization).filter(
                Organization.tenant_id == user_context["tenant_id"]
            ).limit(5).all()
            filtered = [o for o in items if not query or query in (o.name + (o.domain or "")).lower()]
            base_route = "organizations"
        elif entity_type == "contact":
            from app.domain.entities.contact import Contact
            items = db.query(Contact).filter(
                Contact.tenant_id == user_context["tenant_id"]
            ).limit(5).all()
            filtered = [c for c in items if not query or query in (c.first_name + c.last_name + (c.email or "")).lower()]
            base_route = "contacts"
        elif entity_type == "opportunity":
            from app.domain.entities.opportunity import Opportunity
            items = db.query(Opportunity).filter(
                Opportunity.tenant_id == user_context["tenant_id"]
            ).limit(5).all()
            filtered = [o for o in items if not query or query in (o.name).lower()]
            base_route = "opportunities"
        else:
            return {"status": "error", "message": f"Unsupported entity {entity_type}"}
            
        if filtered:
            return {
                "status": "ok",
                "action": "navigate",
                "page": f"{base_route}/{filtered[0].id}",
                "message": f"Opened {entity_type} details."
            }
        else:
            return {
                "status": "error",
                "message": f"Could not find {entity_type} matching '{query}'."
            }

    elif tool_name == "search_organizations":
        from app.domain.entities.organization import Organization
        query = args.get("query", "").lower()
        limit = args.get("limit", 5)
        orgs = db.query(Organization).filter(
            Organization.tenant_id == user_context["tenant_id"]
        ).limit(limit).all()
        return {
            "status": "ok",
            "results": [
                {
                    "id": str(o.id),
                    "name": o.name,
                    "domain": o.domain,
                }
                for o in orgs if not query or query in (o.name + (o.domain or "")).lower()
            ][:limit]
        }

    elif tool_name == "get_pipeline_stats":
        from app.domain.entities.opportunity import Opportunity
        from sqlalchemy import func
        stats = db.query(
            Opportunity.stage,
            func.count(Opportunity.id),
            func.sum(Opportunity.amount)
        ).filter(
            Opportunity.tenant_id == user_context["tenant_id"]
        ).group_by(Opportunity.stage).all()
        return {
            "status": "ok",
            "stages": [
                {"stage": s[0], "count": s[1], "value": float(s[2] or 0)} 
                for s in stats
            ]
        }
        
    # ── 2. Create APIs ──────────────────────────────────────────
    elif tool_name == "create_contact":
        return {"status": "error", "message": "Creation via AI is temporarily restricted. Please use the create dialog in the UI."}
        
    elif tool_name == "create_organization":
        return {"status": "error", "message": "Creation via AI is temporarily restricted. Please use the create dialog in the UI."}

    # ── 3. Profile / Context Knowledge ──────────────────────────
    elif tool_name == "bcc_update_profile":
        from app.domain.entities.bcc_entities import BccProfileEntry
        from app.domain.entities.base import generate_uuid

        entity_type = args.get("entity_type", "")
        entity_id = args.get("entity_id", "")
        section = args.get("section", "")
        content = args.get("content", "")
        perspective = args.get("perspective", "general")

        # Get user name for contributor display
        from app.domain.entities.user import User
        user = db.query(User).filter(User.id == user_context["user_id"]).first()
        contributor_name = "Bob" if not user else f"{user.first_name} {user.last_name} (via Bob)"

        # Find latest version for this entity+section+perspective
        latest = (
            db.query(BccProfileEntry)
            .filter(
                and_(
                    BccProfileEntry.entity_type == entity_type,
                    BccProfileEntry.entity_id == entity_id,
                    BccProfileEntry.section == section,
                    BccProfileEntry.perspective == perspective,
                )
            )
            .order_by(BccProfileEntry.version.desc())
            .first()
        )

        new_version = (latest.version + 1) if latest else 1

        # Deactivate previous active version
        if latest and latest.is_active:
            latest.is_active = False

        entry = BccProfileEntry(
            id=generate_uuid(),
            entity_type=entity_type,
            entity_id=entity_id,
            section=section,
            content=content,
            perspective=perspective,
            version=new_version,
            is_active=True,
            contributed_by=user_context["user_id"],
            contributor_name=contributor_name,
            contribution_method="conversation",
            conversation_id=user_context.get("session_id"),
        )
        db.add(entry)
        db.commit()

        logger.info(
            "bcc_profile_updated",
            entity_type=entity_type,
            entity_id=entity_id,
            section=section,
            version=new_version,
        )
        return {
            "status": "ok",
            "message": f"Profile updated: {entity_type}/{entity_id} section='{section}' v{new_version}",
        }

    elif tool_name == "bcc_get_profile":
        from app.domain.entities.bcc_entities import BccProfileEntry

        entity_type = args.get("entity_type", "")
        entity_id = args.get("entity_id", "")

        entries = (
            db.query(BccProfileEntry)
            .filter(
                and_(
                    BccProfileEntry.entity_type == entity_type,
                    BccProfileEntry.entity_id == entity_id,
                    BccProfileEntry.is_active == True,
                )
            )
            .order_by(BccProfileEntry.section)
            .all()
        )

        if not entries:
            return {"status": "ok", "profile": [], "message": "No profile data found."}

        profile = []
        for e in entries:
            profile.append({
                "section": e.section,
                "perspective": e.perspective,
                "version": e.version,
                "content": e.content,
            })
        return {"status": "ok", "profile": profile}

    elif tool_name == "upsert_bcc_profile_from_interaction":
        # Knowledge extractor module not yet implemented — safe stub
        logger.warning("tool_not_implemented", tool=tool_name)
        return {"status": "error", "message": "Knowledge extractor not yet available."}

    elif tool_name == "get_bcc_profile_context":
        # Knowledge extractor module not yet implemented — safe stub
        logger.warning("tool_not_implemented", tool=tool_name)
        return {"status": "ok", "markdown": "No specific knowledge profile found yet."}
        
    # ── 4. Training Overlay Tools ──────────────────────────────
    elif tool_name == "save_training_note":
        from app.domain.entities.training_models import TrainingNote
        note = TrainingNote(
            session_id=args.get("session_id"),
            user_id=user_context["user_id"],
            slide_id=args.get("slide_id"),
            content=args.get("content"),
            note_type=args.get("note_type", "insight"),
        )
        db.add(note)
        db.commit()
        return {"status": "ok", "id": str(note.id)}
        
    elif tool_name == "save_missing_element":
        from app.domain.entities.training_models import TrainingMissingElement
        missing = TrainingMissingElement(
            session_id=args.get("session_id"),
            user_id=user_context["user_id"],
            label=args.get("label"),
            category=args.get("category", "feature"),
            description=args.get("description"),
        )
        db.add(missing)
        db.commit()
        return {"status": "ok", "id": str(missing.id)}

    elif tool_name == "get_recent_activities":
        from app.domain.entities.activity import Activity
        activities = db.query(Activity).filter(
            Activity.tenant_id == user_context["tenant_id"]
        ).order_by(Activity.created_at.desc()).limit(10).all()
        return {
            "status": "ok", 
            "activities": [
                {
                    "title": a.title, 
                    "type": a.activity_type, 
                    "due": str(a.due_date) if a.due_date else None
                } 
                for a in activities
            ]
        }

    # ── 5. UI Tools (handled here for voice fallback) ──────────
    elif tool_name == "ui_switch_tab":
        return {
            "status": "ok",
            "action": "ui_switch_tab",
            "tab_name": args.get("tab_name", ""),
        }

    else:
        logger.warning("execute_bob_tool_unknown", tool=tool_name)
        return {"status": "error", "message": f"Unknown tool: {tool_name}"}
