#!/usr/bin/env python3
"""Batch Email Enrichment Script — Manual execution.

Processes all unanalyzed synced emails:
1. Creates Organizations from email domains (excludes public domains)
2. Creates Contacts and associates them to their Organization (domain match)
3. Links emails bidirectionally to all participants (from, to, cc)
4. Uses Groq to:
   - Generate a concise summary (ai_summary)
   - Assign a SmartLabel from the user's actual categories
   - Extract action items
   - Extract the real company name to update the Organization

Usage:
    docker exec croo-api python scripts/enrich_emails.py
    docker exec croo-api python scripts/enrich_emails.py --dry-run
    docker exec croo-api python scripts/enrich_emails.py --limit 10
"""

import argparse
import json
import sys
import time
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infrastructure.database import SessionLocal
from app.domain.entities.synced_email import SyncedEmail
from app.domain.entities.contact import Contact
from app.domain.entities.organization import Organization
from app.domain.entities.smart_label import SmartLabel
from app.domain.entities.email_contact import email_contacts
from app.agents.llm_client import llm_client

import tldextract

# ── Config ───────────────────────────────────────────────────────

PUBLIC_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "live.com",
    "icloud.com", "me.com", "msn.com", "googlemail.com", "aol.com",
    "protonmail.com", "zoho.com", "ymail.com", "yahoo.ca", "yahoo.fr",
    "hotmail.ca", "hotmail.fr", "outlook.fr", "live.ca", "live.fr",
}

# Domains we own — never rename these orgs
OWN_DOMAINS = {"croo.io"}

MAX_BODY_CHARS = 2000  # Truncate email body for LLM (cost control)
GROQ_MODEL = "llama-3.3-70b-versatile"
BATCH_DELAY_SECONDS = 0.3  # Rate-limit padding between Groq calls


# ── Helpers ──────────────────────────────────────────────────────

def get_root_domain(email_address: str) -> str | None:
    """Extract root domain from email address, e.g. 'bell.ca' from 'nathalie@bell.ca'."""
    if "@" not in email_address:
        return None
    domain_raw = email_address.split("@")[-1]
    ext = tldextract.extract(domain_raw)
    if ext.domain and ext.suffix:
        return f"{ext.domain}.{ext.suffix}"
    return None


def is_public_domain(domain: str) -> bool:
    return domain.lower() in PUBLIC_DOMAINS


def build_smart_label_context(db) -> tuple[str, list[str]]:
    """Build SmartLabel context string for the LLM prompt.
    
    Returns (context_string, flat_label_list).
    """
    labels = db.query(SmartLabel).filter(
        SmartLabel.parent_id == None,
    ).all()

    if not labels:
        return "No categories defined.", []

    lines = []
    flat_labels = []

    for label in labels:
        parts = [f"- **{label.name}**"]
        if label.description:
            parts.append(f": {label.description}")
        if label.keywords:
            kw = ", ".join(label.keywords) if isinstance(label.keywords, list) else str(label.keywords)
            parts.append(f" [keywords: {kw}]")
        if label.prompt_hint:
            parts.append(f" (hint: {label.prompt_hint})")
        lines.append("".join(parts))
        flat_labels.append(label.name)

        # Sub-labels
        for sub in (label.sub_labels or []):
            sub_parts = [f"  - **{label.name} > {sub.name}**"]
            if sub.description:
                sub_parts.append(f": {sub.description}")
            if sub.keywords:
                kw = ", ".join(sub.keywords) if isinstance(sub.keywords, list) else str(sub.keywords)
                sub_parts.append(f" [keywords: {kw}]")
            lines.append("".join(sub_parts))
            flat_labels.append(f"{label.name} > {sub.name}")

    return "\n".join(lines), flat_labels


def find_or_create_org(db, domain: str, tenant_id: str) -> Organization | None:
    """Find org by domain or create a new one."""
    if is_public_domain(domain):
        return None

    org = db.query(Organization).filter(
        Organization.tenant_id == tenant_id,
        Organization.is_deleted == False,
        Organization.website.ilike(f"%{domain}%"),
    ).first()

    if not org:
        pretty_name = domain.split(".")[0].replace("-", " ").title()
        org = Organization(name=pretty_name, website=domain, tenant_id=tenant_id)
        db.add(org)
        db.flush()
        print(f"  🏢 Created org: {pretty_name} ({domain})")

    return org


