"""Bob's Control Center routes — CRUD for all BCC entities.

Layer 1: Library (Industries, Careers, SkillTemplates, TaskTemplates)
Layer 2: Organization (Org, OrgProfile, Department, Team, Role)
Layer 3: Context (Regulations)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import structlog

from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user
from app.domain.entities.bcc_entities import (
    BccRole, BccSkill, BccTask, BccTaskStep, BccResource, BccMilestone,
    BccOrganization, BccOrgProfile, BccDepartment, BccTeam,
    BccIndustry, BccCareer, BccSkillTemplate, BccTaskTemplate,
    BccDomain, BccIntent, BccIntentTask,
    BccRegulation, BccOrgIndustry, BccProfileEntry,
)
from app.presentation.schemas.bcc_schemas import (
    # Existing
    BccRoleCreate, BccRoleUpdate, BccRoleResponse, BccRoleDetailResponse,
    BccSkillCreate, BccSkillUpdate, BccSkillResponse,
    BccTaskCreate, BccTaskUpdate, BccTaskResponse,
    BccTaskStepCreate, BccTaskStepResponse,
    BccResourceCreate, BccResourceResponse,
    BccMilestoneCreate, BccMilestoneResponse,
    # Layer 1 — Library
    BccIndustryCreate, BccIndustryUpdate, BccIndustryResponse,
    BccCareerCreate, BccCareerUpdate, BccCareerResponse,
    BccSkillTemplateCreate, BccSkillTemplateUpdate, BccSkillTemplateResponse,
    BccTaskTemplateCreate, BccTaskTemplateUpdate, BccTaskTemplateResponse,
    BccDomainCreate, BccDomainUpdate, BccDomainResponse,
    BccIntentCreate, BccIntentResponse, BccIntentTaskResponse,
    # Layer 2 — Organization
    BccOrganizationCreate, BccOrganizationUpdate, BccOrganizationResponse,
    BccOrgProfileCreate, BccOrgProfileUpdate, BccOrgProfileResponse,
    BccDepartmentCreate, BccDepartmentUpdate, BccDepartmentResponse,
    BccTeamCreate, BccTeamUpdate, BccTeamResponse,
    BccOrgDetailResponse,
    # Layer 3 — Regulations
    BccRegulationCreate, BccRegulationUpdate, BccRegulationResponse,
    # Layer 4 — Profile entries
    BccProfileEntryCreate, BccProfileEntryResponse,
    BccProfileSectionResponse, BccProfileResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/bcc")


# ═══════════════════════════════════════════════════════════════
# LAYER 2 — ORGANIZATIONS
# ═══════════════════════════════════════════════════════════════


@router.get("/organizations", response_model=list[BccOrganizationResponse])
async def list_organizations(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all organizations for the current tenant."""
    orgs = db.query(BccOrganization).filter(
        BccOrganization.tenant_id == current_user["tenant_id"],
    ).order_by(BccOrganization.name).all()

    return [
        BccOrganizationResponse(
            id=org.id, name=org.name, description=org.description,
            icon=org.icon, color=org.color,
            profile=BccOrgProfileResponse.model_validate(org.profile) if org.profile else None,
            department_count=len(org.departments),
            industry_count=len(org.industry_links),
        )
        for org in orgs
    ]


