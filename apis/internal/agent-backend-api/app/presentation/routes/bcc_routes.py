"""Bob Control Center HTTP routes."""
from fastapi import APIRouter, Depends, status

from app.application.use_cases.bcc_use_cases import BccUseCases
from app.infrastructure.database import get_db  # kept for test dependency overrides
from app.middleware.auth import get_current_user
from app.presentation.bcc_operations import BccOperations, _validate_entity_type
from app.presentation.deps import get_bcc_use_cases
from app.presentation.schemas.bcc_schemas import (
    # Existing
    BccRoleCreate, BccRoleUpdate, BccRoleResponse, BccRoleDetailResponse,
    BccSkillCreate, BccSkillUpdate, BccSkillResponse,
    BccTaskCreate, BccTaskUpdate, BccTaskResponse,
    BccTaskStepCreate, BccTaskStepResponse,
    BccResourceCreate, BccResourceResponse,
    BccMilestoneCreate, BccMilestoneResponse,
    # Layer 1 - Library
    BccIndustryCreate, BccIndustryUpdate, BccIndustryResponse,
    BccCareerCreate, BccCareerUpdate, BccCareerResponse,
    BccSkillTemplateCreate, BccSkillTemplateUpdate, BccSkillTemplateResponse,
    BccTaskTemplateCreate, BccTaskTemplateUpdate, BccTaskTemplateResponse,
    BccDomainCreate, BccDomainUpdate, BccDomainResponse,
    BccIntentCreate, BccIntentResponse, BccIntentTaskResponse,
    # Layer 2 - Organization
    BccOrganizationCreate, BccOrganizationUpdate, BccOrganizationResponse,
    BccOrgProfileCreate, BccOrgProfileUpdate, BccOrgProfileResponse,
    BccDepartmentCreate, BccDepartmentUpdate, BccDepartmentResponse,
    BccTeamCreate, BccTeamUpdate, BccTeamResponse,
    BccOrgDetailResponse,
    # Layer 3 - Regulations
    BccRegulationCreate, BccRegulationUpdate, BccRegulationResponse,
    # Layer 4 - Profile entries
    BccProfileEntryCreate, BccProfileEntryResponse,
    BccProfileSectionResponse, BccProfileResponse,
)

router = APIRouter(prefix="/api/v1/bcc")


def _resolve_use_cases(candidate):
    if isinstance(candidate, BccUseCases):
        return candidate
    if hasattr(candidate, "query"):
        return BccUseCases(operations=BccOperations(candidate))
    return candidate

@router.get('/organizations', response_model=list[BccOrganizationResponse])
async def list_organizations(
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).list_organizations(current_user)

@router.post('/organizations', status_code=status.HTTP_201_CREATED, response_model=BccOrganizationResponse)
async def create_organization(
    data: BccOrganizationCreate,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).create_organization(data, current_user)

@router.get('/organizations/{org_id}', response_model=BccOrgDetailResponse)
async def get_organization_detail(
    org_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).get_organization_detail(org_id, current_user)

@router.put('/organizations/{org_id}', response_model=BccOrganizationResponse)
async def update_organization(
    org_id: str,
    data: BccOrganizationUpdate,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).update_organization(org_id, data, current_user)

