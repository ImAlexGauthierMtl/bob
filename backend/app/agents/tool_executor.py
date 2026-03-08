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
    
    # ── Track tool execution for audit ──
    try:
        from app.middleware.usage_tracker import UsageTracker
        from app.domain.entities.usage_transaction import TriggerSource
        _tracker = UsageTracker(db)
        _trigger = TriggerSource.BOB_VOICE if user_context.get("source") == "voice" else TriggerSource.BOB_CHAT
        _tracker.track_tool(
            tenant_id=user_context.get("tenant_id", ""),
            user_id=user_context.get("user_id", ""),
            tool_name=tool_name,
            trigger_source=_trigger,
            trigger_id=user_context.get("session_id", ""),
            correlation_id=user_context.get("intent_id", user_context.get("session_id", "")),
            correlation_label=user_context.get("intent_label", ""),
            metadata={"args_keys": list(args.keys())},
        )
    except Exception as _te:
        logger.warning("tool_usage_tracking_failed", error=str(_te))
    
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
            filtered = [o for o in items if not query or query in (o.name + (o.website or "")).lower()]
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
                    "website": o.website,
                }
                for o in orgs if not query or query in (o.name + (o.website or "")).lower()
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
        from app.domain.entities.contact import Contact
        from app.domain.entities.organization import Organization

        first_name = args.get("first_name", "")
        last_name = args.get("last_name", "")
        email = args.get("email", "")
        phone = args.get("phone", "")
        company = args.get("company", "")

        # ── Organization resolution strategy ──
        # Priority: 1) company name match  2) email domain match
        org_id = None
        org_name = ""
        org_created = False

        if company:
            org = db.query(Organization).filter(
                Organization.tenant_id == user_context["tenant_id"],
                Organization.name.ilike(f"%{company}%"),
            ).first()
            if org:
                org_id = org.id
                org_name = org.name

        # Fallback: extract domain from email and match by website
        if not org_id and email and "@" in email:
            email_domain = email.split("@")[1].lower()
            # Search by website containing the domain
            org = db.query(Organization).filter(
                Organization.tenant_id == user_context["tenant_id"],
                Organization.website.ilike(f"%{email_domain}%"),
            ).first()
            if org:
                org_id = org.id
                org_name = org.name
            else:
                # Auto-create organization from domain
                org = Organization(
                    name=email_domain.split(".")[0].upper(),
                    website=email_domain,
                    tenant_id=user_context["tenant_id"],
                    created_by=user_context.get("user_email", "bob"),
                )
                db.add(org)
                db.commit()
                db.refresh(org)
                org_id = org.id
                org_name = org.name
                org_created = True
                logger.info("tool_org_auto_created", org_id=str(org.id), domain=email_domain)

        contact = Contact(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            organization_id=org_id,
            tenant_id=user_context["tenant_id"],
            created_by=user_context.get("user_email", "bob"),
        )
        db.add(contact)
        db.commit()
        db.refresh(contact)

        logger.info(
            "tool_contact_created",
            contact_id=str(contact.id),
            email=email,
            organization=org_name or None,
            user_id=user_context["user_id"],
        )

        result_msg = f"Contact created: {first_name} {last_name}"
        if email:
            result_msg += f" ({email})"
        if org_created:
            result_msg += f" — auto-created organization '{org_name}' from domain"
        elif org_name:
            result_msg += f" — linked to '{org_name}'"
        elif company:
            result_msg += f" — organization '{company}' not found"

        return {"status": "ok", "contact_id": str(contact.id), "organization_id": str(org_id) if org_id else None, "org_created": org_created, "message": result_msg}

    elif tool_name == "create_organization":
        from app.domain.entities.organization import Organization

        name = args.get("name", "")
        org = Organization(
            name=name,
            tenant_id=user_context["tenant_id"],
            created_by=user_context.get("user_email", "bob"),
        )
        if args.get("website"):
            org.website = args["website"]
        db.add(org)
        db.commit()
        db.refresh(org)

        logger.info(
            "tool_organization_created",
            org_id=str(org.id),
            name=name,
            user_id=user_context["user_id"],
        )
        return {"status": "ok", "org_id": str(org.id), "message": f"Organization created: {name}"}

    elif tool_name == "create_opportunity":
        from app.domain.entities.opportunity import Opportunity
        from app.domain.entities.organization import Organization
        from app.domain.entities.contact import Contact

        name = args.get("name", "")
        org_id = args.get("organization_id")
        contact_id = args.get("contact_id")
        stage = args.get("stage", "PROSPECTING")
        source = args.get("source", "Bob")
        amount = args.get("amount")

        # Validate org exists
        if org_id:
            org = db.query(Organization).filter(
                Organization.id == org_id,
                Organization.tenant_id == user_context["tenant_id"],
            ).first()
            if not org:
                return {"status": "error", "message": f"Organization {org_id} not found"}

        # Validate contact exists
        if contact_id:
            contact = db.query(Contact).filter(
                Contact.id == contact_id,
                Contact.tenant_id == user_context["tenant_id"],
            ).first()
            if not contact:
                return {"status": "error", "message": f"Contact {contact_id} not found"}

        opp = Opportunity(
            name=name,
            organization_id=org_id,
            contact_id=contact_id,
            stage=stage,
            source=source,
            amount=amount,
            tenant_id=user_context["tenant_id"],
            created_by=user_context.get("user_email", "bob"),
        )
        db.add(opp)
        db.commit()
        db.refresh(opp)

        logger.info(
            "tool_opportunity_created",
            opp_id=str(opp.id),
            name=name,
            org_id=org_id,
            user_id=user_context["user_id"],
        )
        return {"status": "ok", "opportunity_id": str(opp.id), "message": f"Opportunity created: {name}"}

    elif tool_name == "link_product_to_opportunity":
        from app.domain.entities.opportunity import Opportunity
        from app.domain.entities.product import Product
        from app.domain.entities.opportunity_product import OpportunityProduct

        opp_id = args.get("opportunity_id", "")
        product_id = args.get("product_id", "")
        quantity = args.get("quantity", 1)

        # Validate opportunity
        opp = db.query(Opportunity).filter(
            Opportunity.id == opp_id,
            Opportunity.tenant_id == user_context["tenant_id"],
        ).first()
        if not opp:
            return {"status": "error", "message": f"Opportunity {opp_id} not found"}

        # Validate product
        product = db.query(Product).filter(
            Product.id == product_id,
            Product.tenant_id == user_context["tenant_id"],
        ).first()
        if not product:
            return {"status": "error", "message": f"Product {product_id} not found"}

        line = OpportunityProduct(
            opportunity_id=opp_id,
            product_id=product_id,
            quantity=quantity,
            unit_price=product.unit_price,
            tenant_id=user_context["tenant_id"],
            created_by=user_context.get("user_email", "bob"),
        )
        db.add(line)
        db.commit()
        db.refresh(line)

        logger.info(
            "tool_product_linked",
            line_id=str(line.id),
            opp_id=opp_id,
            product=product.name,
            user_id=user_context["user_id"],
        )
        return {
            "status": "ok",
            "line_id": str(line.id),
            "message": f"Product '{product.name}' linked to opportunity (qty={quantity}, price={product.unit_price})",
        }

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
