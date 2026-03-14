import asyncio
from sqlalchemy.orm import Session
from app.infrastructure.database import SessionLocal
from app.domain.entities.ms365_connection import MS365Connection
from app.infrastructure.external.ms365_graph_service import MS365GraphService
from app.application.services.ms365_sync_service import MS365SyncService
from app.domain.entities.synced_email import SyncedEmail
from app.infrastructure.persistence.ms365_repository import MS365Repository
from app.domain.entities.workflow import Workflow
from app.agents.workflow_runner import WorkflowRunner
from app.domain.entities.user import User

async def force_sync_history():
    db = SessionLocal()
    try:
        conn = db.query(MS365Connection).filter(MS365Connection.is_active == True).first()
        if not conn:
            print("No active connection")
            return
            
        print(f"Fetching history for connection: {conn.ms_email}")
        
        graph = MS365GraphService()
        token, _ = await graph.ensure_valid_token(conn.access_token, conn.refresh_token, conn.token_expires_at)
        
        import httpx
        
        # We already fetched 1000 emails into the DB previously.
        # Fetching them locally to save API calls.
        sync_service = MS365SyncService(db)
        repo = MS365Repository(db)
        
        print(f"Reading emails from DB for user {conn.user_id}...")
        synced_objs = repo.list_emails(conn.user_id, conn.tenant_id, skip=0, limit=1000)
        
        print(f"Total messages to process: {len(synced_objs)}")
        
        print(f"Loaded {len(synced_objs)} emails from cache.")
        
        # Now trigger the workflow on them
        user = db.query(User).filter(User.id == conn.user_id).first()
        workflow = db.query(Workflow).filter(
            Workflow.name == "Inbox AI Triaging",
            Workflow.tenant_id == conn.tenant_id
        ).first()
        
        if not workflow:
            print("Workflow 'Inbox AI Triaging' not found for this tenant.")
            return
            
        print(f"Running AI Triaging workflow {workflow.id} on the {len(synced_objs)} emails...")
        runner = WorkflowRunner(db)
        
        processed = 0
        for email_obj in synced_objs:
            await runner.run(
                workflow=workflow,
                user=user,
                tenant_id=conn.tenant_id,
                input_data={"synced_email": {
                    "id": email_obj.id, 
                    "subject": email_obj.subject, 
                    "body_preview": email_obj.body_preview,
                    "from_address": email_obj.from_address
                }},
                triggered_by="manual"
            )
            processed += 1
            if processed % 10 == 0:
                print(f"Processed {processed}/{len(synced_objs)} via AI Triaging...")
                
        print("Done completely!")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(force_sync_history())