@router.delete('/organizations/{org_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).delete_organization(org_id, current_user)

@router.put('/organizations/{org_id}/profile', response_model=BccOrgProfileResponse)
async def update_org_profile(
    org_id: str,
    data: BccOrgProfileUpdate,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).update_org_profile(org_id, data, current_user)

@router.get('/organizations/{org_id}/departments', response_model=list[BccDepartmentResponse])
async def list_departments(
    org_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).list_departments(org_id, current_user)

@router.post('/organizations/{org_id}/departments', status_code=status.HTTP_201_CREATED, response_model=BccDepartmentResponse)
async def create_department(
    org_id: str,
    data: BccDepartmentCreate,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).create_department(org_id, data, current_user)

@router.delete('/departments/{dept_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    dept_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).delete_department(dept_id, current_user)

@router.get('/departments/{dept_id}/teams', response_model=list[BccTeamResponse])
async def list_teams(
    dept_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).list_teams(dept_id, current_user)

@router.post('/departments/{dept_id}/teams', status_code=status.HTTP_201_CREATED, response_model=BccTeamResponse)
async def create_team(
    dept_id: str,
    data: BccTeamCreate,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).create_team(dept_id, data, current_user)

@router.delete('/teams/{team_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).delete_team(team_id, current_user)

@router.get('/industries', response_model=list[BccIndustryResponse])
async def list_industries(
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).list_industries(current_user)

@router.get('/industries/{industry_id}', response_model=BccIndustryResponse)
async def get_industry(
    industry_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).get_industry(industry_id, current_user)

@router.post('/industries', status_code=status.HTTP_201_CREATED, response_model=BccIndustryResponse)
async def create_industry(
    data: BccIndustryCreate,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).create_industry(data, current_user)

@router.put('/industries/{industry_id}', response_model=BccIndustryResponse)
async def update_industry(
    industry_id: str,
    data: BccIndustryUpdate,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).update_industry(industry_id, data, current_user)

@router.delete('/industries/{industry_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_industry(
    industry_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).delete_industry(industry_id, current_user)

@router.get('/careers', response_model=list[BccCareerResponse])
async def list_careers(
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).list_careers(current_user)

@router.get('/careers/{career_id}', response_model=BccCareerResponse)
async def get_career(
    career_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).get_career(career_id, current_user)

@router.post('/careers', status_code=status.HTTP_201_CREATED, response_model=BccCareerResponse)
async def create_career(
    data: BccCareerCreate,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).create_career(data, current_user)

@router.delete('/careers/{career_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_career(
    career_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).delete_career(career_id, current_user)

@router.get('/skill-templates', response_model=list[BccSkillTemplateResponse])
async def list_skill_templates(
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).list_skill_templates(current_user)

@router.get('/skill-templates/{template_id}', response_model=BccSkillTemplateResponse)
async def get_skill_template(
    template_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).get_skill_template(template_id, current_user)

@router.post('/skill-templates', status_code=status.HTTP_201_CREATED, response_model=BccSkillTemplateResponse)
async def create_skill_template(
    data: BccSkillTemplateCreate,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).create_skill_template(data, current_user)

@router.delete('/skill-templates/{template_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill_template(
    template_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).delete_skill_template(template_id, current_user)

@router.get('/task-templates', response_model=list[BccTaskTemplateResponse])
async def list_task_templates(
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).list_task_templates(current_user)

@router.get('/task-templates/{template_id}', response_model=BccTaskTemplateResponse)
async def get_task_template(
    template_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).get_task_template(template_id, current_user)

@router.post('/task-templates', status_code=status.HTTP_201_CREATED, response_model=BccTaskTemplateResponse)
async def create_task_template(
    data: BccTaskTemplateCreate,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).create_task_template(data, current_user)

@router.delete('/task-templates/{template_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_template(
    template_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).delete_task_template(template_id, current_user)

@router.get('/domains', response_model=list[BccDomainResponse])
async def list_domains(
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).list_domains(current_user)

@router.post('/domains', status_code=status.HTTP_201_CREATED, response_model=BccDomainResponse)
async def create_domain(
    data: BccDomainCreate,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).create_domain(data, current_user)

@router.delete('/domains/{domain_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_domain(
    domain_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).delete_domain(domain_id, current_user)

@router.get('/intents', response_model=list[BccIntentResponse])
async def list_intents(
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).list_intents(current_user)

@router.get('/intents/{intent_id}', response_model=BccIntentResponse)
async def get_intent(
    intent_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).get_intent(intent_id, current_user)

@router.post('/intents', status_code=status.HTTP_201_CREATED, response_model=BccIntentResponse)
async def create_intent(
    data: BccIntentCreate,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).create_intent(data, current_user)

@router.delete('/intents/{intent_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_intent(
    intent_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).delete_intent(intent_id, current_user)

@router.get('/cognitive-map')
async def get_cognitive_map(
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).get_cognitive_map(current_user)

@router.get('/organizations/{org_id}/regulations', response_model=list[BccRegulationResponse])
async def list_regulations(
    org_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).list_regulations(org_id, current_user)

@router.post('/organizations/{org_id}/regulations', status_code=status.HTTP_201_CREATED, response_model=BccRegulationResponse)
async def create_regulation(
    org_id: str,
    data: BccRegulationCreate,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).create_regulation(org_id, data, current_user)

@router.delete('/regulations/{reg_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_regulation(
    reg_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).delete_regulation(reg_id, current_user)

@router.post('/organizations/{org_id}/industries/{industry_id}', status_code=status.HTTP_201_CREATED)
async def link_org_industry(
    org_id: str,
    industry_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).link_org_industry(org_id, industry_id, current_user)

@router.delete('/organizations/{org_id}/industries/{industry_id}', status_code=status.HTTP_204_NO_CONTENT)
async def unlink_org_industry(
    org_id: str,
    industry_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).unlink_org_industry(org_id, industry_id, current_user)

@router.get('/roles', response_model=list[BccRoleResponse])
async def list_roles(
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).list_roles(current_user)

@router.post('/roles', status_code=status.HTTP_201_CREATED, response_model=BccRoleResponse)
async def create_role(
    data: BccRoleCreate,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).create_role(data, current_user)

@router.get('/roles/{role_id}', response_model=BccRoleDetailResponse)
async def get_role_detail(
    role_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).get_role_detail(role_id, current_user)

@router.put('/roles/{role_id}', response_model=BccRoleResponse)
async def update_role(
    role_id: str,
    data: BccRoleUpdate,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).update_role(role_id, data, current_user)

@router.delete('/roles/{role_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).delete_role(role_id, current_user)

@router.get('/teams/{team_id}/roles', response_model=list[BccRoleResponse])
async def list_team_roles(
    team_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).list_team_roles(team_id, current_user)

@router.post('/roles/{role_id}/skills', status_code=status.HTTP_201_CREATED, response_model=BccSkillResponse)
async def add_skill(
    role_id: str,
    data: BccSkillCreate,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).add_skill(role_id, data, current_user)

@router.get('/skills/{skill_id}', response_model=BccSkillResponse)
async def get_skill(
    skill_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).get_skill(skill_id, current_user)

@router.put('/skills/{skill_id}', response_model=BccSkillResponse)
async def update_skill(
    skill_id: str,
    data: BccSkillUpdate,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).update_skill(skill_id, data, current_user)

@router.delete('/skills/{skill_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    skill_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).delete_skill(skill_id, current_user)

@router.post('/roles/{role_id}/tasks', status_code=status.HTTP_201_CREATED, response_model=BccTaskResponse)
async def add_task(
    role_id: str,
    data: BccTaskCreate,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).add_task(role_id, data, current_user)

@router.get('/tasks/{task_id}', response_model=BccTaskResponse)
async def get_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).get_task(task_id, current_user)

@router.put('/tasks/{task_id}', response_model=BccTaskResponse)
async def update_task(
    task_id: str,
    data: BccTaskUpdate,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).update_task(task_id, data, current_user)

@router.delete('/tasks/{task_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).delete_task(task_id, current_user)

@router.post('/tasks/{task_id}/steps', status_code=status.HTTP_201_CREATED, response_model=BccTaskStepResponse)
async def add_task_step(
    task_id: str,
    data: BccTaskStepCreate,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).add_task_step(task_id, data, current_user)

@router.post('/skills/{skill_id}/resources', status_code=status.HTTP_201_CREATED, response_model=BccResourceResponse)
async def add_resource(
    skill_id: str,
    data: BccResourceCreate,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).add_resource(skill_id, data, current_user)

@router.post('/roles/{role_id}/milestones', status_code=status.HTTP_201_CREATED, response_model=BccMilestoneResponse)
async def add_milestone(
    role_id: str,
    data: BccMilestoneCreate,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).add_milestone(role_id, data, current_user)

@router.post('/profiles/{entity_type}/{entity_id}/entries', status_code=status.HTTP_201_CREATED, response_model=BccProfileEntryResponse)
async def create_profile_entry(
    entity_type: str,
    entity_id: str,
    data: BccProfileEntryCreate,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).create_profile_entry(entity_type, entity_id, data, current_user)

@router.get('/profiles/{entity_type}/{entity_id}', response_model=BccProfileResponse)
async def get_profile(
    entity_type: str,
    entity_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).get_profile(entity_type, entity_id, current_user)

@router.get('/profiles/{entity_type}/{entity_id}/history', response_model=list[BccProfileEntryResponse])
async def get_profile_history(
    entity_type: str,
    entity_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).get_profile_history(entity_type, entity_id, current_user)

@router.get('/profiles/{entity_type}/{entity_id}/{section}', response_model=BccProfileSectionResponse)
async def get_profile_section(
    entity_type: str,
    entity_id: str,
    section: str,
    current_user: dict = Depends(get_current_user),
    use_cases: BccUseCases = Depends(get_bcc_use_cases),
):
    return await _resolve_use_cases(use_cases).get_profile_section(entity_type, entity_id, section, current_user)
