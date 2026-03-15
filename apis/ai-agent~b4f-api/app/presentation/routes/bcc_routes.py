"""Bob's Control Center routes — B4F proxy to agent~backend-api.

Delegates all CRUD to the backend via HTTP client.
"""

from fastapi import APIRouter, Depends, Request
from app.middleware.auth import get_current_user
from app.infrastructure.clients.agent_client import bcc_client

router = APIRouter(prefix="/api/v1/bcc")


def _fh(request: Request) -> dict:
    return {"Authorization": request.headers.get("Authorization", "")}


# ── Organizations ────────────────────────────────────────────

@router.get("/organizations")
async def list_organizations(request: Request, current_user: dict = Depends(get_current_user)):
    return await bcc_client.list_organizations(forward_headers=_fh(request))

@router.post("/organizations", status_code=201)
async def create_organization(request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await bcc_client.create_organization(data, forward_headers=_fh(request))

@router.get("/organizations/{org_id}")
async def get_organization_detail(org_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    return await bcc_client.get_organization(org_id, forward_headers=_fh(request))

@router.put("/organizations/{org_id}")
async def update_organization(org_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await bcc_client.update_organization(org_id, data, forward_headers=_fh(request))

@router.delete("/organizations/{org_id}", status_code=204)
async def delete_organization(org_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    await bcc_client.delete_organization(org_id, forward_headers=_fh(request))

@router.put("/organizations/{org_id}/profile")
async def update_org_profile(org_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await bcc_client.update_org_profile(org_id, data, forward_headers=_fh(request))

# ── Departments ──────────────────────────────────────────────

@router.get("/organizations/{org_id}/departments")
async def list_departments(org_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    return await bcc_client.list_departments(org_id, forward_headers=_fh(request))

@router.post("/organizations/{org_id}/departments", status_code=201)
async def create_department(org_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await bcc_client.create_department(org_id, data, forward_headers=_fh(request))

@router.delete("/departments/{dept_id}", status_code=204)
async def delete_department(dept_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    await bcc_client.delete_department(dept_id, forward_headers=_fh(request))

# ── Teams ────────────────────────────────────────────────────

@router.get("/departments/{dept_id}/teams")
async def list_teams(dept_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    return await bcc_client.list_teams(dept_id, forward_headers=_fh(request))

@router.post("/departments/{dept_id}/teams", status_code=201)
async def create_team(dept_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await bcc_client.create_team(dept_id, data, forward_headers=_fh(request))

@router.delete("/teams/{team_id}", status_code=204)
async def delete_team(team_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    await bcc_client.delete_team(team_id, forward_headers=_fh(request))

# ── Library: Industries ──────────────────────────────────────

@router.get("/industries")
async def list_industries(request: Request, current_user: dict = Depends(get_current_user)):
    return await bcc_client.list_industries(forward_headers=_fh(request))

@router.get("/industries/{industry_id}")
async def get_industry(industry_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    return await bcc_client.get_industry(industry_id, forward_headers=_fh(request))

@router.post("/industries", status_code=201)
async def create_industry(request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await bcc_client.create_industry(data, forward_headers=_fh(request))

@router.put("/industries/{industry_id}")
async def update_industry(industry_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await bcc_client.update_industry(industry_id, data, forward_headers=_fh(request))

@router.delete("/industries/{industry_id}", status_code=204)
async def delete_industry(industry_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    await bcc_client.delete_industry(industry_id, forward_headers=_fh(request))

# ── Library: Careers ─────────────────────────────────────────

@router.get("/careers")
async def list_careers(request: Request, current_user: dict = Depends(get_current_user)):
    return await bcc_client.list_careers(forward_headers=_fh(request))

@router.post("/careers", status_code=201)
async def create_career(request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await bcc_client.create_career(data, forward_headers=_fh(request))

@router.delete("/careers/{career_id}", status_code=204)
async def delete_career(career_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    await bcc_client.delete_career(career_id, forward_headers=_fh(request))

# ── Library: Skill Templates ────────────────────────────────

@router.get("/skill-templates")
async def list_skill_templates(request: Request, current_user: dict = Depends(get_current_user)):
    return await bcc_client.list_skill_templates(forward_headers=_fh(request))

@router.post("/skill-templates", status_code=201)
async def create_skill_template(request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await bcc_client.create_skill_template(data, forward_headers=_fh(request))

@router.delete("/skill-templates/{template_id}", status_code=204)
async def delete_skill_template(template_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    await bcc_client.delete_skill_template(template_id, forward_headers=_fh(request))

# ── Library: Task Templates ─────────────────────────────────

@router.get("/task-templates")
async def list_task_templates(request: Request, current_user: dict = Depends(get_current_user)):
    return await bcc_client.list_task_templates(forward_headers=_fh(request))

@router.post("/task-templates", status_code=201)
async def create_task_template(request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await bcc_client.create_task_template(data, forward_headers=_fh(request))

@router.delete("/task-templates/{template_id}", status_code=204)
async def delete_task_template(template_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    await bcc_client.delete_task_template(template_id, forward_headers=_fh(request))

# ── Domains & Intents ────────────────────────────────────────

@router.get("/domains")
async def list_domains(request: Request, current_user: dict = Depends(get_current_user)):
    return await bcc_client.list_domains(forward_headers=_fh(request))

@router.post("/domains", status_code=201)
async def create_domain(request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await bcc_client.create_domain(data, forward_headers=_fh(request))

@router.delete("/domains/{domain_id}", status_code=204)
async def delete_domain(domain_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    await bcc_client.delete_domain(domain_id, forward_headers=_fh(request))

@router.get("/intents")
async def list_intents(request: Request, current_user: dict = Depends(get_current_user)):
    return await bcc_client.list_intents(forward_headers=_fh(request))

@router.get("/intents/{intent_id}")
async def get_intent(intent_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    return await bcc_client.get_intent(intent_id, forward_headers=_fh(request))

@router.post("/intents", status_code=201)
async def create_intent(request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await bcc_client.create_intent(data, forward_headers=_fh(request))

@router.delete("/intents/{intent_id}", status_code=204)
async def delete_intent(intent_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    await bcc_client.delete_intent(intent_id, forward_headers=_fh(request))

@router.get("/cognitive-map")
async def get_cognitive_map(request: Request, current_user: dict = Depends(get_current_user)):
    return await bcc_client.get_cognitive_map(forward_headers=_fh(request))

# ── Regulations ──────────────────────────────────────────────

@router.get("/organizations/{org_id}/regulations")
async def list_regulations(org_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    return await bcc_client.list_regulations(org_id, forward_headers=_fh(request))

@router.post("/organizations/{org_id}/regulations", status_code=201)
async def create_regulation(org_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await bcc_client.create_regulation(org_id, data, forward_headers=_fh(request))

@router.delete("/regulations/{reg_id}", status_code=204)
async def delete_regulation(reg_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    await bcc_client.delete_regulation(reg_id, forward_headers=_fh(request))

# ── Org ↔ Industry links ────────────────────────────────────

@router.post("/organizations/{org_id}/industries/{industry_id}", status_code=201)
async def link_org_industry(org_id: str, industry_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    return await bcc_client.link_org_industry(org_id, industry_id, forward_headers=_fh(request))

@router.delete("/organizations/{org_id}/industries/{industry_id}", status_code=204)
async def unlink_org_industry(org_id: str, industry_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    await bcc_client.unlink_org_industry(org_id, industry_id, forward_headers=_fh(request))

# ── Roles ────────────────────────────────────────────────────

@router.get("/roles")
async def list_roles(request: Request, current_user: dict = Depends(get_current_user)):
    return await bcc_client.list_roles(forward_headers=_fh(request))

@router.post("/roles", status_code=201)
async def create_role(request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await bcc_client.create_role(data, forward_headers=_fh(request))

@router.get("/roles/{role_id}")
async def get_role_detail(role_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    return await bcc_client.get_role(role_id, forward_headers=_fh(request))

@router.put("/roles/{role_id}")
async def update_role(role_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await bcc_client.update_role(role_id, data, forward_headers=_fh(request))

@router.delete("/roles/{role_id}", status_code=204)
async def delete_role(role_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    await bcc_client.delete_role(role_id, forward_headers=_fh(request))

@router.get("/teams/{team_id}/roles")
async def list_team_roles(team_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    return await bcc_client.list_team_roles(team_id, forward_headers=_fh(request))

# ── Skills, Tasks, Resources, Milestones ─────────────────────

@router.post("/roles/{role_id}/skills", status_code=201)
async def add_skill(role_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await bcc_client.add_skill(role_id, data, forward_headers=_fh(request))

@router.put("/skills/{skill_id}")
async def update_skill(skill_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await bcc_client.update_skill(skill_id, data, forward_headers=_fh(request))

@router.delete("/skills/{skill_id}", status_code=204)
async def delete_skill(skill_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    await bcc_client.delete_skill(skill_id, forward_headers=_fh(request))

@router.post("/roles/{role_id}/tasks", status_code=201)
async def add_task(role_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await bcc_client.add_task(role_id, data, forward_headers=_fh(request))

@router.put("/tasks/{task_id}")
async def update_task(task_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await bcc_client.update_task(task_id, data, forward_headers=_fh(request))

@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    await bcc_client.delete_task(task_id, forward_headers=_fh(request))

@router.post("/tasks/{task_id}/steps", status_code=201)
async def add_task_step(task_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await bcc_client.add_task_step(task_id, data, forward_headers=_fh(request))

@router.post("/skills/{skill_id}/resources", status_code=201)
async def add_resource(skill_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await bcc_client.add_resource(skill_id, data, forward_headers=_fh(request))

@router.post("/roles/{role_id}/milestones", status_code=201)
async def add_milestone(role_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await bcc_client.add_milestone(role_id, data, forward_headers=_fh(request))

# ── Profile Entries ──────────────────────────────────────────

@router.post("/profiles/{entity_type}/{entity_id}/entries", status_code=201)
async def create_profile_entry(entity_type: str, entity_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await bcc_client.create_profile_entry(entity_type, entity_id, data, forward_headers=_fh(request))

@router.get("/profiles/{entity_type}/{entity_id}")
async def get_profile(entity_type: str, entity_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    return await bcc_client.get_profile(entity_type, entity_id, forward_headers=_fh(request))

@router.get("/profiles/{entity_type}/{entity_id}/history")
async def get_profile_history(entity_type: str, entity_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    return await bcc_client.get_profile_history(entity_type, entity_id, forward_headers=_fh(request))

@router.get("/profiles/{entity_type}/{entity_id}/{section}")
async def get_profile_section(entity_type: str, entity_id: str, section: str, request: Request, current_user: dict = Depends(get_current_user)):
    return await bcc_client.get_profile_section(entity_type, entity_id, section, forward_headers=_fh(request))
