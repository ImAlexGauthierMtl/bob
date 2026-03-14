"""Reset all email AI fields and re-process with enhanced multi-contact linking + AI workflow."""

import asyncio
from sqlalchemy import desc
from app.infrastructure.database import SessionLocal
from app.domain.entities.synced_email import SyncedEmail
from app.domain.entities.workflow import Workflow
from app.domain.entities.user import User
from app.domain.entities.ms365_connection import MS365Connection
from app.domain.entities.email_contact import email_contacts
from app.agents.workflow_runner import WorkflowRunner
from app.application.services.ms365_sync_service import MS365SyncService


async def reset_and_reprocess():
    db = SessionLocal()
    try:
        conn = db.query(MS365Connection).filter(MS365Connection.is_active == True).first()
        if not conn:
            print("No active MS365 connection found!")
            return

        user = db.query(User).filter(User.id == conn.user_id).first()
        workflow = db.query(Workflow).filter(
            Workflow.name == "Inbox AI Triaging",
            Workflow.tenant_id == conn.tenant_id,
        ).first()

        if not workflow:
            print("Workflow 'Inbox AI Triaging' not found!")
            return

        # Get all emails
        emails = db.query(SyncedEmail).filter(
            SyncedEmail.user_id == conn.user_id,
        ).order_by(desc(SyncedEmail.received_at)).all()

        total = len(emails)
        print(f"Processing {total} emails...")

        # Phase 1: Multi-contact auto-link
        print("\n=== Phase 1: Multi-Contact CRM Linking ===")
        sync_service = MS365SyncService(db)

        for i, email in enumerate(emails):
            sync_service._auto_link_email(email, conn.tenant_id)
            if (i + 1) % 50 == 0:
                print(f"  Linked {i+1}/{total}...")

        # Count junction rows
        junction_count = db.execute(email_contacts.select()).fetchall()
        print(f"  Total junction rows (email_contacts): {len(junction_count)}")

        # Phase 2: AI Workflow (smart_label + ai_summary + ai_action_items)
        print(f"\n=== Phase 2: AI Triaging Workflow ===")
        runner = WorkflowRunner(db)

        for i, email in enumerate(emails):
            try:
                await runner.run(
                    workflow=workflow,
                    user=user,
                    tenant_id=conn.tenant_id,
                    input_data={"synced_email": {
                        "id": email.id,
                        "subject": email.subject,
                        "body_preview": email.body_preview,
                        "from_address": email.from_address,
                    }},
                    triggered_by="manual-reset",
                )
            except Exception as e:
                print(f"  Error on email {email.subject[:40]}: {e}")

            if (i + 1) % 25 == 0:
                print(f"  AI processed {i+1}/{total}...")

        # Summary
        labeled = db.query(SyncedEmail).filter(
            SyncedEmail.user_id == conn.user_id,
            SyncedEmail.smart_label.isnot(None),
        ).count()
        summarized = db.query(SyncedEmail).filter(
            SyncedEmail.user_id == conn.user_id,
            SyncedEmail.ai_summary.isnot(None),
        ).count()

        print(f"\n=== DONE ===")
        print(f"  Emails processed: {total}")
        print(f"  With smart_label: {labeled}")
        print(f"  With ai_summary:  {summarized}")
        print(f"  Junction rows:    {len(junction_count)}")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(reset_and_reprocess())