def find_or_create_contact(db, addr: str, name: str, tenant_id: str) -> Contact | None:
    """Find contact by email or create a new one, linking to org by domain."""
    contact = db.query(Contact).filter(
        Contact.email == addr,
        Contact.tenant_id == tenant_id,
        Contact.is_deleted == False,
    ).first()

    if contact:
        return contact

    # Parse name
    first_name, last_name = addr.split("@")[0], ""
    if name and name.strip():
        parts = name.strip().split(" ", 1)
        first_name = parts[0]
        if len(parts) > 1:
            last_name = parts[1]

    # Find/create org from domain
    organization_id = None
    domain = get_root_domain(addr)
    if domain:
        org = find_or_create_org(db, domain, tenant_id)
        if org:
            organization_id = org.id

    contact = Contact(
        first_name=first_name,
        last_name=last_name,
        email=addr,
        organization_id=organization_id,
        tenant_id=tenant_id,
    )
    db.add(contact)
    db.flush()
    print(f"  👤 Created contact: {first_name} {last_name} <{addr}>")
    return contact


def link_email_to_contacts(db, email: SyncedEmail, tenant_id: str):
    """Link email to ALL participants (from, to, cc) via email_contacts junction."""
    addresses = []

    if email.from_address:
        addresses.append({
            "address": email.from_address.lower().strip(),
            "name": email.from_name or "",
            "role": "from",
        })

    for recipient_list, role in [(email.to_addresses, "to"), (email.cc_addresses, "cc")]:
        if not recipient_list:
            continue
        for r in recipient_list:
            addr = (r.get("address") or "").lower().strip()
            if addr:
                addresses.append({"address": addr, "name": r.get("name", ""), "role": role})

    # De-duplicate
    seen = set()
    unique = []
    for a in addresses:
        if a["address"] not in seen:
            seen.add(a["address"])
            unique.append(a)

    sender_contact = None

    for entry in unique:
        contact = find_or_create_contact(db, entry["address"], entry["name"], tenant_id)
        if not contact:
            continue

        # Check if junction row already exists
        exists = db.execute(
            email_contacts.select().where(
                email_contacts.c.synced_email_id == email.id,
                email_contacts.c.contact_id == contact.id,
            )
        ).first()

        if not exists:
            db.execute(email_contacts.insert().values(
                synced_email_id=email.id,
                contact_id=contact.id,
                role=entry["role"],
            ))

        if entry["role"] == "from" and not sender_contact:
            sender_contact = contact

    # Backward compat FK
    if sender_contact:
        email.linked_contact_id = sender_contact.id
        if sender_contact.organization_id:
            email.linked_organization_id = sender_contact.organization_id


def enrich_email_with_ai(email: SyncedEmail, label_context: str, flat_labels: list[str]) -> dict | None:
    """Call Groq to analyze a single email. Returns parsed JSON or None."""
    content = email.body_preview or email.subject or ""
    if email.body_html:
        # Strip HTML for cleaner text (rough)
        import re
        text = re.sub(r'<[^>]+>', ' ', email.body_html)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > len(content or ""):
            content = text

    content = (content or "")[:MAX_BODY_CHARS]

    if not content.strip():
        return None

    # Get the sender's domain for grounded company name extraction
    sender_domain = get_root_domain(email.from_address) if email.from_address else None

    labels_json = json.dumps(flat_labels)

    system_prompt = f"""You are an email analysis assistant for a CRM system.
Your job is to analyze the email and return a JSON object with these fields:

1. "summary": A concise 1-2 sentence summary of what the email is about. Write in the same language as the email.
2. "smart_label": Pick the MOST APPROPRIATE label from the list below. You MUST use EXACTLY one of these labels. If none fit well, pick the closest match.
3. "action_items": An array of specific action items found in the email. Empty array if none.
4. "sender_company_name": The official/full name of the company that OWNS the sender's email domain "{sender_domain or 'unknown'}". This is the sender's employer, NOT any company mentioned in the email body. Look at the email signature, header, or sender display name. Return null if you cannot determine it.
5. "is_spam": true if this is clearly spam, marketing newsletter, automated notification, or non-business email. false otherwise.

IMPORTANT for sender_company_name:
- The sender's domain is "{sender_domain or 'unknown'}" — the company name must be the organization that OWNS this domain.
- Do NOT return companies that are merely mentioned or discussed in the email body.
- Example: if someone@consultantscdm.com writes about a conference by "Aramis Biotechnologies", the sender_company_name is "Consultants CDM", NOT "Aramis Biotechnologies".

Available labels (use EXACTLY one of these):
{labels_json}

Available labels with descriptions:
{label_context}

Respond ONLY with valid JSON. No markdown, no code fences."""

    user_prompt = f"""Subject: {email.subject or '(no subject)'}
From: {email.from_name or ''} ({email.from_address or ''})
Date: {email.received_at or ''}
Content:
{content}"""

    try:
        response = llm_client.chat(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=GROQ_MODEL,
            json_mode=True,
            temperature=0.0,
            max_tokens=500,
        )
        return json.loads(response)
    except Exception as e:
        print(f"  ⚠️  Groq error: {e}")
        return None


