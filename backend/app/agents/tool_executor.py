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
        from sqlalchemy import or_
        query = args.get("query", "").lower().strip()
        limit = args.get("limit", 5)
        
        q = db.query(Contact).filter(
            Contact.tenant_id == user_context["tenant_id"]
        )
        if query:
            q = q.filter(
                or_(
                    Contact.first_name.ilike(f"%{query}%"),
                    Contact.last_name.ilike(f"%{query}%"),
                    Contact.email.ilike(f"%{query}%"),
                )
            )
        contacts = q.limit(limit).all()
        
        return {
            "status": "ok",
            "results": [
                {
                    "id": str(c.id),
                    "name": f"{c.first_name} {c.last_name}",
                    "email": c.email,
                }
                for c in contacts
            ]
        }

    elif tool_name == "search_and_open_entity":
        entity_type = args.get("entity", "organization")
        query = args.get("query", "").lower().strip()
        
        if not query:
            return {"status": "error", "message": "No search query provided."}
        
        # 1. Dispatch search using proper DB ilike queries
        if entity_type == "organization":
            from app.domain.entities.organization import Organization
            filtered = db.query(Organization).filter(
                Organization.tenant_id == user_context["tenant_id"],
                Organization.name.ilike(f"%{query}%"),
            ).limit(5).all()
            base_route = "organizations"
        elif entity_type == "contact":
            from app.domain.entities.contact import Contact
            from sqlalchemy import or_
            filtered = db.query(Contact).filter(
                Contact.tenant_id == user_context["tenant_id"],
                or_(
                    Contact.first_name.ilike(f"%{query}%"),
                    Contact.last_name.ilike(f"%{query}%"),
                    Contact.email.ilike(f"%{query}%"),
                ),
            ).limit(5).all()
            base_route = "contacts"
        elif entity_type == "opportunity":
            from app.domain.entities.opportunity import Opportunity
            filtered = db.query(Opportunity).filter(
                Opportunity.tenant_id == user_context["tenant_id"],
                Opportunity.name.ilike(f"%{query}%"),
            ).limit(5).all()
            base_route = "opportunities"
        else:
            return {"status": "error", "message": f"Unsupported entity {entity_type}"}
            
        if filtered:
            logger.info(
                "search_and_open_entity_found",
                entity_type=entity_type,
                query=query,
                result_id=str(filtered[0].id),
                result_count=len(filtered),
            )
            return {
                "status": "ok",
                "action": "navigate",
                "page": f"{base_route}/{filtered[0].id}",
                "message": f"Opened {entity_type} details."
            }
        else:
            logger.info(
                "search_and_open_entity_not_found",
                entity_type=entity_type,
                query=query,
            )
            return {
                "status": "error",
                "message": f"Could not find {entity_type} matching '{query}'."
            }

    elif tool_name == "search_organizations":
        from app.domain.entities.organization import Organization
        query = args.get("query", "").lower()
        limit = args.get("limit", 5)
        
        q = db.query(Organization).filter(
            Organization.tenant_id == user_context["tenant_id"]
        )
        if query:
            q = q.filter(Organization.name.ilike(f"%{query}%"))
        orgs = q.limit(limit).all()
        
        return {
            "status": "ok",
            "results": [
                {
                    "id": str(o.id),
                    "name": o.name,
                    "industry": o.industry,
                    "phone": o.phone,
                    "website": o.website,
                }
                for o in orgs
            ]
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

        # ── Deduplication check: prevent creating duplicate orgs ──
        existing = db.query(Organization).filter(
            Organization.tenant_id == user_context["tenant_id"],
            Organization.name.ilike(f"%{name}%"),
        ).limit(5).all()

        if existing:
            results = [
                {"id": str(o.id), "name": o.name, "industry": o.industry, "phone": o.phone}
                for o in existing
            ]
            logger.info(
                "create_org_intercepted_existing",
                name=name,
                count=len(existing),
                tenant_id=user_context["tenant_id"],
            )
            return {
                "status": "already_exists",
                "message": f"Organization(s) matching '{name}' already exist in the CRM. Use the existing org_id instead of creating a duplicate.",
                "existing_organizations": results,
            }

        # No match — proceed with creation (all 16 fields)
        org = Organization(
            name=name,
            tenant_id=user_context["tenant_id"],
            created_by=user_context.get("user_email", "bob"),
        )
        _ORG_FIELDS = [
            "website", "industry", "phone", "email",
            "address_street", "address_city", "address_state",
            "address_country", "address_postal_code",
            "status", "org_type", "employee_count", "annual_revenue",
            "description", "linkedin_url",
        ]
        for field in _ORG_FIELDS:
            val = args.get(field)
            if val is not None:
                setattr(org, field, val)
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

        # Build artifact fields
        artifact_fields = [
            {"label": "Nom", "value": name},
            {"label": "Étape", "value": stage},
            {"label": "Source", "value": source},
        ]
        if amount:
            artifact_fields.append({"label": "Montant", "value": f"${amount:,.2f}"})
        if org_id:
            org_name = ""
            try:
                _org = db.query(Organization).filter(Organization.id == org_id).first()
                if _org:
                    org_name = _org.name
            except Exception:
                pass
            if org_name:
                artifact_fields.append({"label": "Organisation", "value": org_name})
        if contact_id:
            contact_name = ""
            try:
                _ct = db.query(Contact).filter(Contact.id == contact_id).first()
                if _ct:
                    contact_name = f"{_ct.first_name} {_ct.last_name}"
            except Exception:
                pass
            if contact_name:
                artifact_fields.append({"label": "Contact", "value": contact_name})

        return {
            "status": "ok",
            "opportunity_id": str(opp.id),
            "message": f"Opportunity created: {name}",
            "artifact": {
                "type": "opportunity",
                "title": name,
                "fields": artifact_fields,
                "status": "complete",
                "entity_id": str(opp.id),
            },
        }

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
        # Delegate to the real bcc_update_profile implementation
        return await execute_bob_tool("bcc_update_profile", args, user_context, db)

    elif tool_name == "get_bcc_profile_context":
        # Delegate to the real bcc_get_profile implementation
        return await execute_bob_tool("bcc_get_profile", args, user_context, db)
        
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

    # ── 6. change_training_slide ───────────────────────────────
    elif tool_name == "change_training_slide":
        result = {"action": "change_slide", "direction": args.get("direction", "next")}
        if args.get("direction") == "goto" and args.get("slide_number"):
            result["slide_number"] = args["slide_number"]
        return {"status": "ok", **result}

    # ── 7. invoke_deep_agent ───────────────────────────────────
    elif tool_name == "invoke_deep_agent":
        from app.agents.deep_agent_graph import run_deep_agent
        from app.domain.entities.user import User as _UserDA

        user = db.query(_UserDA).filter(_UserDA.id == user_context["user_id"]).first()
        if not user:
            return {"status": "error", "message": "User not found"}

        try:
            result = await run_deep_agent(
                instruction=args.get("instruction", ""),
                tenant_id=user.tenant_id,
                user_id=user_context["user_id"],
                user_email=user.email or "unknown",
            )
        except Exception as e:
            logger.error("invoke_deep_agent_failed", error=str(e))
            return {"status": "error", "message": f"Deep Agent failed: {str(e)}"}

        if result.get("error"):
            return {"status": "error", "message": f"Deep Agent error: {result['error']}"}

        return {
            "status": "ok",
            "message": (
                f"Deep Agent completed: {result.get('domains_created', 0)} domains, "
                f"{result.get('intents_created', 0)} intents, "
                f"{result.get('tasks_created', 0)} tasks created."
            ),
            "review": result.get("review", {}),
        }

    # ── 8. enrich_account ──────────────────────────────────────
    elif tool_name == "enrich_account":
        from app.domain.entities.organization import Organization as _OrgEnrich
        from app.application.use_cases.enrich_organization import EnrichOrganizationUseCase
        from app.domain.entities.user import User as _UserEnrich

        user = db.query(_UserEnrich).filter(_UserEnrich.id == user_context["user_id"]).first()
        if not user:
            return {"status": "error", "message": "User not found"}

        organization_id = args.get("organization_id", "")
        org = db.query(_OrgEnrich).filter(
            _OrgEnrich.id == organization_id,
            _OrgEnrich.tenant_id == user.tenant_id,
        ).first()

        if not org:
            return {"status": "error", "message": f"Organization {organization_id} not found"}

        logger.info("enrich_account_tool_start", org_id=organization_id, org_name=org.name)

        use_case = EnrichOrganizationUseCase(db)
        result = await use_case.execute(
            org_id=organization_id,
            tenant_id=user.tenant_id,
            user_email=user.email,
        )

        # Build artifact fields from enrichment results
        artifact_fields = []
        fields = result.get("fields", {})
        if fields.get("industry"):
            artifact_fields.append({"label": "Industry", "value": fields["industry"]})
        if fields.get("employee_count"):
            artifact_fields.append({"label": "Employees", "value": str(fields["employee_count"])})
        if fields.get("annual_revenue"):
            artifact_fields.append({"label": "Revenue", "value": str(fields["annual_revenue"])})
        if fields.get("description"):
            desc = fields["description"]
            artifact_fields.append({"label": "Description", "value": desc[:200] + "..." if len(desc) > 200 else desc})
        if fields.get("linkedin_url"):
            artifact_fields.append({"label": "LinkedIn", "value": fields["linkedin_url"]})
        if fields.get("website"):
            artifact_fields.append({"label": "Website", "value": fields["website"]})

        hunter_contacts = result.get("hunter_contacts", [])
        if hunter_contacts:
            contact_lines = []
            for hc in hunter_contacts[:5]:
                name = f"{hc.get('first_name', '')} {hc.get('last_name', '')}".strip()
                pos = hc.get("position", "")
                email = hc.get("email", "")
                contact_lines.append(f"{name} — {pos} ({email})" if pos else f"{name} ({email})")
            artifact_fields.append({
                "label": f"Contacts ({len(hunter_contacts)})",
                "value": "\n".join(contact_lines),
            })

        intelligence = result.get("intelligence_sections")
        if intelligence and isinstance(intelligence, int) and intelligence > 0:
            artifact_fields.append({"label": "Intelligence", "value": f"{intelligence} sections generated"})

        artifact = {
            "type": "enrichment",
            "title": f"🔍 Enrichment — {org.name}",
            "status": "complete" if result.get("status") == "done" else result.get("status", "partial"),
            "fields": artifact_fields,
            "links": [
                {"label": "View Account", "url": f"/organizations/{organization_id}", "icon": "fa-building"},
            ],
        }

        logger.info(
            "enrich_account_tool_done",
            org_id=organization_id,
            status=result.get("status"),
            fields_updated=result.get("fields_updated"),
            contacts_created=result.get("contacts_created"),
        )

        return {
            "status": result.get("status", "done"),
            "message": f"Enrichment complete for {org.name}. {result.get('fields_updated', 0)} fields updated, {result.get('contacts_created', 0)} contacts created.",
            "artifact": artifact,
        }

    # ── 9. search_rolodex ──────────────────────────────────────
    elif tool_name == "search_rolodex":
        import httpx
        from app.config import settings

        query = args.get("query", "").strip()
        if not query:
            return {"status": "error", "message": "Please provide a query to search Bob's Rolodex."}

        logger.info("search_rolodex_start", query=query)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    "https://google.serper.dev/maps",
                    json={"q": query, "num": 10},
                    headers={
                        "X-API-KEY": settings.serper_api_key,
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()

            places = data.get("places", [])
            if not places:
                return {"status": "ok", "message": f'No results found in Bob\'s Rolodex for "{query}".', "results": []}

            results = []
            for place in places:
                results.append({
                    "title": place.get("title", "Unknown"),
                    "address": place.get("address", "N/A"),
                    "phone": place.get("phoneNumber", ""),
                    "website": place.get("website", ""),
                    "industry": place.get("type", ""),
                    "rating": place.get("rating"),
                })

            logger.info("search_rolodex_done", query=query, results=len(places))
            return {"status": "ok", "message": f"Found {len(places)} result(s).", "results": results}

        except Exception as e:
            logger.error("search_rolodex_error", query=query, error=str(e))
            return {"status": "error", "message": f"Rolodex search failed: {str(e)}"}

    # ── 11. Organization management tools ───────────────────────

    elif tool_name == "get_organization":
        from app.domain.entities.organization import Organization as _OrgGet
        from app.domain.entities.contact import Contact as _ContactGet
        from app.domain.entities.opportunity import Opportunity as _OppGet

        org_id = args.get("organization_id", "")
        org = db.query(_OrgGet).filter(
            _OrgGet.id == org_id,
            _OrgGet.tenant_id == user_context["tenant_id"],
        ).first()

        if not org:
            return {"status": "error", "message": f"Organization {org_id} not found"}

        contacts_count = db.query(_ContactGet).filter(
            _ContactGet.organization_id == org_id,
            _ContactGet.tenant_id == user_context["tenant_id"],
        ).count()
        opp_count = db.query(_OppGet).filter(
            _OppGet.organization_id == org_id,
            _OppGet.tenant_id == user_context["tenant_id"],
        ).count()

        return {
            "status": "ok",
            "organization": {
                "id": str(org.id),
                "name": org.name,
                "industry": org.industry,
                "website": org.website,
                "phone": org.phone,
                "email": org.email,
                "address_street": org.address_street,
                "address_city": org.address_city,
                "address_state": org.address_state,
                "address_country": org.address_country,
                "address_postal_code": org.address_postal_code,
                "status": org.status.value if org.status else None,
                "org_type": org.org_type.value if org.org_type else None,
                "employee_count": org.employee_count,
                "annual_revenue": org.annual_revenue,
                "description": org.description,
                "linkedin_url": org.linkedin_url,
                "logo_url": org.logo_url,
                "ai_enriched": org.ai_enriched,
                "owner_id": org.owner_id,
                "created_at": str(org.created_at) if org.created_at else None,
                "updated_at": str(org.updated_at) if org.updated_at else None,
                "contacts_count": contacts_count,
                "opportunities_count": opp_count,
            },
        }

    elif tool_name == "update_organization":
        from app.domain.entities.organization import Organization as _OrgUpd

        org_id = args.get("organization_id", "")
        org = db.query(_OrgUpd).filter(
            _OrgUpd.id == org_id,
            _OrgUpd.tenant_id == user_context["tenant_id"],
        ).first()

        if not org:
            return {"status": "error", "message": f"Organization {org_id} not found"}

        _UPD_FIELDS = [
            "name", "website", "industry", "phone", "email",
            "address_street", "address_city", "address_state",
            "address_country", "address_postal_code",
            "status", "org_type", "employee_count", "annual_revenue",
            "description", "linkedin_url",
        ]
        updated_fields = []
        for field in _UPD_FIELDS:
            val = args.get(field)
            if val is not None:
                setattr(org, field, val)
                updated_fields.append(field)

        if not updated_fields:
            return {"status": "error", "message": "No fields to update provided."}

        org.updated_by = user_context.get("user_email", "bob")
        db.commit()
        db.refresh(org)

        logger.info("tool_organization_updated", org_id=org_id, fields=updated_fields)
        return {
            "status": "ok",
            "message": f"Organization '{org.name}' updated: {', '.join(updated_fields)}",
            "org_id": str(org.id),
        }

    elif tool_name == "delete_organization":
        from app.domain.entities.organization import Organization as _OrgDel
        from app.middleware.dependency_guard import guard_delete

        org_id = args.get("organization_id", "")
        org = db.query(_OrgDel).filter(
            _OrgDel.id == org_id,
            _OrgDel.tenant_id == user_context["tenant_id"],
        ).first()

        if not org:
            return {"status": "error", "message": f"Organization {org_id} not found"}

        try:
            guard_delete(db, "organizations", org_id, user_context["tenant_id"])
        except Exception as e:
            return {
                "status": "error",
                "message": f"Cannot delete '{org.name}': {str(e)}. Remove linked records first.",
            }

        org_name = org.name
        org.deleted_by = user_context.get("user_email", "bob")
        org.is_deleted = True
        db.commit()

        logger.info("tool_organization_deleted", org_id=org_id, name=org_name)
        return {"status": "ok", "message": f"Organization '{org_name}' has been deleted."}

    elif tool_name == "list_organization_contacts":
        from app.domain.entities.contact import Contact as _ContactList

        org_id = args.get("organization_id", "")
        limit = min(int(args.get("limit", 20)), 50)

        contacts = db.query(_ContactList).filter(
            _ContactList.organization_id == org_id,
            _ContactList.tenant_id == user_context["tenant_id"],
        ).limit(limit).all()

        return {
            "status": "ok",
            "organization_id": org_id,
            "contacts": [
                {
                    "id": str(c.id),
                    "first_name": c.first_name,
                    "last_name": c.last_name,
                    "email": c.email,
                    "phone": c.phone,
                    "job_title": getattr(c, "job_title", None),
                }
                for c in contacts
            ],
            "count": len(contacts),
        }

    elif tool_name == "list_organization_opportunities":
        from app.domain.entities.opportunity import Opportunity as _OppList

        org_id = args.get("organization_id", "")
        limit = min(int(args.get("limit", 20)), 50)

        opps = db.query(_OppList).filter(
            _OppList.organization_id == org_id,
            _OppList.tenant_id == user_context["tenant_id"],
        ).order_by(_OppList.created_at.desc()).limit(limit).all()

        return {
            "status": "ok",
            "organization_id": org_id,
            "opportunities": [
                {
                    "id": str(o.id),
                    "name": o.name,
                    "stage": o.stage.value if o.stage else None,
                    "amount": o.amount,
                    "expected_close_date": str(o.expected_close_date) if getattr(o, "expected_close_date", None) else None,
                }
                for o in opps
            ],
            "count": len(opps),
        }

    elif tool_name == "assign_organization_owner":
        from app.domain.entities.organization import Organization as _OrgOwn
        from app.domain.entities.user import User as _UserOwn

        org_id = args.get("organization_id", "")
        owner_email = args.get("owner_email", "")

        org = db.query(_OrgOwn).filter(
            _OrgOwn.id == org_id,
            _OrgOwn.tenant_id == user_context["tenant_id"],
        ).first()
        if not org:
            return {"status": "error", "message": f"Organization {org_id} not found"}

        new_owner = db.query(_UserOwn).filter(
            _UserOwn.email == owner_email,
            _UserOwn.tenant_id == user_context["tenant_id"],
        ).first()
        if not new_owner:
            return {"status": "error", "message": f"User '{owner_email}' not found in this tenant."}

        org.owner_id = new_owner.id
        org.updated_by = user_context.get("user_email", "bob")
        db.commit()

        logger.info("tool_organization_owner_assigned", org_id=org_id, owner=owner_email)
        return {
            "status": "ok",
            "message": f"Organization '{org.name}' is now owned by {new_owner.email}.",
        }

    elif tool_name == "get_organization_summary":
        from app.domain.entities.organization import Organization as _OrgSum
        from app.domain.entities.contact import Contact as _ContactSum
        from app.domain.entities.opportunity import Opportunity as _OppSum
        from app.domain.entities.activity import Activity

        org_id = args.get("organization_id", "")
        tenant_id = user_context["tenant_id"]

        org = db.query(_OrgSum).filter(
            _OrgSum.id == org_id,
            _OrgSum.tenant_id == tenant_id,
        ).first()
        if not org:
            return {"status": "error", "message": f"Organization {org_id} not found"}

        # Contacts
        contacts = db.query(_ContactSum).filter(
            _ContactSum.organization_id == org_id,
            _ContactSum.tenant_id == tenant_id,
        ).limit(10).all()

        # Opportunities
        opps = db.query(_OppSum).filter(
            _OppSum.organization_id == org_id,
            _OppSum.tenant_id == tenant_id,
        ).order_by(_OppSum.created_at.desc()).limit(10).all()

        # Recent activities
        recent_activities = []
        if org.linked_activities:
            for a in org.linked_activities[:5]:
                recent_activities.append({
                    "title": a.title,
                    "type": a.activity_type,
                    "date": str(a.created_at) if a.created_at else None,
                })

        # BCC profile sections
        bcc_sections = []
        if org.organization_profile and isinstance(org.organization_profile, dict):
            for key, val in org.organization_profile.items():
                if val:
                    preview = str(val)[:200]
                    bcc_sections.append({"section": key, "preview": preview})

        # Pipeline totals
        total_pipeline = sum(o.amount or 0 for o in opps)

        return {
            "status": "ok",
            "summary": {
                "organization": {
                    "id": str(org.id),
                    "name": org.name,
                    "industry": org.industry,
                    "status": org.status.value if org.status else None,
                    "website": org.website,
                    "phone": org.phone,
                    "employee_count": org.employee_count,
                    "annual_revenue": org.annual_revenue,
                    "ai_enriched": org.ai_enriched,
                },
                "contacts": [
                    {
                        "name": f"{c.first_name} {c.last_name}".strip(),
                        "email": c.email,
                        "job_title": getattr(c, "job_title", None),
                    }
                    for c in contacts
                ],
                "contacts_total": len(contacts),
                "opportunities": [
                    {
                        "name": o.name,
                        "stage": o.stage.value if o.stage else None,
                        "amount": o.amount,
                    }
                    for o in opps
                ],
                "pipeline_total": total_pipeline,
                "recent_activities": recent_activities,
                "bcc_intelligence": bcc_sections,
            },
        }

    # ── Contact management tools ──────────────────────────────

    elif tool_name == "get_contact":
        from app.domain.entities.contact import Contact as _CGet
        contact_id = args.get("contact_id", "")
        tenant_id = user_context["tenant_id"]
        c = db.query(_CGet).filter(
            _CGet.id == contact_id,
            _CGet.tenant_id == tenant_id,
        ).first()
        if not c:
            return {"status": "error", "message": f"Contact {contact_id} not found"}
        return {
            "status": "ok",
            "contact": {
                "id": str(c.id),
                "first_name": c.first_name,
                "last_name": c.last_name,
                "email": c.email,
                "phone": c.phone,
                "mobile": c.mobile,
                "job_title": c.job_title,
                "department": c.department,
                "seniority": c.seniority,
                "status": c.status.value if c.status else None,
                "linkedin_url": c.linkedin_url,
                "notes": c.notes,
                "organization_id": c.organization_id,
                "organization_name": c.organization.name if c.organization else None,
                "opportunities_count": len(c.opportunities) if c.opportunities else 0,
                "activities_count": len(c.linked_activities) if c.linked_activities else 0,
                "owner_id": c.owner_id,
            },
        }

    elif tool_name == "update_contact":
        from app.domain.entities.contact import Contact as _CUpd
        contact_id = args.pop("contact_id", "")
        tenant_id = user_context["tenant_id"]
        c = db.query(_CUpd).filter(
            _CUpd.id == contact_id,
            _CUpd.tenant_id == tenant_id,
        ).first()
        if not c:
            return {"status": "error", "message": f"Contact {contact_id} not found"}
        updatable = [
            "first_name", "last_name", "email", "phone", "mobile",
            "job_title", "department", "seniority", "linkedin_url",
            "notes", "status", "organization_id",
        ]
        changed = []
        for field in updatable:
            if field in args and args[field] is not None:
                setattr(c, field, args[field])
                changed.append(field)
        db.commit()
        db.refresh(c)
        return {
            "status": "ok",
            "message": f"Contact updated ({', '.join(changed)})",
            "contact_id": str(c.id),
        }

    elif tool_name == "delete_contact":
        from app.domain.entities.contact import Contact as _CDel
        from app.domain.entities.opportunity import Opportunity as _OppGuard
        contact_id = args.get("contact_id", "")
        tenant_id = user_context["tenant_id"]
        c = db.query(_CDel).filter(
            _CDel.id == contact_id,
            _CDel.tenant_id == tenant_id,
        ).first()
        if not c:
            return {"status": "error", "message": f"Contact {contact_id} not found"}
        opp_count = db.query(_OppGuard).filter(
            _OppGuard.contact_id == contact_id,
            _OppGuard.tenant_id == tenant_id,
        ).count()
        if opp_count > 0:
            return {
                "status": "error",
                "message": f"Cannot delete: {opp_count} opportunity(ies) linked. Reassign them first.",
            }
        c.is_deleted = True
        db.commit()
        return {"status": "ok", "message": f"Contact {c.first_name} {c.last_name} deleted (soft)"}

    elif tool_name == "list_contact_activities":
        from app.domain.entities.contact import Contact as _CLstAct
        contact_id = args.get("contact_id", "")
        tenant_id = user_context["tenant_id"]
        c = db.query(_CLstAct).filter(
            _CLstAct.id == contact_id,
            _CLstAct.tenant_id == tenant_id,
        ).first()
        if not c:
            return {"status": "error", "message": f"Contact {contact_id} not found"}
        limit = min(int(args.get("limit", 20)), 50)
        activities = (c.linked_activities or [])[:limit]
        return {
            "status": "ok",
            "contact_id": contact_id,
            "activities": [
                {
                    "id": str(a.id),
                    "subject": a.subject,
                    "type": a.activity_type.value if a.activity_type else None,
                    "status": a.status.value if a.status else None,
                    "due_date": str(a.due_date) if a.due_date else None,
                }
                for a in activities
            ],
        }

    elif tool_name == "list_contact_opportunities":
        from app.domain.entities.contact import Contact as _CLstOpp
        contact_id = args.get("contact_id", "")
        tenant_id = user_context["tenant_id"]
        c = db.query(_CLstOpp).filter(
            _CLstOpp.id == contact_id,
            _CLstOpp.tenant_id == tenant_id,
        ).first()
        if not c:
            return {"status": "error", "message": f"Contact {contact_id} not found"}
        limit = min(int(args.get("limit", 20)), 50)
        opps = (c.opportunities or [])[:limit]
        return {
            "status": "ok",
            "contact_id": contact_id,
            "opportunities": [
                {
                    "id": str(o.id),
                    "name": o.name,
                    "stage": o.stage.value if o.stage else None,
                    "amount": o.amount,
                    "close_date": str(o.close_date) if o.close_date else None,
                }
                for o in opps
            ],
        }

    elif tool_name == "get_contact_summary":
        from app.domain.entities.contact import Contact as _CSum
        contact_id = args.get("contact_id", "")
        tenant_id = user_context["tenant_id"]
        c = db.query(_CSum).filter(
            _CSum.id == contact_id,
            _CSum.tenant_id == tenant_id,
        ).first()
        if not c:
            return {"status": "error", "message": f"Contact {contact_id} not found"}
        opps = c.opportunities or []
        acts = c.linked_activities or []
        return {
            "status": "ok",
            "summary": {
                "contact": {
                    "id": str(c.id),
                    "name": f"{c.first_name} {c.last_name}".strip(),
                    "email": c.email,
                    "phone": c.phone,
                    "job_title": c.job_title,
                    "status": c.status.value if c.status else None,
                },
                "organization": {
                    "id": c.organization_id,
                    "name": c.organization.name if c.organization else None,
                } if c.organization_id else None,
                "opportunities": [
                    {"name": o.name, "stage": o.stage.value if o.stage else None, "amount": o.amount}
                    for o in opps[:10]
                ],
                "pipeline_total": sum(o.amount or 0 for o in opps),
                "recent_activities": [
                    {"subject": a.subject, "type": a.activity_type.value if a.activity_type else None}
                    for a in acts[:5]
                ],
                "total_opportunities": len(opps),
                "total_activities": len(acts),
            },
        }

    # ── Opportunity management tools ──────────────────────────

    elif tool_name == "get_opportunity":
        from app.domain.entities.opportunity import Opportunity as _OGet
        opp_id = args.get("opportunity_id", "")
        tenant_id = user_context["tenant_id"]
        o = db.query(_OGet).filter(
            _OGet.id == opp_id,
            _OGet.tenant_id == tenant_id,
        ).first()
        if not o:
            return {"status": "error", "message": f"Opportunity {opp_id} not found"}
        return {
            "status": "ok",
            "opportunity": {
                "id": str(o.id),
                "name": o.name,
                "description": o.description,
                "stage": o.stage.value if o.stage else None,
                "priority": o.priority.value if o.priority else None,
                "amount": o.amount,
                "probability": o.probability,
                "close_date": str(o.close_date) if o.close_date else None,
                "source": o.source,
                "organization_id": o.organization_id,
                "organization_name": o.organization.name if o.organization else None,
                "contact_id": o.contact_id,
                "contact_name": f"{o.contact.first_name} {o.contact.last_name}".strip() if o.contact else None,
                "products_count": len(o.products) if o.products else 0,
                "activities_count": len(o.linked_activities) if o.linked_activities else 0,
                "owner_id": o.owner_id,
            },
        }

    elif tool_name == "update_opportunity":
        from app.domain.entities.opportunity import Opportunity as _OUpd
        from datetime import date as _date
        opp_id = args.pop("opportunity_id", "")
        tenant_id = user_context["tenant_id"]
        o = db.query(_OUpd).filter(
            _OUpd.id == opp_id,
            _OUpd.tenant_id == tenant_id,
        ).first()
        if not o:
            return {"status": "error", "message": f"Opportunity {opp_id} not found"}
        updatable = [
            "name", "description", "stage", "priority", "amount",
            "probability", "source", "organization_id", "contact_id",
        ]
        changed = []
        for field in updatable:
            if field in args and args[field] is not None:
                setattr(o, field, args[field])
                changed.append(field)
        if "close_date" in args and args["close_date"]:
            try:
                o.close_date = _date.fromisoformat(args["close_date"])
                changed.append("close_date")
            except ValueError:
                pass
        db.commit()
        db.refresh(o)
        return {
            "status": "ok",
            "message": f"Opportunity updated ({', '.join(changed)})",
            "opportunity_id": str(o.id),
        }

    elif tool_name == "delete_opportunity":
        from app.domain.entities.opportunity import Opportunity as _ODel
        opp_id = args.get("opportunity_id", "")
        tenant_id = user_context["tenant_id"]
        o = db.query(_ODel).filter(
            _ODel.id == opp_id,
            _ODel.tenant_id == tenant_id,
        ).first()
        if not o:
            return {"status": "error", "message": f"Opportunity {opp_id} not found"}
        if o.quotes and len(o.quotes) > 0:
            return {
                "status": "error",
                "message": f"Cannot delete: {len(o.quotes)} quote(s) linked. Remove them first.",
            }
        o.is_deleted = True
        db.commit()
        return {"status": "ok", "message": f"Opportunity '{o.name}' deleted (soft)"}

    elif tool_name == "list_opportunity_activities":
        from app.domain.entities.opportunity import Opportunity as _OLstAct
        opp_id = args.get("opportunity_id", "")
        tenant_id = user_context["tenant_id"]
        o = db.query(_OLstAct).filter(
            _OLstAct.id == opp_id,
            _OLstAct.tenant_id == tenant_id,
        ).first()
        if not o:
            return {"status": "error", "message": f"Opportunity {opp_id} not found"}
        limit = min(int(args.get("limit", 20)), 50)
        activities = (o.linked_activities or [])[:limit]
        return {
            "status": "ok",
            "opportunity_id": opp_id,
            "activities": [
                {
                    "id": str(a.id),
                    "subject": a.subject,
                    "type": a.activity_type.value if a.activity_type else None,
                    "status": a.status.value if a.status else None,
                    "due_date": str(a.due_date) if a.due_date else None,
                }
                for a in activities
            ],
        }

    elif tool_name == "get_opportunity_summary":
        from app.domain.entities.opportunity import Opportunity as _OSum
        opp_id = args.get("opportunity_id", "")
        tenant_id = user_context["tenant_id"]
        o = db.query(_OSum).filter(
            _OSum.id == opp_id,
            _OSum.tenant_id == tenant_id,
        ).first()
        if not o:
            return {"status": "error", "message": f"Opportunity {opp_id} not found"}
        products = o.products or []
        acts = o.linked_activities or []
        return {
            "status": "ok",
            "summary": {
                "opportunity": {
                    "id": str(o.id),
                    "name": o.name,
                    "stage": o.stage.value if o.stage else None,
                    "amount": o.amount,
                    "probability": o.probability,
                    "close_date": str(o.close_date) if o.close_date else None,
                    "priority": o.priority.value if o.priority else None,
                },
                "organization": {
                    "name": o.organization.name if o.organization else None,
                },
                "contact": {
                    "name": f"{o.contact.first_name} {o.contact.last_name}".strip() if o.contact else None,
                },
                "products": [
                    {"name": getattr(p, "product_name", None) or str(p.product_id)[:8], "quantity": p.quantity}
                    for p in products[:10]
                ],
                "recent_activities": [
                    {"subject": a.subject, "type": a.activity_type.value if a.activity_type else None}
                    for a in acts[:5]
                ],
                "total_products": len(products),
                "total_activities": len(acts),
            },
        }

    # ── Activity management tools ─────────────────────────────

    elif tool_name == "create_activity":
        from app.domain.entities.activity import Activity as _ACreate, ActivityType as _AType
        from app.domain.entities.activity import ActivityPriority as _APrio
        from datetime import datetime as _dt_act

        tenant_id = user_context["tenant_id"]
        act = _ACreate(
            tenant_id=tenant_id,
            subject=args.get("subject", "Untitled"),
            activity_type=_AType(args.get("activity_type", "TASK")),
            description=args.get("description"),
            priority=_APrio(args.get("priority", "MEDIUM")),
            assigned_to=args.get("assigned_to"),
            organization_id=args.get("organization_id"),
            contact_id=args.get("contact_id"),
            opportunity_id=args.get("opportunity_id"),
            owner_id=user_context.get("user_id"),
        )
        if args.get("due_date"):
            try:
                act.due_date = _dt_act.fromisoformat(args["due_date"])
            except ValueError:
                pass
        db.add(act)
        db.commit()
        db.refresh(act)
        logger.info("activity_created", id=str(act.id), type=args.get("activity_type"))
        return {
            "status": "ok",
            "message": f"Activity '{act.subject}' created",
            "activity_id": str(act.id),
            "activity_type": act.activity_type.value if act.activity_type else None,
        }

    elif tool_name == "get_activity":
        from app.domain.entities.activity import Activity as _AGet
        act_id = args.get("activity_id", "")
        tenant_id = user_context["tenant_id"]
        a = db.query(_AGet).filter(
            _AGet.id == act_id,
            _AGet.tenant_id == tenant_id,
        ).first()
        if not a:
            return {"status": "error", "message": f"Activity {act_id} not found"}
        return {
            "status": "ok",
            "activity": {
                "id": str(a.id),
                "subject": a.subject,
                "description": a.description,
                "activity_type": a.activity_type.value if a.activity_type else None,
                "priority": a.priority.value if a.priority else None,
                "status": a.status.value if a.status else None,
                "due_date": str(a.due_date) if a.due_date else None,
                "completed_at": str(a.completed_at) if a.completed_at else None,
                "assigned_to": a.assigned_to,
                "organization_id": a.organization_id,
                "contact_id": a.contact_id,
                "opportunity_id": a.opportunity_id,
                "owner_id": a.owner_id,
            },
        }

    elif tool_name == "update_activity":
        from app.domain.entities.activity import Activity as _AUpd
        from datetime import datetime as _dt_upd
        act_id = args.pop("activity_id", "")
        tenant_id = user_context["tenant_id"]
        a = db.query(_AUpd).filter(
            _AUpd.id == act_id,
            _AUpd.tenant_id == tenant_id,
        ).first()
        if not a:
            return {"status": "error", "message": f"Activity {act_id} not found"}
        updatable = [
            "subject", "description", "activity_type",
            "priority", "status", "assigned_to",
        ]
        changed = []
        for field in updatable:
            if field in args and args[field] is not None:
                setattr(a, field, args[field])
                changed.append(field)
        if "due_date" in args and args["due_date"]:
            try:
                a.due_date = _dt_upd.fromisoformat(args["due_date"])
                changed.append("due_date")
            except ValueError:
                pass
        if a.status and a.status.value == "COMPLETED" and not a.completed_at:
            a.completed_at = _dt_upd.utcnow()
        db.commit()
        db.refresh(a)
        return {
            "status": "ok",
            "message": f"Activity updated ({', '.join(changed)})",
            "activity_id": str(a.id),
        }

    elif tool_name == "delete_activity":
        from app.domain.entities.activity import Activity as _ADel
        act_id = args.get("activity_id", "")
        tenant_id = user_context["tenant_id"]
        a = db.query(_ADel).filter(
            _ADel.id == act_id,
            _ADel.tenant_id == tenant_id,
        ).first()
        if not a:
            return {"status": "error", "message": f"Activity {act_id} not found"}
        a.is_deleted = True
        db.commit()
        return {"status": "ok", "message": f"Activity '{a.subject}' deleted (soft)"}

    elif tool_name == "complete_activity":
        from app.domain.entities.activity import Activity as _AComp, ActivityStatus as _AStat
        from datetime import datetime as _dt_comp
        act_id = args.get("activity_id", "")
        tenant_id = user_context["tenant_id"]
        a = db.query(_AComp).filter(
            _AComp.id == act_id,
            _AComp.tenant_id == tenant_id,
        ).first()
        if not a:
            return {"status": "error", "message": f"Activity {act_id} not found"}
        a.status = _AStat.COMPLETED
        a.completed_at = _dt_comp.utcnow()
        db.commit()
        return {"status": "ok", "message": f"Activity '{a.subject}' marked as completed"}

    # ── 12. Client Map 360° ────────────────────────────────────
    elif tool_name == "get_contact_client_map":
        contact_id = args.get("contact_id", "")
        tenant_id = user_context["tenant_id"]
        if not contact_id:
            return {"status": "error", "message": "contact_id is required"}
        from app.infrastructure.persistence.client_map_repository import ClientMapRepository
        repo = ClientMapRepository(db)
        cm = repo.get_by_contact_id(contact_id, tenant_id)
        if not cm:
            return {"status": "ok", "message": "No Client Map exists for this contact yet.", "data": None}
        profile = cm.behavioral_profile or {}
        notes_summary = []
        for n in (cm.golden_notes or [])[:5]:
            note_dict = {
                "date": str(n.interaction_date) if n.interaction_date else None,
                "type": str(n.interaction_type) if n.interaction_type else None,
                "verbatim": n.verbatim,
                "emotional_climate": str(n.emotional_climate) if n.emotional_climate else None,
                "next_step": n.next_step,
            }
            notes_summary.append(note_dict)
        return {
            "status": "ok",
            "data": {
                "meddpicc_score": cm.meddpicc_score,
                "trust_level": cm.trust_level,
                "role_type": str(cm.role_type) if cm.role_type else None,
                "real_role": cm.real_role,
                "disc_profile": str(cm.disc_profile) if cm.disc_profile else None,
                "pain_point": cm.pain_point,
                "inaction_cost": cm.inaction_cost,
                "trigger_event": cm.trigger_event,
                "wiifm_business": cm.wiifm_business,
                "economic_buyer": cm.economic_buyer,
                "champion_name": cm.champion_name,
                "competition": cm.competition,
                "blockers": cm.blockers,
                "behavioral_profile": profile,
                "golden_notes": notes_summary,
            }
        }

    # ── 13. Dynamic BCC tools (generic ORM fallback) ───────────
    else:
        # Try to execute as a BCC-defined dynamic tool
        dynamic_result = await _execute_dynamic_tool(db, user_context, tool_name, args)
        if dynamic_result is not None:
            return dynamic_result
        logger.warning("execute_bob_tool_unknown", tool=tool_name)
        return {"status": "error", "message": f"Unknown tool: {tool_name}"}


# ── Dynamic tool executor ────────────────────────────────────

TABLE_MODEL_MAP = {
    "organizations": "app.domain.entities.organization.Organization",
    "contacts": "app.domain.entities.contact.Contact",
    "opportunities": "app.domain.entities.opportunity.Opportunity",
    "activities": "app.domain.entities.activity.Activity",
    "products": "app.domain.entities.product.Product",
}


async def _execute_dynamic_tool(db, user_context: dict, tool_name: str, arguments: dict):
    """Execute a BCC-defined dynamic tool via generic ORM query.

    Looks up the tool in BccTaskTemplate.context["tool_schemas"],
    then uses db_table/db_operation from context to run a safe SELECT query.
    Returns None if the tool is not found in BCC.
    """
    from app.domain.entities.bcc_entities import BccTaskTemplate
    import importlib

    tenant_id = user_context["tenant_id"]

    templates = db.query(BccTaskTemplate).filter(
        BccTaskTemplate.tenant_id == tenant_id,
    ).all()

    target_tpl = None
    for tpl in templates:
        ctx = tpl.context or {}
        tool_prio = ctx.get("tool_priority", [])
        if isinstance(tool_prio, list) and tool_name in tool_prio:
            target_tpl = tpl
            break
        schemas = ctx.get("tool_schemas", [])
        for s in schemas:
            if s.get("function", {}).get("name") == tool_name:
                target_tpl = tpl
                break
        if target_tpl:
            break

    if not target_tpl:
        return None

    ctx = target_tpl.context or {}
    db_table = ctx.get("db_table")
    db_operation = (ctx.get("db_operation") or "SELECT").upper()

    if not db_table or "SELECT" not in db_operation:
        return {"status": "error", "message": f"Dynamic tool {tool_name}: read-only operations only."}

    table_key = db_table.lower().strip()
    model_path = TABLE_MODEL_MAP.get(table_key)
    if not model_path:
        return {"status": "error", "message": f"Dynamic tool {tool_name}: unknown table '{db_table}'."}

    module_path, class_name = model_path.rsplit(".", 1)
    mod = importlib.import_module(module_path)
    Model = getattr(mod, class_name)

    try:
        query = db.query(Model).filter(Model.tenant_id == tenant_id)

        search_query = arguments.get("query") or arguments.get("search") or arguments.get("name")
        if search_query and hasattr(Model, "name"):
            query = query.filter(Model.name.ilike(f"%{search_query}%"))

        limit = min(int(arguments.get("limit", 10)), 50)

        if hasattr(Model, "created_at"):
            query = query.order_by(Model.created_at.desc())

        results = query.limit(limit).all()

        if not results:
            return {"status": "ok", "message": f"No results found for {tool_name}.", "results": []}

        items = []
        for row in results:
            name = getattr(row, "name", None) or getattr(row, "subject", None) or str(row.id)[:8]
            detail_parts = []
            for attr in ("industry", "stage", "email", "category", "status", "amount"):
                val = getattr(row, attr, None)
                if val:
                    detail_parts.append(f"{attr}={val}")
            items.append({"name": name, "details": ", ".join(detail_parts) if detail_parts else ""})

        logger.info("dynamic_tool_executed", tool=tool_name, table=db_table, results=len(results))
        return {"status": "ok", "message": f"Found {len(results)} result(s).", "results": items}

    except Exception as e:
        logger.error("dynamic_tool_error", tool=tool_name, error=str(e))
        return {"status": "error", "message": f"Dynamic tool {tool_name} error: {str(e)}"}
