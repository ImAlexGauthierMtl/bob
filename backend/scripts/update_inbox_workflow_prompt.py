import sys
import os
import structlog

# Add the app path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app")))

from app.infrastructure.database import SessionLocal
from app.domain.entities.workflow import WorkflowStep
from app.infrastructure.seed_workflows import TEMPLATE_WORKFLOWS

logger = structlog.get_logger(__name__)

def update_workflow_prompts():
    """Update existing Inbox AI Triaging workflow prompts to support nested Smart Labels."""
    db = SessionLocal()
    try:
        # Find the updated prompt from seed_workflows
        new_config = None
        for wf in TEMPLATE_WORKFLOWS:
            if wf["name"] == "Inbox AI Triaging":
                for step in wf["steps"]:
                    if step["name"] == "Bob: Smart Categorization & Insights":
                        new_config = step["config"]
                        break
        
        if not new_config:
            logger.error("Could not find the new config in seed_workflows")
            return
            
        # Update existing workflow steps across ALL tenants
        # Look for steps named exactly like this
        steps = db.query(WorkflowStep).filter(
            WorkflowStep.name == "Bob: Smart Categorization & Insights"
        ).all()
        
        updated_count = 0
        for step in steps:
            if step.config and "prompt" in step.config:
                # Need to explicitly flag dict changes in sqlalchemy if necessary,
                # but assigning the whole new dict works cleanly.
                step.config = dict(new_config)
                updated_count += 1
                
        db.commit()
        logger.info("successfully_updated_workflow_steps", updated_count=updated_count)
        print(f"Successfully updated {updated_count} workflow steps!")
        
    except Exception as e:
        logger.error("error_updating_workflow_steps", error=str(e))
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    update_workflow_prompts()
