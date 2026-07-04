"""HTTP clients for Agent Backend API."""
import os
from typing import Any

from shared.services import HTTPClient
from shared.services import create_service_client
from shared.infrastructure import get_logger

logger = get_logger(__name__)


def create_agent_backend_client() -> HTTPClient:
    base_url = os.environ.get("AGENT_BACKEND_API_URL")
    if not base_url:
        raise RuntimeError("AGENT_BACKEND_API_URL is required for agent-control-b4f-api")
    return HTTPClient(base_url=base_url.rstrip("/"))


def create_agent_runtime_backend_client() -> HTTPClient:
    return create_service_client("agent-runtime~backend-api")


class BccClient:
    """HTTP client for BCC CRUD operations on agent~backend-api."""

    def __init__(self):
        self._client = create_agent_backend_client()

    # ── Organizations ────────────────────────────────────────

    async def list_organizations(self, forward_headers=None):
        resp = await self._client.get("/api/v1/bcc/organizations", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def create_organization(self, data, forward_headers=None):
        resp = await self._client.post("/api/v1/bcc/organizations", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get_organization(self, org_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/bcc/organizations/{org_id}", forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def update_organization(self, org_id, data, forward_headers=None):
        resp = await self._client.put(f"/api/v1/bcc/organizations/{org_id}", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete_organization(self, org_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/bcc/organizations/{org_id}", forward_headers=forward_headers)
        return resp.status_code == 204

    async def update_org_profile(self, org_id, data, forward_headers=None):
        resp = await self._client.put(f"/api/v1/bcc/organizations/{org_id}/profile", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    # ── Departments ──────────────────────────────────────────

    async def list_departments(self, org_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/bcc/organizations/{org_id}/departments", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def create_department(self, org_id, data, forward_headers=None):
        resp = await self._client.post(f"/api/v1/bcc/organizations/{org_id}/departments", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete_department(self, dept_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/bcc/departments/{dept_id}", forward_headers=forward_headers)
        return resp.status_code == 204

    # ── Teams ────────────────────────────────────────────────

    async def list_teams(self, dept_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/bcc/departments/{dept_id}/teams", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def create_team(self, dept_id, data, forward_headers=None):
        resp = await self._client.post(f"/api/v1/bcc/departments/{dept_id}/teams", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete_team(self, team_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/bcc/teams/{team_id}", forward_headers=forward_headers)
        return resp.status_code == 204

    # ── Roles ────────────────────────────────────────────────

    async def list_roles(self, forward_headers=None):
        resp = await self._client.get("/api/v1/bcc/roles", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def create_role(self, data, forward_headers=None):
        resp = await self._client.post("/api/v1/bcc/roles", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get_role(self, role_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/bcc/roles/{role_id}", forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def update_role(self, role_id, data, forward_headers=None):
        resp = await self._client.put(f"/api/v1/bcc/roles/{role_id}", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete_role(self, role_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/bcc/roles/{role_id}", forward_headers=forward_headers)
        return resp.status_code == 204

    async def list_team_roles(self, team_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/bcc/teams/{team_id}/roles", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    # ── Library (Industries, Careers, Templates) ─────────────

    async def list_industries(self, forward_headers=None):
        resp = await self._client.get("/api/v1/bcc/industries", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def create_industry(self, data, forward_headers=None):
        resp = await self._client.post("/api/v1/bcc/industries", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get_industry(self, industry_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/bcc/industries/{industry_id}", forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def update_industry(self, industry_id, data, forward_headers=None):
        resp = await self._client.put(f"/api/v1/bcc/industries/{industry_id}", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete_industry(self, industry_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/bcc/industries/{industry_id}", forward_headers=forward_headers)
        return resp.status_code == 204

    async def list_careers(self, forward_headers=None):
        resp = await self._client.get("/api/v1/bcc/careers", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def create_career(self, data, forward_headers=None):
        resp = await self._client.post("/api/v1/bcc/careers", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete_career(self, career_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/bcc/careers/{career_id}", forward_headers=forward_headers)
        return resp.status_code == 204

    async def list_skill_templates(self, forward_headers=None):
        resp = await self._client.get("/api/v1/bcc/skill-templates", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def create_skill_template(self, data, forward_headers=None):
        resp = await self._client.post("/api/v1/bcc/skill-templates", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete_skill_template(self, template_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/bcc/skill-templates/{template_id}", forward_headers=forward_headers)
        return resp.status_code == 204

    async def list_task_templates(self, forward_headers=None):
        resp = await self._client.get("/api/v1/bcc/task-templates", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def create_task_template(self, data, forward_headers=None):
        resp = await self._client.post("/api/v1/bcc/task-templates", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete_task_template(self, template_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/bcc/task-templates/{template_id}", forward_headers=forward_headers)
        return resp.status_code == 204

    # ── Domains & Intents ────────────────────────────────────

    async def list_domains(self, forward_headers=None):
        resp = await self._client.get("/api/v1/bcc/domains", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def create_domain(self, data, forward_headers=None):
        resp = await self._client.post("/api/v1/bcc/domains", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete_domain(self, domain_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/bcc/domains/{domain_id}", forward_headers=forward_headers)
        return resp.status_code == 204

    async def list_intents(self, forward_headers=None):
        resp = await self._client.get("/api/v1/bcc/intents", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get_intent(self, intent_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/bcc/intents/{intent_id}", forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def create_intent(self, data, forward_headers=None):
        resp = await self._client.post("/api/v1/bcc/intents", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete_intent(self, intent_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/bcc/intents/{intent_id}", forward_headers=forward_headers)
        return resp.status_code == 204

    async def get_cognitive_map(self, forward_headers=None):
        resp = await self._client.get("/api/v1/bcc/cognitive-map", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    # ── Regulations ──────────────────────────────────────────

    async def list_regulations(self, org_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/bcc/organizations/{org_id}/regulations", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def create_regulation(self, org_id, data, forward_headers=None):
        resp = await self._client.post(f"/api/v1/bcc/organizations/{org_id}/regulations", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete_regulation(self, reg_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/bcc/regulations/{reg_id}", forward_headers=forward_headers)
        return resp.status_code == 204

    # ── Org ↔ Industry links ─────────────────────────────────

    async def link_org_industry(self, org_id, industry_id, forward_headers=None):
        resp = await self._client.post(f"/api/v1/bcc/organizations/{org_id}/industries/{industry_id}", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def unlink_org_industry(self, org_id, industry_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/bcc/organizations/{org_id}/industries/{industry_id}", forward_headers=forward_headers)
        return resp.status_code == 204

    # ── Skills, Tasks, Resources, Milestones ─────────────────

    async def add_skill(self, role_id, data, forward_headers=None):
        resp = await self._client.post(f"/api/v1/bcc/roles/{role_id}/skills", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def update_skill(self, skill_id, data, forward_headers=None):
        resp = await self._client.put(f"/api/v1/bcc/skills/{skill_id}", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete_skill(self, skill_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/bcc/skills/{skill_id}", forward_headers=forward_headers)
        return resp.status_code == 204

    async def add_task(self, role_id, data, forward_headers=None):
        resp = await self._client.post(f"/api/v1/bcc/roles/{role_id}/tasks", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def update_task(self, task_id, data, forward_headers=None):
        resp = await self._client.put(f"/api/v1/bcc/tasks/{task_id}", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete_task(self, task_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/bcc/tasks/{task_id}", forward_headers=forward_headers)
        return resp.status_code == 204

    async def add_task_step(self, task_id, data, forward_headers=None):
        resp = await self._client.post(f"/api/v1/bcc/tasks/{task_id}/steps", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def add_resource(self, skill_id, data, forward_headers=None):
        resp = await self._client.post(f"/api/v1/bcc/skills/{skill_id}/resources", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def add_milestone(self, role_id, data, forward_headers=None):
        resp = await self._client.post(f"/api/v1/bcc/roles/{role_id}/milestones", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    # ── Profile Entries ──────────────────────────────────────

    async def create_profile_entry(self, entity_type, entity_id, data, forward_headers=None):
        resp = await self._client.post(f"/api/v1/bcc/profiles/{entity_type}/{entity_id}/entries", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get_profile(self, entity_type, entity_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/bcc/profiles/{entity_type}/{entity_id}", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get_profile_history(self, entity_type, entity_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/bcc/profiles/{entity_type}/{entity_id}/history", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get_profile_section(self, entity_type, entity_id, section, forward_headers=None):
        resp = await self._client.get(f"/api/v1/bcc/profiles/{entity_type}/{entity_id}/{section}", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()


class ClientMapClient:
    """HTTP client for Client Map 360° on agent~backend-api."""

    def __init__(self):
        self._client = create_agent_backend_client()

    async def get(self, contact_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/contacts/{contact_id}/client-map", forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def upsert(self, contact_id, data, forward_headers=None):
        resp = await self._client.put(f"/api/v1/contacts/{contact_id}/client-map", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def create_golden_note(self, contact_id, data, forward_headers=None):
        resp = await self._client.post(f"/api/v1/contacts/{contact_id}/client-map/golden-notes", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def update_golden_note(self, contact_id, note_id, data, forward_headers=None):
        resp = await self._client.put(f"/api/v1/contacts/{contact_id}/client-map/golden-notes/{note_id}", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete_golden_note(self, contact_id, note_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/contacts/{contact_id}/client-map/golden-notes/{note_id}", forward_headers=forward_headers)
        return resp.status_code == 204

    async def get_meddpicc_score(self, contact_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/contacts/{contact_id}/client-map/meddpicc-score", forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def analyze_behavior(self, contact_id, forward_headers=None):
        resp = await self._client.post(
            f"/api/v1/contacts/{contact_id}/client-map/analyze-behavior",
            json={},
            forward_headers=forward_headers,
        )
        resp.raise_for_status()
        return resp.json()


class TrainingClient:
    """HTTP client for Training on agent~backend-api."""

    def __init__(self):
        self._client = create_agent_backend_client()

    async def create_session(self, data, forward_headers=None):
        resp = await self._client.post("/api/v1/training/sessions", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def update_slide(self, session_id, data, forward_headers=None):
        resp = await self._client.patch(f"/api/v1/training/sessions/{session_id}/slide", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get_notes(self, session_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/training/sessions/{session_id}/notes", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def create_note(self, session_id, data, forward_headers=None):
        resp = await self._client.post(f"/api/v1/training/sessions/{session_id}/notes", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete_note(self, note_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/training/notes/{note_id}", forward_headers=forward_headers)
        return resp.status_code == 204

    async def get_missing(self, session_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/training/sessions/{session_id}/missing", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def create_missing(self, session_id, data, forward_headers=None):
        resp = await self._client.post(f"/api/v1/training/sessions/{session_id}/missing", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete_missing(self, item_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/training/missing/{item_id}", forward_headers=forward_headers)
        return resp.status_code == 204


class ToolGovernanceClient:
    """HTTP client for Agent Runtime tool governance."""

    def __init__(self, client: HTTPClient | None = None):
        self._client = client or create_agent_runtime_backend_client()

    async def list_policies(self, headers: dict[str, str]) -> dict[str, Any]:
        resp = await self._client.get(
            "/internal/agent-runtime/v1/settings/tool-governance",
            headers=headers,
        )
        resp.raise_for_status()
        return resp.json()

    async def update_policy(self, policy_id: str, data: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        resp = await self._client.put(
            f"/internal/agent-runtime/v1/settings/tool-governance/{policy_id}",
            json=data,
            headers=headers,
        )
        resp.raise_for_status()
        return resp.json()

    async def get_my_access(self, headers: dict[str, str]) -> dict[str, Any]:
        resp = await self._client.get(
            "/internal/agent-runtime/v1/settings/tool-governance/me",
            headers=headers,
        )
        resp.raise_for_status()
        return resp.json()

    async def update_my_preferences(self, data: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        resp = await self._client.put(
            "/internal/agent-runtime/v1/settings/tool-preferences/me",
            json=data,
            headers=headers,
        )
        resp.raise_for_status()
        return resp.json()


bcc_client = BccClient()
client_map_client = ClientMapClient()
training_client = TrainingClient()
tool_governance_client = ToolGovernanceClient()
