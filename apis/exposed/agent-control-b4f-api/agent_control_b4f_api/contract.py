"""Importable contract for the Agent Control B4F wrapper."""

SERVICE_NAME = "agent-control-b4f-api"
IMPLEMENTATION_SOURCE = "agent-control-b4f-api"
REQUIRED_SURFACE = "agent-control"
PUBLIC_BASE_PATH = "/api/agent-control/v1"

OPERATIONAL_ENDPOINTS = ("/health", "/readiness", "/liveness", "/startup", "/metrics")
PUBLIC_NAMESPACES = ("agent-control", "bcc", "training", "client-map", "tool-governance")


def load_app():
    """Load the FastAPI application instance."""
    import main

    return main.app


def load_runtime_routes():
    """Load the route modules exposed by Agent Control."""
    from app.presentation.routes import (
        agent_control_routes,
        bcc_routes,
        client_map_routes,
        tool_governance_routes,
        training_routes,
    )

    return (
        agent_control_routes,
        bcc_routes,
        client_map_routes,
        tool_governance_routes,
        training_routes,
    )


def load_runtime_client_classes():
    """Load backend client classes used by Agent Control."""
    from app.infrastructure.clients.agent_client import (
        BccClient,
        ClientMapClient,
        ToolGovernanceClient,
        TrainingClient,
    )

    return (
        BccClient,
        ClientMapClient,
        ToolGovernanceClient,
        TrainingClient,
    )
