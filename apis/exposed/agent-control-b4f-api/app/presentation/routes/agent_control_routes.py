"""Agent Control public contract routes."""

from fastapi import APIRouter, Depends

from app.middleware.auth import get_current_user


router = APIRouter(prefix="/agent-control")


@router.get("/contract")
async def get_agent_control_contract(current_user: dict = Depends(get_current_user)):
    return {
        "surface": "agent-control",
        "public_base_path": "/api/agent-control/v1",
        "frontend_environment_key": "agentControlApiUrl",
        "backing_service": {
            "name": "agent-control-b4f-api",
            "status": "dedicated_service_extracted_implementation",
            "implementation_source": "agent-control-b4f-api",
        },
        "identity": {
            "tenant_id_source": "session",
            "user_id_source": "session",
            "frontend_identity_override_allowed": False,
            "session_validated": bool(current_user.get("user_id")),
        },
        "namespaces": [
            {
                "name": "bcc",
                "public_prefix": "/api/agent-control/v1/bcc",
                "local_prefix": "/bcc",
                "covers_existing_namespace": True,
            },
            {
                "name": "training",
                "public_prefix": "/api/agent-control/v1/training",
                "local_prefix": "/training",
                "covers_existing_namespace": True,
            },
            {
                "name": "client-map",
                "public_prefix": "/api/agent-control/v1/contacts/{contact_id}/client-map",
                "local_prefix": "/contacts/{contact_id}/client-map",
                "covers_existing_namespace": True,
            },
        ],
        "guards": [
            "session_required",
            "permission_required",
            "no_tenant_or_user_from_frontend",
            "frontend_to_b4f_only",
        ],
    }