# ── Main ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Batch email enrichment with Groq")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without making changes")
    parser.add_argument("--limit", type=int, default=0, help="Max emails to process (0 = all)")
    parser.add_argument("--skip-ai", action="store_true", help="Only do contact/org linking, skip Groq AI analysis")
    parser.add_argument("--reprocess", action="store_true", help="Re-analyze emails that already have ai_summary")
    args = parser.parse_args()

    db = SessionLocal()

    try:
        # ── 1. Find unprocessed emails ──────────────────────────
        query = db.query(SyncedEmail)
        if not args.reprocess:
            query = query.filter(SyncedEmail.ai_summary == None)
        query = query.order_by(SyncedEmail.received_at.desc())

        if args.limit > 0:
            query = query.limit(args.limit)

        emails = query.all()
        total = len(emails)

        if total == 0:
            print("✅ No unprocessed emails found.")
            return

        print(f"\n{'='*60}")
        print(f"📧 Email Enrichment Pipeline")
        print(f"{'='*60}")
        print(f"  Emails to process: {total}")
        print(f"  Dry run: {args.dry_run}")
        print(f"  Skip AI: {args.skip_ai}")
        print(f"  Reprocess: {args.reprocess}")

        # ── 2. Load SmartLabel context ──────────────────────────
        label_context, flat_labels = build_smart_label_context(db)
        print(f"  SmartLabels loaded: {len(flat_labels)}")
        for l in flat_labels:
            print(f"    • {l}")
        print(f"{'='*60}\n")

        if args.dry_run:
            for i, email in enumerate(emails):
                print(f"  [{i+1}/{total}] {email.from_address} → {email.subject or '(no subject)'}")
            print(f"\n🔍 Dry run complete. {total} emails would be processed.")
            return

        # ── 3. Get tenant_id from first email's user ────────────
        from app.domain.entities.user import User
        first_user = db.query(User).filter(User.id == emails[0].user_id).first()
        tenant_id = first_user.tenant_id if first_user else "default"

        # ── 4. Process each email ───────────────────────────────
        stats = {"processed": 0, "linked": 0, "labeled": 0, "orgs_updated": 0, "spam": 0, "errors": 0}
        start_time = time.time()

        for i, email in enumerate(emails):
            print(f"\n[{i+1}/{total}] 📩 {email.subject or '(no subject)'}")
            print(f"  From: {email.from_name} <{email.from_address}>")

            try:
                # Step A: Link to contacts/orgs
                link_email_to_contacts(db, email, tenant_id)
                stats["linked"] += 1

                # Step B: AI analysis
                if not args.skip_ai:
                    time.sleep(BATCH_DELAY_SECONDS)  # Rate limit
                    result = enrich_email_with_ai(email, label_context, flat_labels)

                    if result:
                        email.ai_summary = result.get("summary")
                        email.smart_label = result.get("smart_label")
                        email.ai_action_items = result.get("action_items", [])

                        is_spam = result.get("is_spam", False)
                        if is_spam:
                            stats["spam"] += 1

                        label = result.get("smart_label", "?")
                        summary = (result.get("summary") or "")[:80]
                        print(f"  🏷️  Label: {label}")
                        print(f"  📝 Summary: {summary}...")
                        if is_spam:
                            print(f"  🚫 SPAM detected")

                        # Step C: Update sender's org name if sender_company_name extracted
                        company_name = result.get("sender_company_name")
                        sender_domain = get_root_domain(email.from_address) if email.from_address else None

                        if company_name and sender_domain and sender_domain not in OWN_DOMAINS and not is_public_domain(sender_domain):
                            # Find the org for the sender's domain specifically
                            sender_org = db.query(Organization).filter(
                                Organization.tenant_id == tenant_id,
                                Organization.is_deleted == False,
                                Organization.website.ilike(f"%{sender_domain}%"),
                            ).first()
                            if sender_org and sender_org.name != company_name:
                                old_name = sender_org.name
                                sender_org.name = company_name
                                stats["orgs_updated"] += 1
                                print(f"  🏢 Org renamed: '{old_name}' → '{company_name}'")

                        stats["labeled"] += 1

                db.commit()
                stats["processed"] += 1

            except Exception as e:
                db.rollback()
                stats["errors"] += 1
                print(f"  ❌ Error: {e}")

        # ── 5. Summary ──────────────────────────────────────────
        duration = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"✅ Enrichment Complete")
        print(f"{'='*60}")
        print(f"  Processed:    {stats['processed']}/{total}")
        print(f"  Linked:       {stats['linked']}")
        print(f"  AI Labeled:   {stats['labeled']}")
        print(f"  Orgs Updated: {stats['orgs_updated']}")
        print(f"  Spam:         {stats['spam']}")
        print(f"  Errors:       {stats['errors']}")
        print(f"  Duration:     {duration:.1f}s")
        print(f"{'='*60}\n")

    finally:
        db.close()


if __name__ == "__main__":
    main()