@router.post("/organizations", status_code=status.HTTP_201_CREATED, response_model=BccOrganizationResponse)
async def create_organization(
    data: BccOrganizationCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new organization with a default profile."""
    org = BccOrganization(
        tenant_id=current_user["tenant_id"],
        created_by=current_user["email"],
        **data.model_dump(exclude_none=True),
    )
    db.add(org)
    db.flush()

    # Auto-create empty profile
    profile = BccOrgProfile(
        organization_id=org.id,
        tenant_id=current_user["tenant_id"],
        created_by=current_user["email"],
    )
    db.add(profile)
    db.commit()
    db.refresh(org)
    logger.info("bcc_organization_created", org_id=org.id, name=org.name)
    return BccOrganizationResponse(
        id=org.id, name=org.name, description=org.description,
        icon=org.icon, color=org.color,
        profile=BccOrgProfileResponse.model_validate(org.profile) if org.profile else None,
    )


@router.get("/organizations/{org_id}", response_model=BccOrgDetailResponse)
async def get_organization_detail(
    org_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get organization detail with profile, departments, industries, regulations."""
    org = db.query(BccOrganization).filter(
        BccOrganization.id == org_id,
        BccOrganization.tenant_id == current_user["tenant_id"],
    ).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    departments = [
        BccDepartmentResponse(
            id=d.id, name=d.name, description=d.description,
            organization_id=d.organization_id, team_count=len(d.teams),
        ) for d in org.departments
    ]
    industries = [
        BccIndustryResponse.model_validate(link.industry)
        for link in org.industry_links
    ]
    regulations = []
    if org.profile:
        regulations = [BccRegulationResponse.model_validate(r) for r in org.profile.regulations]

    return BccOrgDetailResponse(
        id=org.id, name=org.name, description=org.description,
        icon=org.icon, color=org.color,
        profile=BccOrgProfileResponse.model_validate(org.profile) if org.profile else None,
        departments=departments,
        industries=industries,
        regulations=regulations,
    )


@router.put("/organizations/{org_id}", response_model=BccOrganizationResponse)
async def update_organization(
    org_id: str,
    data: BccOrganizationUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an organization."""
    org = db.query(BccOrganization).filter(
        BccOrganization.id == org_id,
        BccOrganization.tenant_id == current_user["tenant_id"],
    ).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    for key, value in data.model_dump(exclude_none=True).items():
        setattr(org, key, value)
    org.updated_by = current_user["email"]
    db.commit()
    db.refresh(org)
    return BccOrganizationResponse(
        id=org.id, name=org.name, description=org.description,
        icon=org.icon, color=org.color,
        profile=BccOrgProfileResponse.model_validate(org.profile) if org.profile else None,
        department_count=len(org.departments),
        industry_count=len(org.industry_links),
    )


@router.delete("/organizations/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an organization and all its children (cascade)."""
    org = db.query(BccOrganization).filter(
        BccOrganization.id == org_id,
        BccOrganization.tenant_id == current_user["tenant_id"],
    ).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    logger.info("bcc_organization_deleted", org_id=org.id, name=org.name)
    db.delete(org)
    db.commit()


# ── Organization Profile ─────────────────────────────────────


@router.put("/organizations/{org_id}/profile", response_model=BccOrgProfileResponse)
async def update_org_profile(
    org_id: str,
    data: BccOrgProfileUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update organization profile (jurisdiction, domains)."""
    profile = db.query(BccOrgProfile).filter(
        BccOrgProfile.organization_id == org_id,
        BccOrgProfile.tenant_id == current_user["tenant_id"],
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Organization profile not found")

    for key, value in data.model_dump(exclude_none=True).items():
        setattr(profile, key, value)
    profile.updated_by = current_user["email"]
    db.commit()
    db.refresh(profile)
    return BccOrgProfileResponse.model_validate(profile)


# ── Departments ──────────────────────────────────────────────


@router.get("/organizations/{org_id}/departments", response_model=list[BccDepartmentResponse])
async def list_departments(
    org_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List departments for an organization."""
    depts = db.query(BccDepartment).filter(
        BccDepartment.organization_id == org_id,
        BccDepartment.tenant_id == current_user["tenant_id"],
    ).order_by(BccDepartment.name).all()
    return [
        BccDepartmentResponse(
            id=d.id, name=d.name, description=d.description,
            organization_id=d.organization_id, team_count=len(d.teams),
        ) for d in depts
    ]


@router.post("/organizations/{org_id}/departments", status_code=status.HTTP_201_CREATED, response_model=BccDepartmentResponse)
async def create_department(
    org_id: str,
    data: BccDepartmentCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a department in an organization."""
    org = db.query(BccOrganization).filter(
        BccOrganization.id == org_id,
        BccOrganization.tenant_id == current_user["tenant_id"],
    ).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    dept = BccDepartment(
        organization_id=org_id,
        tenant_id=current_user["tenant_id"],
        created_by=current_user["email"],
        **data.model_dump(exclude_none=True),
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    logger.info("bcc_department_created", dept_id=dept.id, org_id=org_id)
    return BccDepartmentResponse(
        id=dept.id, name=dept.name, description=dept.description,
        organization_id=dept.organization_id, team_count=0,
    )


@router.delete("/departments/{dept_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    dept_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a department and all its children (cascade)."""
    dept = db.query(BccDepartment).filter(
        BccDepartment.id == dept_id,
        BccDepartment.tenant_id == current_user["tenant_id"],
    ).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    db.delete(dept)
    db.commit()


# ── Teams ────────────────────────────────────────────────────


@router.get("/departments/{dept_id}/teams", response_model=list[BccTeamResponse])
async def list_teams(
    dept_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List teams for a department."""
    teams = db.query(BccTeam).filter(
        BccTeam.department_id == dept_id,
        BccTeam.tenant_id == current_user["tenant_id"],
    ).order_by(BccTeam.name).all()
    return [
        BccTeamResponse(
            id=t.id, name=t.name, description=t.description,
            department_id=t.department_id, role_count=len(t.roles),
        ) for t in teams
    ]


@router.post("/departments/{dept_id}/teams", status_code=status.HTTP_201_CREATED, response_model=BccTeamResponse)
async def create_team(
    dept_id: str,
    data: BccTeamCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a team in a department."""
    dept = db.query(BccDepartment).filter(
        BccDepartment.id == dept_id,
        BccDepartment.tenant_id == current_user["tenant_id"],
    ).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    team = BccTeam(
        department_id=dept_id,
        tenant_id=current_user["tenant_id"],
        created_by=current_user["email"],
        **data.model_dump(exclude_none=True),
    )
    db.add(team)
    db.commit()
    db.refresh(team)
    logger.info("bcc_team_created", team_id=team.id, dept_id=dept_id)
    return BccTeamResponse(
        id=team.id, name=team.name, description=team.description,
        department_id=team.department_id, role_count=0,
    )


@router.delete("/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a team and all its children (cascade)."""
    team = db.query(BccTeam).filter(
        BccTeam.id == team_id,
        BccTeam.tenant_id == current_user["tenant_id"],
    ).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    db.delete(team)
    db.commit()


# ═══════════════════════════════════════════════════════════════
# LAYER 1 — LIBRARY
# ═══════════════════════════════════════════════════════════════


# ── Industries ───────────────────────────────────────────────


@router.get("/industries", response_model=list[BccIndustryResponse])
async def list_industries(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all industry templates."""
    items = db.query(BccIndustry).filter(
        BccIndustry.tenant_id == current_user["tenant_id"],
    ).order_by(BccIndustry.name).all()
    return [BccIndustryResponse.model_validate(i) for i in items]


@router.get("/industries/{industry_id}", response_model=BccIndustryResponse)
async def get_industry(
    industry_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single industry template by ID."""
    item = db.query(BccIndustry).filter(
        BccIndustry.id == industry_id,
        BccIndustry.tenant_id == current_user["tenant_id"],
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Industry not found")
    return BccIndustryResponse.model_validate(item)


@router.post("/industries", status_code=status.HTTP_201_CREATED, response_model=BccIndustryResponse)
async def create_industry(
    data: BccIndustryCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create an industry template."""
    item = BccIndustry(
        tenant_id=current_user["tenant_id"],
        created_by=current_user["email"],
        **data.model_dump(exclude_none=True),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    logger.info("bcc_industry_created", id=item.id, name=item.name)
    return BccIndustryResponse.model_validate(item)


@router.put("/industries/{industry_id}", response_model=BccIndustryResponse)
async def update_industry(
    industry_id: str,
    data: BccIndustryUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an industry template."""
    item = db.query(BccIndustry).filter(
        BccIndustry.id == industry_id,
        BccIndustry.tenant_id == current_user["tenant_id"],
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Industry not found")
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(item, key, value)
    item.updated_by = current_user["email"]
    db.commit()
    db.refresh(item)
    return BccIndustryResponse.model_validate(item)


@router.delete("/industries/{industry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_industry(
    industry_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an industry template."""
    item = db.query(BccIndustry).filter(
        BccIndustry.id == industry_id,
        BccIndustry.tenant_id == current_user["tenant_id"],
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Industry not found")
    db.delete(item)
    db.commit()


# ── Careers ──────────────────────────────────────────────────


@router.get("/careers", response_model=list[BccCareerResponse])
async def list_careers(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all career templates."""
    items = db.query(BccCareer).filter(
        BccCareer.tenant_id == current_user["tenant_id"],
    ).order_by(BccCareer.name).all()
    return [BccCareerResponse.model_validate(i) for i in items]


@router.get("/careers/{career_id}", response_model=BccCareerResponse)
async def get_career(
    career_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single career template by ID."""
    item = db.query(BccCareer).filter(
        BccCareer.id == career_id,
        BccCareer.tenant_id == current_user["tenant_id"],
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Career not found")
    return BccCareerResponse.model_validate(item)


@router.post("/careers", status_code=status.HTTP_201_CREATED, response_model=BccCareerResponse)
async def create_career(
    data: BccCareerCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a career template."""
    item = BccCareer(
        tenant_id=current_user["tenant_id"],
        created_by=current_user["email"],
        **data.model_dump(exclude_none=True),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    logger.info("bcc_career_created", id=item.id, name=item.name)
    return BccCareerResponse.model_validate(item)


@router.delete("/careers/{career_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_career(
    career_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a career template."""
    item = db.query(BccCareer).filter(
        BccCareer.id == career_id,
        BccCareer.tenant_id == current_user["tenant_id"],
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Career not found")
    db.delete(item)
    db.commit()


# ── Skill Templates ─────────────────────────────────────────


@router.get("/skill-templates", response_model=list[BccSkillTemplateResponse])
async def list_skill_templates(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all skill templates."""
    items = db.query(BccSkillTemplate).filter(
        BccSkillTemplate.tenant_id == current_user["tenant_id"],
    ).order_by(BccSkillTemplate.name).all()
    return [BccSkillTemplateResponse.model_validate(i) for i in items]


@router.get("/skill-templates/{template_id}", response_model=BccSkillTemplateResponse)
async def get_skill_template(
    template_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single skill template by ID."""
    item = db.query(BccSkillTemplate).filter(
        BccSkillTemplate.id == template_id,
        BccSkillTemplate.tenant_id == current_user["tenant_id"],
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Skill template not found")
    return BccSkillTemplateResponse.model_validate(item)


@router.post("/skill-templates", status_code=status.HTTP_201_CREATED, response_model=BccSkillTemplateResponse)
async def create_skill_template(
    data: BccSkillTemplateCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a skill template."""
    item = BccSkillTemplate(
        tenant_id=current_user["tenant_id"],
        created_by=current_user["email"],
        **data.model_dump(exclude_none=True),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    logger.info("bcc_skill_template_created", id=item.id, name=item.name)
    return BccSkillTemplateResponse.model_validate(item)


@router.delete("/skill-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill_template(
    template_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a skill template."""
    item = db.query(BccSkillTemplate).filter(
        BccSkillTemplate.id == template_id,
        BccSkillTemplate.tenant_id == current_user["tenant_id"],
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Skill template not found")
    db.delete(item)
    db.commit()


# ── Task Templates ───────────────────────────────────────────


@router.get("/task-templates", response_model=list[BccTaskTemplateResponse])
async def list_task_templates(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all task templates."""
    items = db.query(BccTaskTemplate).filter(
        BccTaskTemplate.tenant_id == current_user["tenant_id"],
    ).order_by(BccTaskTemplate.name).all()
    return [BccTaskTemplateResponse.model_validate(i) for i in items]


@router.get("/task-templates/{template_id}", response_model=BccTaskTemplateResponse)
async def get_task_template(
    template_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single task template by ID."""
    item = db.query(BccTaskTemplate).filter(
        BccTaskTemplate.id == template_id,
        BccTaskTemplate.tenant_id == current_user["tenant_id"],
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Task template not found")
    return BccTaskTemplateResponse.model_validate(item)


@router.post("/task-templates", status_code=status.HTTP_201_CREATED, response_model=BccTaskTemplateResponse)
async def create_task_template(
    data: BccTaskTemplateCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a task template."""
    item = BccTaskTemplate(
        tenant_id=current_user["tenant_id"],
        created_by=current_user["email"],
        **data.model_dump(exclude_none=True),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    logger.info("bcc_task_template_created", id=item.id, name=item.name)
    return BccTaskTemplateResponse.model_validate(item)


@router.delete("/task-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_template(
    template_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a task template."""
    item = db.query(BccTaskTemplate).filter(
        BccTaskTemplate.id == template_id,
        BccTaskTemplate.tenant_id == current_user["tenant_id"],
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Task template not found")
    db.delete(item)
    db.commit()


# ── Domains ──────────────────────────────────────────────────

@router.get("/domains", response_model=list[BccDomainResponse])
async def list_domains(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all domains."""
    items = db.query(BccDomain).filter(
        BccDomain.tenant_id == current_user["tenant_id"],
    ).order_by(BccDomain.name).all()
    return [
        BccDomainResponse(
            id=d.id,
            name=d.name,
            description=d.description,
            icon=d.icon,
            intent_count=len(d.intents)
        )
        for d in items
    ]


@router.post("/domains", status_code=status.HTTP_201_CREATED, response_model=BccDomainResponse)
async def create_domain(
    data: BccDomainCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new domain."""
    item = BccDomain(
        tenant_id=current_user["tenant_id"],
        created_by=current_user["email"],
        **data.model_dump(exclude_none=True),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    logger.info("bcc_domain_created", id=item.id, name=item.name)
    return BccDomainResponse(
        id=item.id,
        name=item.name,
        description=item.description,
        icon=item.icon,
        intent_count=0
    )


@router.delete("/domains/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_domain(
    domain_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a domain."""
    item = db.query(BccDomain).filter(
        BccDomain.id == domain_id,
        BccDomain.tenant_id == current_user["tenant_id"],
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Domain not found")
    db.delete(item)
    db.commit()


# ── Intents ──────────────────────────────────────────────────


@router.get("/intents", response_model=list[BccIntentResponse])
async def list_intents(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all intents with their linked tasks."""
    items = db.query(BccIntent).filter(
        BccIntent.tenant_id == current_user["tenant_id"],
    ).order_by(BccIntent.name).all()
    result = []
    for intent in items:
        tasks = [
            BccIntentTaskResponse(
                id=link.id,
                task_template_id=link.task_template_id,
                task_template_name=link.task_template.name if link.task_template else "",
                sort_order=link.sort_order,
                tool_name=link.tool_name,
            )
            for link in intent.task_links
        ]
        result.append(BccIntentResponse(
            id=intent.id,
            name=intent.name,
            description=intent.description,
            trigger_phrases=intent.trigger_phrases,
            category=intent.category,
            domain_id=intent.domain_id,
            domain_name=intent.domain.name if intent.domain else None,
            workflow_key=intent.workflow_key,
            pipeline_key=intent.pipeline_key,
            task_count=len(tasks),
            tasks=tasks,
        ))
    return result


@router.get("/intents/{intent_id}", response_model=BccIntentResponse)
async def get_intent(
    intent_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single intent with its linked tasks."""
    intent = db.query(BccIntent).filter(
        BccIntent.id == intent_id,
        BccIntent.tenant_id == current_user["tenant_id"],
    ).first()
    if not intent:
        raise HTTPException(status_code=404, detail="Intent not found")
    tasks = [
        BccIntentTaskResponse(
            id=link.id,
            task_template_id=link.task_template_id,
            task_template_name=link.task_template.name if link.task_template else "",
            sort_order=link.sort_order,
            tool_name=link.tool_name,
        )
        for link in intent.task_links
    ]
    return BccIntentResponse(
        id=intent.id,
        name=intent.name,
        description=intent.description,
        trigger_phrases=intent.trigger_phrases,
        category=intent.category,
        domain_id=intent.domain_id,
        domain_name=intent.domain.name if intent.domain else None,
        workflow_key=intent.workflow_key,
        pipeline_key=intent.pipeline_key,
        task_count=len(tasks),
        tasks=tasks,
    )


@router.post("/intents", status_code=status.HTTP_201_CREATED, response_model=BccIntentResponse)
async def create_intent(
    data: BccIntentCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create an intent and link task templates."""
    intent = BccIntent(
        tenant_id=current_user["tenant_id"],
        created_by=current_user["email"],
        name=data.name,
        description=data.description,
        trigger_phrases=data.trigger_phrases,
        category=data.category,
        domain_id=data.domain_id,
        workflow_key=data.workflow_key,
        pipeline_key=data.pipeline_key,
    )
    db.add(intent)
    db.flush()

    if data.task_template_ids:
        for idx, tpl_id in enumerate(data.task_template_ids):
            link = BccIntentTask(
                intent_id=intent.id,
                task_template_id=tpl_id,
                sort_order=idx,
                tenant_id=current_user["tenant_id"],
            )
            db.add(link)

    db.commit()
    db.refresh(intent)
    logger.info("bcc_intent_created", id=intent.id, name=intent.name)

    tasks = [
        BccIntentTaskResponse(
            id=link.id,
            task_template_id=link.task_template_id,
            task_template_name=link.task_template.name if link.task_template else "",
            sort_order=link.sort_order,
            tool_name=link.tool_name,
        )
        for link in intent.task_links
    ]
    return BccIntentResponse(
        id=intent.id,
        name=intent.name,
        description=intent.description,
        trigger_phrases=intent.trigger_phrases,
        category=intent.category,
        domain_id=intent.domain_id,
        domain_name=intent.domain.name if intent.domain else None,
        workflow_key=intent.workflow_key,
        pipeline_key=intent.pipeline_key,
        task_count=len(tasks),
        tasks=tasks,
    )


@router.delete("/intents/{intent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_intent(
    intent_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an intent and its task links."""
    intent = db.query(BccIntent).filter(
        BccIntent.id == intent_id,
        BccIntent.tenant_id == current_user["tenant_id"],
    ).first()
    if not intent:
        raise HTTPException(status_code=404, detail="Intent not found")
    db.delete(intent)
    db.commit()


# ── Cognitive Map ────────────────────────────────────────────


@router.get("/cognitive-map")
async def get_cognitive_map(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the full Domain -> Intent -> Task tree for the cognitive flow view."""
    from sqlalchemy.orm import joinedload

    domains = (
        db.query(BccDomain)
        .filter(BccDomain.tenant_id == current_user["tenant_id"])
        .options(
            joinedload(BccDomain.intents)
            .joinedload(BccIntent.task_links)
            .joinedload(BccIntentTask.task_template)
        )
        .order_by(BccDomain.name)
        .all()
    )

    result = []
    for domain in domains:
        intents_out = []
        for intent in sorted(domain.intents, key=lambda i: i.name):
            tasks_out = []
            for link in sorted(intent.task_links, key=lambda l: l.sort_order):
                tasks_out.append({
                    "id": link.id,
                    "sort_order": link.sort_order,
                    "tool_name": link.tool_name,
                    "task_template": {
                        "id": link.task_template.id,
                        "name": link.task_template.name,
                        "description": link.task_template.description,
                        "context": link.task_template.context or {},
                        "frequency": link.task_template.frequency,
                        "category": link.task_template.category,
                    } if link.task_template else None,
                })
            intents_out.append({
                "id": intent.id,
                "name": intent.name,
                "description": intent.description,
                "workflow_key": intent.workflow_key,
                "pipeline_key": intent.pipeline_key,
                "category": intent.category,
                "trigger_phrases": intent.trigger_phrases or [],
                "tasks": tasks_out,
            })
        result.append({
            "id": domain.id,
            "name": domain.name,
            "description": domain.description,
            "icon": domain.icon,
            "intent_count": len(intents_out),
            "task_count": sum(len(i["tasks"]) for i in intents_out),
            "intents": intents_out,
        })

    return result


# ═══════════════════════════════════════════════════════════════
# LAYER 3 — REGULATIONS
# ═══════════════════════════════════════════════════════════════


@router.get("/organizations/{org_id}/regulations", response_model=list[BccRegulationResponse])
async def list_regulations(
    org_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List regulations for an organization (via its profile)."""
    profile = db.query(BccOrgProfile).filter(
        BccOrgProfile.organization_id == org_id,
        BccOrgProfile.tenant_id == current_user["tenant_id"],
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Organization profile not found")
    return [BccRegulationResponse.model_validate(r) for r in profile.regulations]


@router.post("/organizations/{org_id}/regulations", status_code=status.HTTP_201_CREATED, response_model=BccRegulationResponse)
async def create_regulation(
    org_id: str,
    data: BccRegulationCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a regulation to an organization."""
    profile = db.query(BccOrgProfile).filter(
        BccOrgProfile.organization_id == org_id,
        BccOrgProfile.tenant_id == current_user["tenant_id"],
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Organization profile not found")

    reg = BccRegulation(
        profile_id=profile.id,
        tenant_id=current_user["tenant_id"],
        created_by=current_user["email"],
        **data.model_dump(exclude_none=True),
    )
    db.add(reg)
    db.commit()
    db.refresh(reg)
    logger.info("bcc_regulation_created", id=reg.id, org_id=org_id)
    return BccRegulationResponse.model_validate(reg)


@router.delete("/regulations/{reg_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_regulation(
    reg_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a regulation."""
    reg = db.query(BccRegulation).filter(
        BccRegulation.id == reg_id,
        BccRegulation.tenant_id == current_user["tenant_id"],
    ).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Regulation not found")
    db.delete(reg)
    db.commit()


# ── Organization ↔ Industry links ────────────────────────────


@router.post("/organizations/{org_id}/industries/{industry_id}", status_code=status.HTTP_201_CREATED)
async def link_org_industry(
    org_id: str,
    industry_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Link an industry to an organization."""
    link = BccOrgIndustry(
        organization_id=org_id,
        industry_id=industry_id,
        tenant_id=current_user["tenant_id"],
    )
    db.add(link)
    db.commit()
    return {"status": "linked"}


@router.delete("/organizations/{org_id}/industries/{industry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_org_industry(
    org_id: str,
    industry_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Unlink an industry from an organization."""
    link = db.query(BccOrgIndustry).filter(
        BccOrgIndustry.organization_id == org_id,
        BccOrgIndustry.industry_id == industry_id,
    ).first()
    if link:
        db.delete(link)
        db.commit()


# ═══════════════════════════════════════════════════════════════
# EXISTING ROUTES — Roles (backward compatible)
# ═══════════════════════════════════════════════════════════════


@router.get("/roles", response_model=list[BccRoleResponse])
async def list_roles(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all roles for the current tenant."""
    roles = db.query(BccRole).filter(
        BccRole.tenant_id == current_user["tenant_id"],
    ).order_by(BccRole.name).all()

    result = []
    for role in roles:
        result.append(BccRoleResponse(
            id=role.id,
            name=role.name,
            team_id=role.team_id,
            department=role.department,
            description=role.description,
            icon=role.icon,
            color=role.color,
            kpis=role.kpis,
            context=role.context,
            skill_count=len(role.skills),
            task_count=len(role.tasks),
            user_count=len(role.user_roles),
        ))
    return result


@router.post("/roles", status_code=status.HTTP_201_CREATED, response_model=BccRoleResponse)
async def create_role(
    data: BccRoleCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new role."""
    role = BccRole(
        tenant_id=current_user["tenant_id"],
        created_by=current_user["email"],
        **data.model_dump(exclude_none=True),
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    logger.info("bcc_role_created", role_id=role.id, name=role.name)
    return BccRoleResponse(
        id=role.id, name=role.name, team_id=role.team_id,
        department=role.department, description=role.description,
        icon=role.icon, color=role.color,
        kpis=role.kpis, context=role.context,
    )


@router.get("/roles/{role_id}", response_model=BccRoleDetailResponse)
async def get_role_detail(
    role_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get role detail with all skills, tasks, and milestones."""
    role = db.query(BccRole).filter(
        BccRole.id == role_id,
        BccRole.tenant_id == current_user["tenant_id"],
    ).first()

    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    return BccRoleDetailResponse(
        id=role.id,
        name=role.name,
        team_id=role.team_id,
        department=role.department,
        description=role.description,
        icon=role.icon,
        color=role.color,
        kpis=role.kpis,
        context=role.context,
        skills=[BccSkillResponse.model_validate(s) for s in role.skills],
        tasks=[BccTaskResponse.model_validate(t) for t in role.tasks],
        milestones=[BccMilestoneResponse.model_validate(m) for m in role.milestones],
        user_count=len(role.user_roles),
    )


@router.put("/roles/{role_id}", response_model=BccRoleResponse)
async def update_role(
    role_id: str,
    data: BccRoleUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a role."""
    role = db.query(BccRole).filter(
        BccRole.id == role_id,
        BccRole.tenant_id == current_user["tenant_id"],
    ).first()

    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(role, key, value)

    role.updated_by = current_user["email"]
    db.commit()
    db.refresh(role)
    logger.info("bcc_role_updated", role_id=role.id)

    return BccRoleResponse(
        id=role.id, name=role.name, team_id=role.team_id,
        department=role.department,
        description=role.description, icon=role.icon, color=role.color,
        kpis=role.kpis, context=role.context,
        skill_count=len(role.skills), task_count=len(role.tasks),
        user_count=len(role.user_roles),
    )


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a role and all its children (cascade)."""
    role = db.query(BccRole).filter(
        BccRole.id == role_id,
        BccRole.tenant_id == current_user["tenant_id"],
    ).first()

    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    logger.info("bcc_role_deleted", role_id=role.id, name=role.name)
    db.delete(role)
    db.commit()


# ── Roles under Teams ────────────────────────────────────────


@router.get("/teams/{team_id}/roles", response_model=list[BccRoleResponse])
async def list_team_roles(
    team_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List roles for a team."""
    roles = db.query(BccRole).filter(
        BccRole.team_id == team_id,
        BccRole.tenant_id == current_user["tenant_id"],
    ).order_by(BccRole.name).all()
    return [
        BccRoleResponse(
            id=r.id, name=r.name, team_id=r.team_id,
            department=r.department, description=r.description,
            icon=r.icon, color=r.color,
            skill_count=len(r.skills), task_count=len(r.tasks),
            user_count=len(r.user_roles),
        ) for r in roles
    ]


# ═══════════════════════════════════════════════════════════════
# EXISTING ROUTES — Skills, Tasks, Resources, Milestones
# ═══════════════════════════════════════════════════════════════


# ── Skills ───────────────────────────────────────────────────


@router.post("/roles/{role_id}/skills", status_code=status.HTTP_201_CREATED, response_model=BccSkillResponse)
async def add_skill(
    role_id: str,
    data: BccSkillCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a skill to a role."""
    role = db.query(BccRole).filter(
        BccRole.id == role_id,
        BccRole.tenant_id == current_user["tenant_id"],
    ).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    skill = BccSkill(
        role_id=role_id,
        tenant_id=current_user["tenant_id"],
        created_by=current_user["email"],
        **data.model_dump(exclude_none=True),
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    logger.info("bcc_skill_created", skill_id=skill.id, role_id=role_id)
    return BccSkillResponse.model_validate(skill)


@router.get("/skills/{skill_id}", response_model=BccSkillResponse)
async def get_skill(
    skill_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single skill by ID."""
    skill = db.query(BccSkill).filter(
        BccSkill.id == skill_id,
        BccSkill.tenant_id == current_user["tenant_id"],
    ).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return BccSkillResponse.model_validate(skill)


@router.put("/skills/{skill_id}", response_model=BccSkillResponse)
async def update_skill(
    skill_id: str,
    data: BccSkillUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a skill."""
    skill = db.query(BccSkill).filter(
        BccSkill.id == skill_id,
        BccSkill.tenant_id == current_user["tenant_id"],
    ).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    for key, value in data.model_dump(exclude_none=True).items():
        setattr(skill, key, value)
    skill.updated_by = current_user["email"]
    db.commit()
    db.refresh(skill)
    return BccSkillResponse.model_validate(skill)


@router.delete("/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    skill_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a skill."""
    skill = db.query(BccSkill).filter(
        BccSkill.id == skill_id,
        BccSkill.tenant_id == current_user["tenant_id"],
    ).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    db.delete(skill)
    db.commit()


# ── Tasks ────────────────────────────────────────────────────


@router.post("/roles/{role_id}/tasks", status_code=status.HTTP_201_CREATED, response_model=BccTaskResponse)
async def add_task(
    role_id: str,
    data: BccTaskCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a task to a role."""
    role = db.query(BccRole).filter(
        BccRole.id == role_id,
        BccRole.tenant_id == current_user["tenant_id"],
    ).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    task = BccTask(
        role_id=role_id,
        tenant_id=current_user["tenant_id"],
        created_by=current_user["email"],
        **data.model_dump(exclude_none=True),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    logger.info("bcc_task_created", task_id=task.id, role_id=role_id)
    return BccTaskResponse.model_validate(task)


@router.get("/tasks/{task_id}", response_model=BccTaskResponse)
async def get_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single task by ID."""
    task = db.query(BccTask).filter(
        BccTask.id == task_id,
        BccTask.tenant_id == current_user["tenant_id"],
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return BccTaskResponse.model_validate(task)


@router.put("/tasks/{task_id}", response_model=BccTaskResponse)
async def update_task(
    task_id: str,
    data: BccTaskUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a task."""
    task = db.query(BccTask).filter(
        BccTask.id == task_id,
        BccTask.tenant_id == current_user["tenant_id"],
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    for key, value in data.model_dump(exclude_none=True).items():
        setattr(task, key, value)
    task.updated_by = current_user["email"]
    db.commit()
    db.refresh(task)
    return BccTaskResponse.model_validate(task)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a task."""
    task = db.query(BccTask).filter(
        BccTask.id == task_id,
        BccTask.tenant_id == current_user["tenant_id"],
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()


# ── Task Steps ───────────────────────────────────────────────


@router.post("/tasks/{task_id}/steps", status_code=status.HTTP_201_CREATED, response_model=BccTaskStepResponse)
async def add_task_step(
    task_id: str,
    data: BccTaskStepCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a step to a task."""
    task = db.query(BccTask).filter(
        BccTask.id == task_id,
        BccTask.tenant_id == current_user["tenant_id"],
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    step = BccTaskStep(
        task_id=task_id,
        **data.model_dump(),
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return BccTaskStepResponse.model_validate(step)


# ── Resources ────────────────────────────────────────────────


@router.post("/skills/{skill_id}/resources", status_code=status.HTTP_201_CREATED, response_model=BccResourceResponse)
async def add_resource(
    skill_id: str,
    data: BccResourceCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a learning resource to a skill."""
    skill = db.query(BccSkill).filter(
        BccSkill.id == skill_id,
        BccSkill.tenant_id == current_user["tenant_id"],
    ).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    resource = BccResource(
        skill_id=skill_id,
        tenant_id=current_user["tenant_id"],
        created_by=current_user["email"],
        **data.model_dump(exclude_none=True),
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return BccResourceResponse.model_validate(resource)


# ── Milestones ───────────────────────────────────────────────


@router.post("/roles/{role_id}/milestones", status_code=status.HTTP_201_CREATED, response_model=BccMilestoneResponse)
async def add_milestone(
    role_id: str,
    data: BccMilestoneCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a milestone to a role."""
    role = db.query(BccRole).filter(
        BccRole.id == role_id,
        BccRole.tenant_id == current_user["tenant_id"],
    ).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    milestone = BccMilestone(
        role_id=role_id,
        tenant_id=current_user["tenant_id"],
        created_by=current_user["email"],
        **data.model_dump(exclude_none=True),
    )
    db.add(milestone)
    db.commit()
    db.refresh(milestone)
    return BccMilestoneResponse.model_validate(milestone)


# ═══════════════════════════════════════════════════════════════
# LAYER 4 — PROFILE ENTRIES (versioned knowledge)
# ═══════════════════════════════════════════════════════════════

VALID_ENTITY_TYPES = {
    "industry", "career", "skill_template", "task_template",
    "organization", "department", "team", "role", "regulation",
}
VALID_PERSPECTIVES = {"general", "ceo", "cfo", "director", "employee"}


def _validate_entity_type(entity_type: str) -> None:
    if entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity_type '{entity_type}'. Valid: {sorted(VALID_ENTITY_TYPES)}",
        )


@router.post(
    "/profiles/{entity_type}/{entity_id}/entries",
    status_code=status.HTTP_201_CREATED,
    response_model=BccProfileEntryResponse,
)
async def create_profile_entry(
    entity_type: str,
    entity_id: str,
    data: BccProfileEntryCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a versioned profile entry for any BCC entity.

    Auto-increments version and deactivates previous version for the
    same (entity_type, entity_id, section, perspective) tuple.
    """
    _validate_entity_type(entity_type)
    if data.perspective not in VALID_PERSPECTIVES:
        raise HTTPException(status_code=400, detail=f"Invalid perspective '{data.perspective}'")

    tenant_id = current_user["tenant_id"]

    # Find latest version for this section + perspective
    latest = (
        db.query(BccProfileEntry)
        .filter(
            BccProfileEntry.tenant_id == tenant_id,
            BccProfileEntry.entity_type == entity_type,
            BccProfileEntry.entity_id == entity_id,
            BccProfileEntry.section == data.section,
            BccProfileEntry.perspective == data.perspective,
        )
        .order_by(BccProfileEntry.version.desc())
        .first()
    )

    new_version = (latest.version + 1) if latest else 1

    # Deactivate previous active version
    if latest and latest.is_active:
        latest.is_active = False

    entry = BccProfileEntry(
        tenant_id=tenant_id,
        entity_type=entity_type,
        entity_id=entity_id,
        section=data.section,
        content=data.content,
        structured_data=data.structured_data,
        perspective=data.perspective,
        version=new_version,
        is_active=True,
        contributed_by=current_user.get("user_id"),
        contributor_name=current_user.get("email", "unknown"),
        contribution_method=data.contribution_method,
        conversation_id=data.conversation_id,
        created_by=current_user["email"],
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    logger.info("profile_entry_created",
                entity_type=entity_type, entity_id=entity_id,
                section=data.section, perspective=data.perspective,
                version=new_version)

    # Index in RAG for semantic retrieval
    if entry.content:
        try:
            from app.rag.indexer import index_bcc_profile_entry
            index_bcc_profile_entry(
                db=db,
                entity_type=entity_type,
                entity_id=entity_id,
                section=data.section,
                content=entry.content,
                tenant_id=tenant_id,
            )
        except Exception as rag_err:
            logger.warning("rag_index_profile_failed", error=str(rag_err))

    return BccProfileEntryResponse.model_validate(entry)


@router.get(
    "/profiles/{entity_type}/{entity_id}",
    response_model=BccProfileResponse,
)
async def get_profile(
    entity_type: str,
    entity_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full profile for an entity — all active sections grouped by section name."""
    _validate_entity_type(entity_type)

    entries = (
        db.query(BccProfileEntry)
        .filter(
            BccProfileEntry.tenant_id == current_user["tenant_id"],
            BccProfileEntry.entity_type == entity_type,
            BccProfileEntry.entity_id == entity_id,
            BccProfileEntry.is_active == True,  # noqa: E712
        )
        .order_by(BccProfileEntry.section, BccProfileEntry.perspective)
        .all()
    )

    # Group by section
    sections_map: dict[str, list] = {}
    for e in entries:
        sections_map.setdefault(e.section, []).append(
            BccProfileEntryResponse.model_validate(e)
        )

    sections = [
        BccProfileSectionResponse(section=sec, perspectives=persp)
        for sec, persp in sections_map.items()
    ]

    return BccProfileResponse(
        entity_type=entity_type,
        entity_id=entity_id,
        sections=sections,
    )

@router.get(
    "/profiles/{entity_type}/{entity_id}/history",
    response_model=list[BccProfileEntryResponse],
)
async def get_profile_history(
    entity_type: str,
    entity_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full version history for all sections of an entity."""
    _validate_entity_type(entity_type)

    entries = (
        db.query(BccProfileEntry)
        .filter(
            BccProfileEntry.tenant_id == current_user["tenant_id"],
            BccProfileEntry.entity_type == entity_type,
            BccProfileEntry.entity_id == entity_id,
        )
        .order_by(BccProfileEntry.section, BccProfileEntry.version.desc())
        .all()
    )

    return [BccProfileEntryResponse.model_validate(e) for e in entries]


@router.get(
    "/profiles/{entity_type}/{entity_id}/{section}",
    response_model=BccProfileSectionResponse,
)
async def get_profile_section(
    entity_type: str,
    entity_id: str,
    section: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific section with all its active perspectives."""
    _validate_entity_type(entity_type)

    entries = (
        db.query(BccProfileEntry)
        .filter(
            BccProfileEntry.tenant_id == current_user["tenant_id"],
            BccProfileEntry.entity_type == entity_type,
            BccProfileEntry.entity_id == entity_id,
            BccProfileEntry.section == section,
            BccProfileEntry.is_active == True,  # noqa: E712
        )
        .order_by(BccProfileEntry.perspective)
        .all()
    )

    return BccProfileSectionResponse(
        section=section,
        perspectives=[BccProfileEntryResponse.model_validate(e) for e in entries],
    )

