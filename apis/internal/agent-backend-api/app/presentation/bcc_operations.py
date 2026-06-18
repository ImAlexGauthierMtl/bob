"""BCC operations used by the BCC use case adapter."""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import structlog

from app.infrastructure.persistence.models.bcc_entities import (
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

logger = structlog.get_logger(__name__)

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


class BccOperations:
    def __init__(self, db: Session) -> None:
        self.db = db

    async def list_organizations(self, current_user: dict):
        orgs = self.db.query(BccOrganization).filter(
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

    async def create_organization(self, data: BccOrganizationCreate, current_user: dict):
        org = BccOrganization(
            tenant_id=current_user["tenant_id"],
            created_by=current_user["email"],
            **data.model_dump(exclude_none=True),
        )
        self.db.add(org)
        self.db.flush()
    
        profile = BccOrgProfile(
            organization_id=org.id,
            tenant_id=current_user["tenant_id"],
            created_by=current_user["email"],
        )
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(org)
        logger.info("bcc_organization_created", org_id=org.id, name=org.name)
        return BccOrganizationResponse(
            id=org.id, name=org.name, description=org.description,
            icon=org.icon, color=org.color,
            profile=BccOrgProfileResponse.model_validate(org.profile) if org.profile else None,
        )

    async def get_organization_detail(self, org_id: str, current_user: dict):
        org = self.db.query(BccOrganization).filter(
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

    async def update_organization(self, org_id: str, data: BccOrganizationUpdate, current_user: dict):
        org = self.db.query(BccOrganization).filter(
            BccOrganization.id == org_id,
            BccOrganization.tenant_id == current_user["tenant_id"],
        ).first()
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
    
        for key, value in data.model_dump(exclude_none=True).items():
            setattr(org, key, value)
        org.updated_by = current_user["email"]
        self.db.commit()
        self.db.refresh(org)
        return BccOrganizationResponse(
            id=org.id, name=org.name, description=org.description,
            icon=org.icon, color=org.color,
            profile=BccOrgProfileResponse.model_validate(org.profile) if org.profile else None,
            department_count=len(org.departments),
            industry_count=len(org.industry_links),
        )

    async def delete_organization(self, org_id: str, current_user: dict):
        org = self.db.query(BccOrganization).filter(
            BccOrganization.id == org_id,
            BccOrganization.tenant_id == current_user["tenant_id"],
        ).first()
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        logger.info("bcc_organization_deleted", org_id=org.id, name=org.name)
        self.db.delete(org)
        self.db.commit()

    async def update_org_profile(self, org_id: str, data: BccOrgProfileUpdate, current_user: dict):
        profile = self.db.query(BccOrgProfile).filter(
            BccOrgProfile.organization_id == org_id,
            BccOrgProfile.tenant_id == current_user["tenant_id"],
        ).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Organization profile not found")
    
        for key, value in data.model_dump(exclude_none=True).items():
            setattr(profile, key, value)
        profile.updated_by = current_user["email"]
        self.db.commit()
        self.db.refresh(profile)
        return BccOrgProfileResponse.model_validate(profile)

    async def list_departments(self, org_id: str, current_user: dict):
        depts = self.db.query(BccDepartment).filter(
            BccDepartment.organization_id == org_id,
            BccDepartment.tenant_id == current_user["tenant_id"],
        ).order_by(BccDepartment.name).all()
        return [
            BccDepartmentResponse(
                id=d.id, name=d.name, description=d.description,
                organization_id=d.organization_id, team_count=len(d.teams),
            ) for d in depts
        ]

    async def create_department(self, org_id: str, data: BccDepartmentCreate, current_user: dict):
        org = self.db.query(BccOrganization).filter(
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
        self.db.add(dept)
        self.db.commit()
        self.db.refresh(dept)
        logger.info("bcc_department_created", dept_id=dept.id, org_id=org_id)
        return BccDepartmentResponse(
            id=dept.id, name=dept.name, description=dept.description,
            organization_id=dept.organization_id, team_count=0,
        )

    async def delete_department(self, dept_id: str, current_user: dict):
        dept = self.db.query(BccDepartment).filter(
            BccDepartment.id == dept_id,
            BccDepartment.tenant_id == current_user["tenant_id"],
        ).first()
        if not dept:
            raise HTTPException(status_code=404, detail="Department not found")
        self.db.delete(dept)
        self.db.commit()

    async def list_teams(self, dept_id: str, current_user: dict):
        teams = self.db.query(BccTeam).filter(
            BccTeam.department_id == dept_id,
            BccTeam.tenant_id == current_user["tenant_id"],
        ).order_by(BccTeam.name).all()
        return [
            BccTeamResponse(
                id=t.id, name=t.name, description=t.description,
                department_id=t.department_id, role_count=len(t.roles),
            ) for t in teams
        ]

    async def create_team(self, dept_id: str, data: BccTeamCreate, current_user: dict):
        dept = self.db.query(BccDepartment).filter(
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
        self.db.add(team)
        self.db.commit()
        self.db.refresh(team)
        logger.info("bcc_team_created", team_id=team.id, dept_id=dept_id)
        return BccTeamResponse(
            id=team.id, name=team.name, description=team.description,
            department_id=team.department_id, role_count=0,
        )

    async def delete_team(self, team_id: str, current_user: dict):
        team = self.db.query(BccTeam).filter(
            BccTeam.id == team_id,
            BccTeam.tenant_id == current_user["tenant_id"],
        ).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        self.db.delete(team)
        self.db.commit()

    async def list_industries(self, current_user: dict):
        items = self.db.query(BccIndustry).filter(
            BccIndustry.tenant_id == current_user["tenant_id"],
        ).order_by(BccIndustry.name).all()
        return [BccIndustryResponse.model_validate(i) for i in items]

    async def get_industry(self, industry_id: str, current_user: dict):
        item = self.db.query(BccIndustry).filter(
            BccIndustry.id == industry_id,
            BccIndustry.tenant_id == current_user["tenant_id"],
        ).first()
        if not item:
            raise HTTPException(status_code=404, detail="Industry not found")
        return BccIndustryResponse.model_validate(item)

    async def create_industry(self, data: BccIndustryCreate, current_user: dict):
        item = BccIndustry(
            tenant_id=current_user["tenant_id"],
            created_by=current_user["email"],
            **data.model_dump(exclude_none=True),
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        logger.info("bcc_industry_created", id=item.id, name=item.name)
        return BccIndustryResponse.model_validate(item)

    async def update_industry(self, industry_id: str, data: BccIndustryUpdate, current_user: dict):
        item = self.db.query(BccIndustry).filter(
            BccIndustry.id == industry_id,
            BccIndustry.tenant_id == current_user["tenant_id"],
        ).first()
        if not item:
            raise HTTPException(status_code=404, detail="Industry not found")
        for key, value in data.model_dump(exclude_none=True).items():
            setattr(item, key, value)
        item.updated_by = current_user["email"]
        self.db.commit()
        self.db.refresh(item)
        return BccIndustryResponse.model_validate(item)

    async def delete_industry(self, industry_id: str, current_user: dict):
        item = self.db.query(BccIndustry).filter(
            BccIndustry.id == industry_id,
            BccIndustry.tenant_id == current_user["tenant_id"],
        ).first()
        if not item:
            raise HTTPException(status_code=404, detail="Industry not found")
        self.db.delete(item)
        self.db.commit()

    async def list_careers(self, current_user: dict):
        items = self.db.query(BccCareer).filter(
            BccCareer.tenant_id == current_user["tenant_id"],
        ).order_by(BccCareer.name).all()
        return [BccCareerResponse.model_validate(i) for i in items]

    async def get_career(self, career_id: str, current_user: dict):
        item = self.db.query(BccCareer).filter(
            BccCareer.id == career_id,
            BccCareer.tenant_id == current_user["tenant_id"],
        ).first()
        if not item:
            raise HTTPException(status_code=404, detail="Career not found")
        return BccCareerResponse.model_validate(item)

    async def create_career(self, data: BccCareerCreate, current_user: dict):
        item = BccCareer(
            tenant_id=current_user["tenant_id"],
            created_by=current_user["email"],
            **data.model_dump(exclude_none=True),
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        logger.info("bcc_career_created", id=item.id, name=item.name)
        return BccCareerResponse.model_validate(item)

    async def delete_career(self, career_id: str, current_user: dict):
        item = self.db.query(BccCareer).filter(
            BccCareer.id == career_id,
            BccCareer.tenant_id == current_user["tenant_id"],
        ).first()
        if not item:
            raise HTTPException(status_code=404, detail="Career not found")
        self.db.delete(item)
        self.db.commit()

    async def list_skill_templates(self, current_user: dict):
        items = self.db.query(BccSkillTemplate).filter(
            BccSkillTemplate.tenant_id == current_user["tenant_id"],
        ).order_by(BccSkillTemplate.name).all()
        return [BccSkillTemplateResponse.model_validate(i) for i in items]

    async def get_skill_template(self, template_id: str, current_user: dict):
        item = self.db.query(BccSkillTemplate).filter(
            BccSkillTemplate.id == template_id,
            BccSkillTemplate.tenant_id == current_user["tenant_id"],
        ).first()
        if not item:
            raise HTTPException(status_code=404, detail="Skill template not found")
        return BccSkillTemplateResponse.model_validate(item)

    async def create_skill_template(self, data: BccSkillTemplateCreate, current_user: dict):
        item = BccSkillTemplate(
            tenant_id=current_user["tenant_id"],
            created_by=current_user["email"],
            **data.model_dump(exclude_none=True),
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        logger.info("bcc_skill_template_created", id=item.id, name=item.name)
        return BccSkillTemplateResponse.model_validate(item)

    async def delete_skill_template(self, template_id: str, current_user: dict):
        item = self.db.query(BccSkillTemplate).filter(
            BccSkillTemplate.id == template_id,
            BccSkillTemplate.tenant_id == current_user["tenant_id"],
        ).first()
        if not item:
            raise HTTPException(status_code=404, detail="Skill template not found")
        self.db.delete(item)
        self.db.commit()

    async def list_task_templates(self, current_user: dict):
        items = self.db.query(BccTaskTemplate).filter(
            BccTaskTemplate.tenant_id == current_user["tenant_id"],
        ).order_by(BccTaskTemplate.name).all()
        return [BccTaskTemplateResponse.model_validate(i) for i in items]

    async def get_task_template(self, template_id: str, current_user: dict):
        item = self.db.query(BccTaskTemplate).filter(
            BccTaskTemplate.id == template_id,
            BccTaskTemplate.tenant_id == current_user["tenant_id"],
        ).first()
        if not item:
            raise HTTPException(status_code=404, detail="Task template not found")
        return BccTaskTemplateResponse.model_validate(item)

    async def create_task_template(self, data: BccTaskTemplateCreate, current_user: dict):
        item = BccTaskTemplate(
            tenant_id=current_user["tenant_id"],
            created_by=current_user["email"],
            **data.model_dump(exclude_none=True),
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        logger.info("bcc_task_template_created", id=item.id, name=item.name)
        return BccTaskTemplateResponse.model_validate(item)

    async def delete_task_template(self, template_id: str, current_user: dict):
        item = self.db.query(BccTaskTemplate).filter(
            BccTaskTemplate.id == template_id,
            BccTaskTemplate.tenant_id == current_user["tenant_id"],
        ).first()
        if not item:
            raise HTTPException(status_code=404, detail="Task template not found")
        self.db.delete(item)
        self.db.commit()

    async def list_domains(self, current_user: dict):
        items = self.db.query(BccDomain).filter(
            BccDomain.tenant_id == current_user["tenant_id"],
        ).order_by(BccDomain.name).all()
        return [
            BccDomainResponse(
                id=d.id, name=d.name, description=d.description,
                icon=d.icon, intent_count=len(d.intents)
            )
            for d in items
        ]

    async def create_domain(self, data: BccDomainCreate, current_user: dict):
        item = BccDomain(
            tenant_id=current_user["tenant_id"],
            created_by=current_user["email"],
            **data.model_dump(exclude_none=True),
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        logger.info("bcc_domain_created", id=item.id, name=item.name)
        return BccDomainResponse(
            id=item.id, name=item.name, description=item.description,
            icon=item.icon, intent_count=0
        )

    async def delete_domain(self, domain_id: str, current_user: dict):
        item = self.db.query(BccDomain).filter(
            BccDomain.id == domain_id,
            BccDomain.tenant_id == current_user["tenant_id"],
        ).first()
        if not item:
            raise HTTPException(status_code=404, detail="Domain not found")
        self.db.delete(item)
        self.db.commit()

    async def list_intents(self, current_user: dict):
        items = self.db.query(BccIntent).filter(
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
                id=intent.id, name=intent.name, description=intent.description,
                trigger_phrases=intent.trigger_phrases, category=intent.category,
                domain_id=intent.domain_id,
                domain_name=intent.domain.name if intent.domain else None,
                workflow_key=intent.workflow_key, pipeline_key=intent.pipeline_key,
                task_count=len(tasks), tasks=tasks,
            ))
        return result

    async def get_intent(self, intent_id: str, current_user: dict):
        intent = self.db.query(BccIntent).filter(
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
            id=intent.id, name=intent.name, description=intent.description,
            trigger_phrases=intent.trigger_phrases, category=intent.category,
            domain_id=intent.domain_id,
            domain_name=intent.domain.name if intent.domain else None,
            workflow_key=intent.workflow_key, pipeline_key=intent.pipeline_key,
            task_count=len(tasks), tasks=tasks,
        )

    async def create_intent(self, data: BccIntentCreate, current_user: dict):
        intent = BccIntent(
            tenant_id=current_user["tenant_id"],
            created_by=current_user["email"],
            name=data.name, description=data.description,
            trigger_phrases=data.trigger_phrases, category=data.category,
            domain_id=data.domain_id, workflow_key=data.workflow_key,
            pipeline_key=data.pipeline_key,
        )
        self.db.add(intent)
        self.db.flush()
    
        if data.task_template_ids:
            for idx, tpl_id in enumerate(data.task_template_ids):
                link = BccIntentTask(
                    intent_id=intent.id, task_template_id=tpl_id,
                    sort_order=idx, tenant_id=current_user["tenant_id"],
                )
                self.db.add(link)
    
        self.db.commit()
        self.db.refresh(intent)
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
            id=intent.id, name=intent.name, description=intent.description,
            trigger_phrases=intent.trigger_phrases, category=intent.category,
            domain_id=intent.domain_id,
            domain_name=intent.domain.name if intent.domain else None,
            workflow_key=intent.workflow_key, pipeline_key=intent.pipeline_key,
            task_count=len(tasks), tasks=tasks,
        )

    async def delete_intent(self, intent_id: str, current_user: dict):
        intent = self.db.query(BccIntent).filter(
            BccIntent.id == intent_id,
            BccIntent.tenant_id == current_user["tenant_id"],
        ).first()
        if not intent:
            raise HTTPException(status_code=404, detail="Intent not found")
        self.db.delete(intent)
        self.db.commit()

    async def get_cognitive_map(self, current_user: dict):
        """Return the full Domain -> Intent -> Task tree for the cognitive flow view."""
        from sqlalchemy.orm import joinedload
    
        domains = (
            self.db.query(BccDomain)
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

    async def list_regulations(self, org_id: str, current_user: dict):
        profile = self.db.query(BccOrgProfile).filter(
            BccOrgProfile.organization_id == org_id,
            BccOrgProfile.tenant_id == current_user["tenant_id"],
        ).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Organization profile not found")
        return [BccRegulationResponse.model_validate(r) for r in profile.regulations]

    async def create_regulation(self, org_id: str, data: BccRegulationCreate, current_user: dict):
        profile = self.db.query(BccOrgProfile).filter(
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
        self.db.add(reg)
        self.db.commit()
        self.db.refresh(reg)
        logger.info("bcc_regulation_created", id=reg.id, org_id=org_id)
        return BccRegulationResponse.model_validate(reg)

    async def delete_regulation(self, reg_id: str, current_user: dict):
        reg = self.db.query(BccRegulation).filter(
            BccRegulation.id == reg_id,
            BccRegulation.tenant_id == current_user["tenant_id"],
        ).first()
        if not reg:
            raise HTTPException(status_code=404, detail="Regulation not found")
        self.db.delete(reg)
        self.db.commit()

    async def link_org_industry(self, org_id: str, industry_id: str, current_user: dict):
        link = BccOrgIndustry(
            organization_id=org_id, industry_id=industry_id,
            tenant_id=current_user["tenant_id"],
        )
        self.db.add(link)
        self.db.commit()
        return {"status": "linked"}

    async def unlink_org_industry(self, org_id: str, industry_id: str, current_user: dict):
        link = self.db.query(BccOrgIndustry).filter(
            BccOrgIndustry.organization_id == org_id,
            BccOrgIndustry.industry_id == industry_id,
        ).first()
        if link:
            self.db.delete(link)
            self.db.commit()

    async def list_roles(self, current_user: dict):
        roles = self.db.query(BccRole).filter(
            BccRole.tenant_id == current_user["tenant_id"],
        ).order_by(BccRole.name).all()
        return [BccRoleResponse(
            id=r.id, name=r.name, team_id=r.team_id, department=r.department,
            description=r.description, icon=r.icon, color=r.color,
            kpis=r.kpis, context=r.context,
            skill_count=len(r.skills), task_count=len(r.tasks),
            user_count=len(r.user_roles),
        ) for r in roles]

    async def create_role(self, data: BccRoleCreate, current_user: dict):
        role = BccRole(
            tenant_id=current_user["tenant_id"],
            created_by=current_user["email"],
            **data.model_dump(exclude_none=True),
        )
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        logger.info("bcc_role_created", role_id=role.id, name=role.name)
        return BccRoleResponse(
            id=role.id, name=role.name, team_id=role.team_id,
            department=role.department, description=role.description,
            icon=role.icon, color=role.color,
            kpis=role.kpis, context=role.context,
        )

    async def get_role_detail(self, role_id: str, current_user: dict):
        role = self.db.query(BccRole).filter(
            BccRole.id == role_id,
            BccRole.tenant_id == current_user["tenant_id"],
        ).first()
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        return BccRoleDetailResponse(
            id=role.id, name=role.name, team_id=role.team_id,
            department=role.department, description=role.description,
            icon=role.icon, color=role.color,
            kpis=role.kpis, context=role.context,
            skills=[BccSkillResponse.model_validate(s) for s in role.skills],
            tasks=[BccTaskResponse.model_validate(t) for t in role.tasks],
            milestones=[BccMilestoneResponse.model_validate(m) for m in role.milestones],
            user_count=len(role.user_roles),
        )

    async def update_role(self, role_id: str, data: BccRoleUpdate, current_user: dict):
        role = self.db.query(BccRole).filter(
            BccRole.id == role_id,
            BccRole.tenant_id == current_user["tenant_id"],
        ).first()
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        for key, value in data.model_dump(exclude_none=True).items():
            setattr(role, key, value)
        role.updated_by = current_user["email"]
        self.db.commit()
        self.db.refresh(role)
        logger.info("bcc_role_updated", role_id=role.id)
        return BccRoleResponse(
            id=role.id, name=role.name, team_id=role.team_id,
            department=role.department, description=role.description,
            icon=role.icon, color=role.color,
            kpis=role.kpis, context=role.context,
            skill_count=len(role.skills), task_count=len(role.tasks),
            user_count=len(role.user_roles),
        )

    async def delete_role(self, role_id: str, current_user: dict):
        role = self.db.query(BccRole).filter(
            BccRole.id == role_id,
            BccRole.tenant_id == current_user["tenant_id"],
        ).first()
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        logger.info("bcc_role_deleted", role_id=role.id, name=role.name)
        self.db.delete(role)
        self.db.commit()

    async def list_team_roles(self, team_id: str, current_user: dict):
        roles = self.db.query(BccRole).filter(
            BccRole.team_id == team_id,
            BccRole.tenant_id == current_user["tenant_id"],
        ).order_by(BccRole.name).all()
        return [BccRoleResponse(
            id=r.id, name=r.name, team_id=r.team_id,
            department=r.department, description=r.description,
            icon=r.icon, color=r.color,
            skill_count=len(r.skills), task_count=len(r.tasks),
            user_count=len(r.user_roles),
        ) for r in roles]

    async def add_skill(self, role_id: str, data: BccSkillCreate, current_user: dict):
        role = self.db.query(BccRole).filter(BccRole.id == role_id, BccRole.tenant_id == current_user["tenant_id"]).first()
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        skill = BccSkill(role_id=role_id, tenant_id=current_user["tenant_id"], created_by=current_user["email"], **data.model_dump(exclude_none=True))
        self.db.add(skill)
        self.db.commit()
        self.db.refresh(skill)
        return BccSkillResponse.model_validate(skill)

    async def get_skill(self, skill_id: str, current_user: dict):
        skill = self.db.query(BccSkill).filter(BccSkill.id == skill_id, BccSkill.tenant_id == current_user["tenant_id"]).first()
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        return BccSkillResponse.model_validate(skill)

    async def update_skill(self, skill_id: str, data: BccSkillUpdate, current_user: dict):
        skill = self.db.query(BccSkill).filter(BccSkill.id == skill_id, BccSkill.tenant_id == current_user["tenant_id"]).first()
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        for key, value in data.model_dump(exclude_none=True).items():
            setattr(skill, key, value)
        skill.updated_by = current_user["email"]
        self.db.commit()
        self.db.refresh(skill)
        return BccSkillResponse.model_validate(skill)

    async def delete_skill(self, skill_id: str, current_user: dict):
        skill = self.db.query(BccSkill).filter(BccSkill.id == skill_id, BccSkill.tenant_id == current_user["tenant_id"]).first()
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        self.db.delete(skill)
        self.db.commit()

    async def add_task(self, role_id: str, data: BccTaskCreate, current_user: dict):
        role = self.db.query(BccRole).filter(BccRole.id == role_id, BccRole.tenant_id == current_user["tenant_id"]).first()
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        task = BccTask(role_id=role_id, tenant_id=current_user["tenant_id"], created_by=current_user["email"], **data.model_dump(exclude_none=True))
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return BccTaskResponse.model_validate(task)

    async def get_task(self, task_id: str, current_user: dict):
        task = self.db.query(BccTask).filter(BccTask.id == task_id, BccTask.tenant_id == current_user["tenant_id"]).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return BccTaskResponse.model_validate(task)

    async def update_task(self, task_id: str, data: BccTaskUpdate, current_user: dict):
        task = self.db.query(BccTask).filter(BccTask.id == task_id, BccTask.tenant_id == current_user["tenant_id"]).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        for key, value in data.model_dump(exclude_none=True).items():
            setattr(task, key, value)
        task.updated_by = current_user["email"]
        self.db.commit()
        self.db.refresh(task)
        return BccTaskResponse.model_validate(task)

    async def delete_task(self, task_id: str, current_user: dict):
        task = self.db.query(BccTask).filter(BccTask.id == task_id, BccTask.tenant_id == current_user["tenant_id"]).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        self.db.delete(task)
        self.db.commit()

    async def add_task_step(self, task_id: str, data: BccTaskStepCreate, current_user: dict):
        task = self.db.query(BccTask).filter(BccTask.id == task_id, BccTask.tenant_id == current_user["tenant_id"]).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        step = BccTaskStep(task_id=task_id, **data.model_dump())
        self.db.add(step)
        self.db.commit()
        self.db.refresh(step)
        return BccTaskStepResponse.model_validate(step)

    async def add_resource(self, skill_id: str, data: BccResourceCreate, current_user: dict):
        skill = self.db.query(BccSkill).filter(BccSkill.id == skill_id, BccSkill.tenant_id == current_user["tenant_id"]).first()
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        resource = BccResource(skill_id=skill_id, tenant_id=current_user["tenant_id"], created_by=current_user["email"], **data.model_dump(exclude_none=True))
        self.db.add(resource)
        self.db.commit()
        self.db.refresh(resource)
        return BccResourceResponse.model_validate(resource)

    async def add_milestone(self, role_id: str, data: BccMilestoneCreate, current_user: dict):
        role = self.db.query(BccRole).filter(BccRole.id == role_id, BccRole.tenant_id == current_user["tenant_id"]).first()
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        milestone = BccMilestone(role_id=role_id, tenant_id=current_user["tenant_id"], created_by=current_user["email"], **data.model_dump(exclude_none=True))
        self.db.add(milestone)
        self.db.commit()
        self.db.refresh(milestone)
        return BccMilestoneResponse.model_validate(milestone)

    async def create_profile_entry(self, entity_type: str, entity_id: str, data: BccProfileEntryCreate, current_user: dict):
        _validate_entity_type(entity_type)
        if data.perspective not in VALID_PERSPECTIVES:
            raise HTTPException(status_code=400, detail=f"Invalid perspective '{data.perspective}'")
    
        tenant_id = current_user["tenant_id"]
    
        latest = (
            self.db.query(BccProfileEntry)
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
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
    
        logger.info("profile_entry_created",
                    entity_type=entity_type, entity_id=entity_id,
                    section=data.section, perspective=data.perspective,
                    version=new_version)
    
        return BccProfileEntryResponse.model_validate(entry)

    async def get_profile(self, entity_type: str, entity_id: str, current_user: dict):
        _validate_entity_type(entity_type)
    
        entries = (
            self.db.query(BccProfileEntry)
            .filter(
                BccProfileEntry.tenant_id == current_user["tenant_id"],
                BccProfileEntry.entity_type == entity_type,
                BccProfileEntry.entity_id == entity_id,
                BccProfileEntry.is_active == True,  # noqa: E712
            )
            .order_by(BccProfileEntry.section, BccProfileEntry.perspective)
            .all()
        )
    
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
            entity_type=entity_type, entity_id=entity_id, sections=sections,
        )

    async def get_profile_history(self, entity_type: str, entity_id: str, current_user: dict):
        _validate_entity_type(entity_type)
        entries = (
            self.db.query(BccProfileEntry)
            .filter(
                BccProfileEntry.tenant_id == current_user["tenant_id"],
                BccProfileEntry.entity_type == entity_type,
                BccProfileEntry.entity_id == entity_id,
            )
            .order_by(BccProfileEntry.section, BccProfileEntry.version.desc())
            .all()
        )
        return [BccProfileEntryResponse.model_validate(e) for e in entries]

    async def get_profile_section(self, entity_type: str, entity_id: str, section: str, current_user: dict):
        _validate_entity_type(entity_type)
        entries = (
            self.db.query(BccProfileEntry)
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
