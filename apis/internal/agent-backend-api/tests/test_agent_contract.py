from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from jose import jwt

import main
from app.infrastructure.persistence.models.bcc_entities import (
    BccCareer,
    BccDepartment,
    BccDomain,
    BccIndustry,
    BccIntent,
    BccIntentTask,
    BccMilestone,
    BccOrgIndustry,
    BccOrgProfile,
    BccOrganization,
    BccProfileEntry,
    BccRegulation,
    BccResource,
    BccRole,
    BccSkill,
    BccSkillTemplate,
    BccTask,
    BccTaskStep,
    BccTaskTemplate,
    BccTeam,
)
from app.infrastructure.persistence.models.bob_settings import BobUserSettings
from app.infrastructure.persistence.models.capability import CapabilityDefinition, DeptCapability, UserCapability
from app.infrastructure.persistence.models.client_map import ClientMap, GoldenNote, InteractionType
from app.infrastructure.persistence.models.department import UserDepartment
from app.infrastructure.persistence.models.training_models import TrainingMissingElement, TrainingNote, TrainingSession
from app.events import publishers
from app.infrastructure import database
from app.infrastructure.persistence.client_map_repository import ClientMapRepository, compute_meddpicc_score
from app.middleware.auth import get_current_user, settings
from app.presentation import deps as agent_deps
from app.presentation.routes import (
    bcc_routes,
    bob_settings_routes,
    capability_routes,
    client_map_routes,
    training_routes,
)
from app.presentation.schemas import bcc_schemas, client_map_schemas


USER = {"user_id": "user-1", "email": "agent@example.com", "tenant_id": "tenant-1"}
NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def stamp(entity):
    entity.created_at = NOW
    entity.updated_at = NOW
    entity.version = 1
    entity.is_deleted = False
    entity.deleted_at = None
    entity.deleted_by = None
    return entity


def ns(**kwargs):
    return SimpleNamespace(**kwargs)


def make_bob_settings(**overrides):
    data = {
        "id": "bob-settings-1",
        "user_id": "user-1",
        "tenant_id": "tenant-1",
        "tone": "professional",
        "formality": 0.5,
        "response_length": "balanced",
        "language": "fr-CA",
        "creativity": 0.3,
        "emoji_usage": False,
        "voice": "Cherry",
        "speed": 1.0,
        "auto_listen": True,
    }
    data.update(overrides)
    return ns(**data)


def make_client_map(map_id="client-map-1", **overrides):
    client_map = ClientMap(
        id=map_id,
        contact_id="contact-1",
        tenant_id="tenant-1",
        role_type=None,
        real_role="VP Sales",
        pain_point="Manual qualification",
        pain_business_impact="Long cycle",
        metrics_target="20% faster close",
        wiifm_business="More revenue",
        economic_buyer="CFO",
        decision_criteria="Integration",
        decision_process="Committee",
        paper_process="Procurement",
        champion_name="Ada",
        competition="Spreadsheet",
        alternative_if_no="Do nothing",
        trust_level=4,
        meddpicc_score=0,
        created_by="agent@example.com",
    )
    client_map.golden_notes = []
    client_map.insight_triples = []
    client_map.created_at = NOW
    client_map.updated_at = NOW
    client_map.is_deleted = False
    for key, value in overrides.items():
        setattr(client_map, key, value)
    return client_map


def make_golden_note(note_id="note-1", **overrides):
    note = GoldenNote(
        id=note_id,
        client_map_id="client-map-1",
        tenant_id="tenant-1",
        interaction_date=NOW,
        interaction_type=InteractionType.CALL,
        verbatim="This saves the team",
        created_by="agent@example.com",
    )
    note.created_at = NOW
    note.is_deleted = False
    for key, value in overrides.items():
        setattr(note, key, value)
    return note


class FakeQuery:
    def __init__(self, items=None):
        self.items = list(items or [])

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def options(self, *args):
        return self

    def offset(self, skip):
        self.items = self.items[skip:]
        return self

    def limit(self, limit):
        self.items = self.items[:limit]
        return self

    def first(self):
        return self.items[0] if self.items else None

    def all(self):
        return self.items

    def count(self):
        return len(self.items)


class FakeDB:
    def __init__(self):
        self.added = []
        self.deleted = []
        self.commits = 0
        self.flushes = 0
        self.refreshes = 0
        self.bob_settings = make_bob_settings()
        self.storage = self._build_storage()

    def _build_storage(self):
        industry = stamp(BccIndustry(id="industry-1", name="SaaS", tenant_id="tenant-1"))
        career = stamp(BccCareer(id="career-1", name="Account Executive", tenant_id="tenant-1"))
        skill_template = stamp(
            BccSkillTemplate(id="skill-template-1", name="Discovery", type="hard", tenant_id="tenant-1")
        )
        task_template = stamp(
            BccTaskTemplate(
                id="task-template-1",
                name="Qualify",
                frequency="weekly",
                tenant_id="tenant-1",
                context={},
            )
        )
        domain = stamp(BccDomain(id="domain-1", name="Revenue", icon="chart", tenant_id="tenant-1"))
        intent_task = stamp(
            BccIntentTask(
                id="intent-task-1",
                intent_id="intent-1",
                task_template_id="task-template-1",
                sort_order=0,
                tool_name="crm",
                tenant_id="tenant-1",
            )
        )
        intent_task.task_template = task_template
        intent = stamp(
            BccIntent(
                id="intent-1",
                name="Qualify lead",
                trigger_phrases=["qualify"],
                category="sales",
                domain_id="domain-1",
                workflow_key="workflow",
                pipeline_key="pipeline",
                tenant_id="tenant-1",
            )
        )
        intent.domain = domain
        intent.task_links = [intent_task]
        domain.intents = [intent]
        profile = stamp(
            BccOrgProfile(
                id="profile-1",
                organization_id="org-1",
                country="Canada",
                state_province="QC",
                city="Montreal",
                operations_domains=["sales"],
                tenant_id="tenant-1",
            )
        )
        regulation = stamp(
            BccRegulation(
                id="reg-1",
                profile_id="profile-1",
                name="Privacy",
                type="general",
                enforcement_level="mandatory",
                tenant_id="tenant-1",
            )
        )
        profile.regulations = [regulation]
        department = stamp(
            BccDepartment(id="dept-1", organization_id="org-1", name="Sales", tenant_id="tenant-1")
        )
        team = stamp(BccTeam(id="team-1", department_id="dept-1", name="Enterprise", tenant_id="tenant-1"))
        skill = stamp(
            BccSkill(
                id="skill-1",
                role_id="role-1",
                name="Discovery",
                type="hard",
                stage="foundation",
                priority=2,
                tenant_id="tenant-1",
            )
        )
        resource = stamp(
            BccResource(id="resource-1", skill_id="skill-1", title="Guide", type="article", tenant_id="tenant-1")
        )
        skill.resources = [resource]
        task_step = BccTaskStep(id="step-1", task_id="task-1", step_number=1, instruction="Ask why now")
        task = stamp(
            BccTask(
                id="task-1",
                role_id="role-1",
                name="Qualify",
                frequency="daily",
                stage="foundation",
                category="sales",
                tenant_id="tenant-1",
            )
        )
        task.steps = [task_step]
        milestone = stamp(
            BccMilestone(
                id="milestone-1",
                role_id="role-1",
                name="Ready",
                stage="foundation",
                sort_order=0,
                tenant_id="tenant-1",
            )
        )
        role = stamp(
            BccRole(
                id="role-1",
                team_id="team-1",
                name="AE",
                department="Sales",
                kpis={"pipeline": 3},
                context={"segment": "enterprise"},
                tenant_id="tenant-1",
            )
        )
        role.skills = [skill]
        role.tasks = [task]
        role.milestones = [milestone]
        role.user_roles = []
        team.roles = [role]
        department.teams = [team]
        link = stamp(BccOrgIndustry(id="org-industry-1", organization_id="org-1", industry_id="industry-1", tenant_id="tenant-1"))
        link.industry = industry
        org = stamp(
            BccOrganization(
                id="org-1",
                name="Croo",
                description="Digital experience",
                icon="building",
                color="#335577",
                tenant_id="tenant-1",
            )
        )
        org.profile = profile
        org.departments = [department]
        org.industry_links = [link]
        entry = stamp(
            BccProfileEntry(
                id="entry-1",
                tenant_id="tenant-1",
                entity_type="organization",
                entity_id="org-1",
                section="overview",
                content="A useful profile",
                perspective="general",
                version=1,
                is_active=True,
                contributed_by="user-1",
                contributor_name="agent@example.com",
                contribution_method="manual",
            )
        )
        cap_def = CapabilityDefinition(
            id="cap-1",
            code="agent.read",
            name="Read agent data",
            scope="agent",
            module="agent",
            default_enabled=True,
            risk_level="low",
        )
        user_cap = stamp(
            UserCapability(
                id="user-cap-1",
                user_id="user-1",
                capability_id="cap-1",
                granted=True,
                granted_by="admin@example.com",
                tenant_id="tenant-1",
            )
        )
        dept_cap = stamp(
            DeptCapability(
                id="dept-cap-1",
                department_id="dept-1",
                capability_id="cap-1",
                granted=True,
                tenant_id="tenant-1",
            )
        )
        user_dept = UserDepartment(id="user-dept-1", user_id="user-1", department_id="dept-1")
        training_session = TrainingSession(
            id="training-1",
            user_id="user-1",
            tenant_id="tenant-1",
            training_slug="voice-basics",
            current_slide=0,
        )
        training_session.started_at = NOW
        note = TrainingNote(
            id="training-note-1",
            session_id="training-1",
            user_id="user-1",
            content="Useful note",
            note_type="insight",
        )
        note.created_at = NOW
        missing = TrainingMissingElement(
            id="missing-1",
            session_id="training-1",
            user_id="user-1",
            label="CRM connector",
            category="integration",
        )
        missing.created_at = NOW
        client_map = make_client_map()
        golden_note = make_golden_note()
        client_map.golden_notes = [golden_note]
        return {
            BccIndustry: [industry],
            BccCareer: [career],
            BccSkillTemplate: [skill_template],
            BccTaskTemplate: [task_template],
            BccDomain: [domain],
            BccIntent: [intent],
            BccIntentTask: [intent_task],
            BccOrganization: [org],
            BccOrgProfile: [profile],
            BccDepartment: [department],
            BccTeam: [team],
            BccRole: [role],
            BccSkill: [skill],
            BccTask: [task],
            BccTaskStep: [task_step],
            BccResource: [resource],
            BccMilestone: [milestone],
            BccRegulation: [regulation],
            BccOrgIndustry: [link],
            BccProfileEntry: [entry],
            CapabilityDefinition: [cap_def],
            UserCapability: [user_cap],
            DeptCapability: [dept_cap],
            UserDepartment: [user_dept],
            TrainingSession: [training_session],
            TrainingNote: [note],
            TrainingMissingElement: [missing],
            ClientMap: [client_map],
            GoldenNote: [golden_note],
            BobUserSettings: [self.bob_settings],
        }

    def query(self, entity):
        return FakeQuery(self.storage.get(entity, []))

    def add(self, entity):
        self.added.append(entity)
        if not getattr(entity, "id", None):
            entity.id = f"{entity.__class__.__name__.lower()}-{len(self.added)}"
        self._apply_defaults(entity)
        self.storage.setdefault(entity.__class__, []).append(entity)
        if isinstance(entity, BccOrgProfile):
            self.storage[BccOrganization][0].profile = entity
        if isinstance(entity, BccDepartment):
            self.storage[BccOrganization][0].departments.append(entity)
            entity.teams = []
        if isinstance(entity, BccTeam):
            self.storage[BccDepartment][0].teams.append(entity)
            entity.roles = []
        if isinstance(entity, BccIntentTask):
            self.storage[BccIntent][0].task_links.append(entity)
        if isinstance(entity, BccSkill):
            entity.resources = []
            self.storage[BccRole][0].skills.append(entity)
        if isinstance(entity, BccTask):
            entity.steps = []
            self.storage[BccRole][0].tasks.append(entity)
        if isinstance(entity, BccMilestone):
            self.storage[BccRole][0].milestones.append(entity)

    def _apply_defaults(self, entity):
        if isinstance(entity, BccOrganization):
            entity.profile = getattr(entity, "profile", None)
            entity.departments = getattr(entity, "departments", [])
            entity.industry_links = getattr(entity, "industry_links", [])
        if isinstance(entity, BccOrgProfile):
            entity.regulations = getattr(entity, "regulations", [])
        if isinstance(entity, BccDomain):
            entity.intents = getattr(entity, "intents", [])
        if isinstance(entity, BccIntent):
            entity.domain = getattr(entity, "domain", None)
            entity.task_links = getattr(entity, "task_links", [])
        if isinstance(entity, BccRole):
            entity.skills = getattr(entity, "skills", [])
            entity.tasks = getattr(entity, "tasks", [])
            entity.milestones = getattr(entity, "milestones", [])
            entity.user_roles = getattr(entity, "user_roles", [])
            entity.kpis = entity.kpis or {}
            entity.context = entity.context or {}
        if isinstance(entity, TrainingSession):
            entity.current_slide = entity.current_slide or 0
            entity.started_at = getattr(entity, "started_at", None) or NOW
        if isinstance(entity, (TrainingNote, TrainingMissingElement)):
            entity.created_at = getattr(entity, "created_at", None) or NOW
        if isinstance(entity, BccRegulation):
            entity.type = entity.type or "general"
            entity.enforcement_level = entity.enforcement_level or "mandatory"

    def flush(self):
        self.flushes += 1

    def commit(self):
        self.commits += 1

    def refresh(self, entity):
        self.refreshes += 1
        self._apply_defaults(entity)

    def delete(self, entity):
        self.deleted.append(entity)

    def execute(self, *args, **kwargs):
        return ns(first=lambda: (0.82,))

    def close(self):
        return None


class EmptyDB(FakeDB):
    def _build_storage(self):
        return {}

    def execute(self, *args, **kwargs):
        return ns(first=lambda: None)


class FakeClientMapRepository:
    def __init__(self, db):
        self.db = db
        self.client_map = make_client_map()
        self.note = make_golden_note()
        self.client_map.golden_notes = [self.note]

    def contact_exists(self, contact_id, tenant_id):
        return contact_id == "contact-1" and tenant_id == "tenant-1"

    def get_by_contact_id(self, contact_id, tenant_id):
        return self.client_map if contact_id == "contact-1" and tenant_id == "tenant-1" else None

    def upsert(self, contact_id, tenant_id, data, user_email=""):
        for key, value in data.items():
            setattr(self.client_map, key, value)
        self.client_map.contact_id = contact_id
        self.client_map.tenant_id = tenant_id
        self.client_map.created_by = user_email
        return self.client_map

    def add_golden_note(self, client_map_id, tenant_id, data, user_email=""):
        self.note = make_golden_note("note-new", client_map_id=client_map_id, tenant_id=tenant_id, **data)
        self.note.created_by = user_email
        return self.note

    def update_golden_note(self, note_id, tenant_id, data):
        if note_id != "note-1":
            return None
        for key, value in data.items():
            setattr(self.note, key, value)
        return self.note

    def delete_golden_note(self, note_id, tenant_id):
        return note_id == "note-1"

    def get_meddpicc_detail(self, contact_id, tenant_id):
        score, breakdown = compute_meddpicc_score(self.client_map)
        return {"total_score": score, "max_score": 100, "components": breakdown}


@pytest.fixture()
def fake_db():
    return FakeDB()


@pytest.fixture()
def client(monkeypatch, fake_db):
    repository = FakeClientMapRepository(fake_db)
    monkeypatch.setattr(agent_deps, "ClientMapRepository", lambda db: repository)
    main.app.dependency_overrides[bcc_routes.get_current_user] = lambda: USER
    main.app.dependency_overrides[bcc_routes.get_db] = lambda: fake_db
    main.app.dependency_overrides[bob_settings_routes.get_current_user] = lambda: USER
    main.app.dependency_overrides[capability_routes.get_current_user] = lambda: USER
    main.app.dependency_overrides[agent_deps.get_db] = lambda: fake_db
    main.app.dependency_overrides[client_map_routes.get_current_user] = lambda: USER
    main.app.dependency_overrides[training_routes.get_current_user] = lambda: USER
    test_client = TestClient(main.app)
    yield test_client
    test_client.close()
    main.app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers():
    token = jwt.encode(
        {"sub": "user-1", "email": "agent@example.com", "tenant_id": "tenant-1"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


def test_monitoring_endpoints(client):
    for path in ["/health", "/readiness", "/liveness", "/startup", "/metrics"]:
        response = client.get(path)
        assert response.status_code == 200
    assert "dependencies" in client.get("/health").json()
    assert "cde_api_info" in client.get("/metrics").text


def test_auth_dependency_accepts_and_rejects_tokens(auth_headers):
    credentials = type("Credentials", (), {"credentials": auth_headers["Authorization"].split(" ", 1)[1]})()
    assert get_current_user(credentials)["tenant_id"] == "tenant-1"

    invalid = type("Credentials", (), {"credentials": "not-a-token"})()
    with pytest.raises(Exception) as invalid_token:
        get_current_user(invalid)
    assert getattr(invalid_token.value, "status_code", None) == 401

    no_sub = jwt.encode({"email": "agent@example.com"}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    with pytest.raises(Exception) as missing_sub:
        get_current_user(type("Credentials", (), {"credentials": no_sub})())
    assert getattr(missing_sub.value, "status_code", None) == 401


def test_bob_settings_routes(client):
    response = client.get("/api/v1/bob/settings")
    assert response.status_code == 200
    assert response.json()["personality"]["language"] == "fr-CA"

    updated = client.put(
        "/api/v1/bob/settings",
        json={
            "personality": {"tone": "friendly", "language": "fr-FR"},
            "voice": {"voice": "Cherry", "speed": 1.2, "auto_listen": False},
        },
    )
    assert updated.status_code == 200
    assert updated.json()["personality"]["tone"] == "friendly"
    assert client.put("/api/v1/bob/settings", json={"voice": {"voice": "missing"}}).status_code == 400
    assert client.put("/api/v1/bob/settings", json={"personality": {"tone": "robot"}}).status_code == 400
    assert client.delete("/api/v1/bob/settings").status_code == 204


def test_capability_routes(client):
    assert client.get("/api/v1/capabilities/catalog").json()[0]["code"] == "agent.read"
    mine = client.get("/api/v1/capabilities/me")
    assert mine.status_code == 200
    assert mine.json()["capabilities"][0]["source"] == "user"
    assert client.post("/api/v1/capabilities/check", params={"capability_code": "agent.read"}).json()["granted"] is True
    assigned = client.post(
        "/api/v1/capabilities/users/user-2/assign",
        json={"capability_code": "agent.read", "granted": False},
    )
    assert assigned.status_code == 201
    assert assigned.json()["granted"] is False


def test_client_map_routes(client):
    assert client.get("/api/v1/contacts/contact-1/client-map").json()["contact_id"] == "contact-1"
    upserted = client.put("/api/v1/contacts/contact-1/client-map", json={"pain_point": "Manual work"})
    assert upserted.status_code == 200
    assert upserted.json()["pain_point"] == "Manual work"

    note = client.post(
        "/api/v1/contacts/contact-1/client-map/golden-notes",
        json={"interaction_date": NOW.isoformat(), "interaction_type": "CALL", "verbatim": "Need speed"},
    )
    assert note.status_code == 201
    assert client.put(
        "/api/v1/contacts/contact-1/client-map/golden-notes/note-1",
        json={"verbatim": "Need accuracy"},
    ).json()["verbatim"] == "Need accuracy"
    assert client.put("/api/v1/contacts/contact-1/client-map/golden-notes/missing", json={}).status_code == 404
    assert client.delete("/api/v1/contacts/contact-1/client-map/golden-notes/note-1").status_code == 204
    assert client.delete("/api/v1/contacts/contact-1/client-map/golden-notes/missing").status_code == 404
    score = client.get("/api/v1/contacts/contact-1/client-map/meddpicc-score")
    assert score.status_code == 200
    assert score.json()["total_score"] > 0
    analyzed = client.post("/api/v1/contacts/contact-1/client-map/analyze-behavior")
    assert analyzed.status_code == 200
    assert "disc_primary" in analyzed.json()["behavioral_profile"]
    assert client.get("/api/v1/contacts/missing/client-map/analyze-behavior").status_code == 405
    assert client.post("/api/v1/contacts/missing/client-map/analyze-behavior").status_code == 404


def test_training_routes(client):
    created = client.post("/api/v1/training/sessions", json={"training_slug": "voice-basics"})
    assert created.status_code == 201
    assert created.json()["training_slug"] == "voice-basics"
    assert client.patch("/api/v1/training/sessions/training-1/slide", json={"current_slide": 3}).json()["current_slide"] == 3
    assert client.get("/api/v1/training/sessions/training-1/notes").status_code == 200
    assert client.post(
        "/api/v1/training/sessions/training-1/notes",
        json={"slide_id": 1, "content": "Great example", "note_type": "insight"},
    ).status_code == 201
    assert client.delete("/api/v1/training/notes/training-note-1").status_code == 204
    assert client.get("/api/v1/training/sessions/training-1/missing").status_code == 200
    assert client.post(
        "/api/v1/training/sessions/training-1/missing",
        json={"label": "Calendar sync", "category": "integration"},
    ).status_code == 201
    assert client.delete("/api/v1/training/missing/missing-1").status_code == 204


@pytest.mark.asyncio
async def test_bcc_organization_library_and_role_routes(fake_db):
    assert len(await bcc_routes.list_organizations(USER, fake_db)) == 1
    created_org = await bcc_routes.create_organization(bcc_schemas.BccOrganizationCreate(name="New Org"), USER, fake_db)
    assert created_org.name == "New Org"
    assert (await bcc_routes.get_organization_detail("org-1", USER, fake_db)).id == "org-1"
    assert (await bcc_routes.update_organization("org-1", bcc_schemas.BccOrganizationUpdate(name="Croo Updated"), USER, fake_db)).name == "Croo Updated"
    await bcc_routes.delete_organization("org-1", USER, fake_db)
    assert (await bcc_routes.update_org_profile("org-1", bcc_schemas.BccOrgProfileUpdate(city="Quebec"), USER, fake_db)).city == "Quebec"

    assert (await bcc_routes.list_departments("org-1", USER, fake_db))[0].name == "Sales"
    assert (await bcc_routes.create_department("org-1", bcc_schemas.BccDepartmentCreate(name="Success"), USER, fake_db)).name == "Success"
    await bcc_routes.delete_department("dept-1", USER, fake_db)
    assert (await bcc_routes.list_teams("dept-1", USER, fake_db))[0].name == "Enterprise"
    assert (await bcc_routes.create_team("dept-1", bcc_schemas.BccTeamCreate(name="Midmarket"), USER, fake_db)).name == "Midmarket"
    await bcc_routes.delete_team("team-1", USER, fake_db)

    assert (await bcc_routes.list_industries(USER, fake_db))[0].name == "SaaS"
    assert (await bcc_routes.get_industry("industry-1", USER, fake_db)).id == "industry-1"
    assert (await bcc_routes.create_industry(bcc_schemas.BccIndustryCreate(name="Manufacturing"), USER, fake_db)).name == "Manufacturing"
    assert (await bcc_routes.update_industry("industry-1", bcc_schemas.BccIndustryUpdate(description="Updated"), USER, fake_db)).description == "Updated"
    await bcc_routes.delete_industry("industry-1", USER, fake_db)

    assert (await bcc_routes.list_careers(USER, fake_db))[0].name == "Account Executive"
    assert (await bcc_routes.get_career("career-1", USER, fake_db)).id == "career-1"
    assert (await bcc_routes.create_career(bcc_schemas.BccCareerCreate(name="CSM"), USER, fake_db)).name == "CSM"
    await bcc_routes.delete_career("career-1", USER, fake_db)

    assert (await bcc_routes.list_skill_templates(USER, fake_db))[0].name == "Discovery"
    assert (await bcc_routes.get_skill_template("skill-template-1", USER, fake_db)).id == "skill-template-1"
    assert (await bcc_routes.create_skill_template(bcc_schemas.BccSkillTemplateCreate(name="Demo"), USER, fake_db)).name == "Demo"
    await bcc_routes.delete_skill_template("skill-template-1", USER, fake_db)

    assert (await bcc_routes.list_task_templates(USER, fake_db))[0].name == "Qualify"
    assert (await bcc_routes.get_task_template("task-template-1", USER, fake_db)).id == "task-template-1"
    assert (await bcc_routes.create_task_template(bcc_schemas.BccTaskTemplateCreate(name="Follow up"), USER, fake_db)).name == "Follow up"
    await bcc_routes.delete_task_template("task-template-1", USER, fake_db)

    assert (await bcc_routes.list_domains(USER, fake_db))[0].name == "Revenue"
    assert (await bcc_routes.create_domain(bcc_schemas.BccDomainCreate(name="Ops"), USER, fake_db)).name == "Ops"
    await bcc_routes.delete_domain("domain-1", USER, fake_db)

    assert (await bcc_routes.list_intents(USER, fake_db))[0].name == "Qualify lead"
    assert (await bcc_routes.get_intent("intent-1", USER, fake_db)).id == "intent-1"
    created_intent = await bcc_routes.create_intent(
        bcc_schemas.BccIntentCreate(name="Coach rep", task_template_ids=["task-template-1"]),
        USER,
        fake_db,
    )
    assert created_intent.name == "Coach rep"
    await bcc_routes.delete_intent("intent-1", USER, fake_db)
    assert (await bcc_routes.get_cognitive_map(USER, fake_db))[0]["intent_count"] >= 1

    assert (await bcc_routes.list_regulations("org-1", USER, fake_db))[0].name == "Privacy"
    assert (await bcc_routes.create_regulation("org-1", bcc_schemas.BccRegulationCreate(name="SOC2"), USER, fake_db)).name == "SOC2"
    await bcc_routes.delete_regulation("reg-1", USER, fake_db)
    assert (await bcc_routes.link_org_industry("org-1", "industry-1", USER, fake_db))["status"] == "linked"
    await bcc_routes.unlink_org_industry("org-1", "industry-1", USER, fake_db)

    assert (await bcc_routes.list_roles(USER, fake_db))[0].name == "AE"
    assert (await bcc_routes.create_role(bcc_schemas.BccRoleCreate(name="Manager"), USER, fake_db)).name == "Manager"
    assert (await bcc_routes.get_role_detail("role-1", USER, fake_db)).id == "role-1"
    assert (await bcc_routes.update_role("role-1", bcc_schemas.BccRoleUpdate(description="Updated"), USER, fake_db)).description == "Updated"
    await bcc_routes.delete_role("role-1", USER, fake_db)
    assert (await bcc_routes.list_team_roles("team-1", USER, fake_db))[0].name == "AE"

    assert (await bcc_routes.add_skill("role-1", bcc_schemas.BccSkillCreate(name="Negotiation"), USER, fake_db)).name == "Negotiation"
    assert (await bcc_routes.get_skill("skill-1", USER, fake_db)).id == "skill-1"
    assert (await bcc_routes.update_skill("skill-1", bcc_schemas.BccSkillUpdate(priority=1), USER, fake_db)).priority == 1
    await bcc_routes.delete_skill("skill-1", USER, fake_db)
    assert (await bcc_routes.add_task("role-1", bcc_schemas.BccTaskCreate(name="Forecast"), USER, fake_db)).name == "Forecast"
    assert (await bcc_routes.get_task("task-1", USER, fake_db)).id == "task-1"
    assert (await bcc_routes.update_task("task-1", bcc_schemas.BccTaskUpdate(category="pipeline"), USER, fake_db)).category == "pipeline"
    await bcc_routes.delete_task("task-1", USER, fake_db)
    assert (await bcc_routes.add_task_step("task-1", bcc_schemas.BccTaskStepCreate(step_number=2, instruction="Confirm value"), USER, fake_db)).step_number == 2
    assert (await bcc_routes.add_resource("skill-1", bcc_schemas.BccResourceCreate(title="Playbook"), USER, fake_db)).title == "Playbook"
    assert (await bcc_routes.add_milestone("role-1", bcc_schemas.BccMilestoneCreate(name="Certified", stage="foundation"), USER, fake_db)).name == "Certified"


@pytest.mark.asyncio
async def test_bcc_profile_entries_and_error_paths(fake_db):
    entry = await bcc_routes.create_profile_entry(
        "organization",
        "org-1",
        bcc_schemas.BccProfileEntryCreate(section="overview", content="Updated", perspective="general"),
        USER,
        fake_db,
    )
    assert entry.version >= 1
    profile = await bcc_routes.get_profile("organization", "org-1", USER, fake_db)
    assert profile.sections[0].section == "overview"
    assert (await bcc_routes.get_profile_history("organization", "org-1", USER, fake_db))[0].id == "entry-1"
    assert (await bcc_routes.get_profile_section("organization", "org-1", "overview", USER, fake_db)).section == "overview"

    with pytest.raises(HTTPException) as invalid_type:
        bcc_routes._validate_entity_type("unknown")
    assert invalid_type.value.status_code == 400
    with pytest.raises(HTTPException) as invalid_perspective:
        await bcc_routes.create_profile_entry(
            "organization",
            "org-1",
            bcc_schemas.BccProfileEntryCreate(section="overview", perspective="wrong"),
            USER,
            fake_db,
        )
    assert invalid_perspective.value.status_code == 400


@pytest.mark.asyncio
async def test_publishers_emit_agent_domain_events(monkeypatch):
    published = []

    async def fake_publish(event):
        published.append(event)

    monkeypatch.setattr(publishers.event_bus, "publish", fake_publish)
    await publishers.publish_agent_event("updated", "entity-1", {"status": "ok"})
    assert published == [{"type": "agent.updated", "entity_id": "entity-1", "data": {"status": "ok"}}]


def test_database_facade_and_schema_contracts(monkeypatch):
    monkeypatch.setattr(database, "create_db_engine", lambda api_name: f"engine:{api_name}")
    monkeypatch.setattr(database, "create_session_factory", lambda api_name: f"factory:{api_name}")
    database.init("agent-backend")
    assert database.get_engine() == "engine:agent-backend"
    assert database.get_session_factory() == "factory:agent-backend"

    client_map = make_client_map()
    response = client_map_schemas.ClientMapResponse.model_validate(client_map)
    assert response.id == "client-map-1"
    note = client_map_schemas.GoldenNoteResponse.model_validate(make_golden_note())
    assert note.id == "note-1"
    assert client_map_schemas.ClientMapUpsert(trust_level=3).trust_level == 3
    assert client_map_schemas.GoldenNoteCreate(interaction_date=NOW, interaction_type="CALL").interaction_type == "CALL"
    assert client_map_schemas.MeddpiccScoreDetail(total_score=75, components={}).max_score == 100


def test_client_map_repository_methods_cover_persistence_paths():
    class RepositorySession(FakeDB):
        def __init__(self):
            super().__init__()
            self.existing = make_client_map()
            self.note = make_golden_note()
            self.storage[ClientMap] = [self.existing]
            self.storage[GoldenNote] = [self.note]

    session = RepositorySession()
    repository = ClientMapRepository(session)
    assert repository.get_by_contact_id("contact-1", "tenant-1").id == "client-map-1"
    assert repository.upsert("contact-1", "tenant-1", {"pain_point": "New pain"}, "agent@example.com").pain_point == "New pain"
    assert repository.add_golden_note(
        "client-map-1",
        "tenant-1",
        {"interaction_date": NOW, "interaction_type": InteractionType.CALL},
        "agent@example.com",
    ).client_map_id == "client-map-1"
    assert repository.update_golden_note("note-1", "tenant-1", {"verbatim": "Updated"}).verbatim == "Updated"
    assert repository.delete_golden_note("note-1", "tenant-1") is True
    detail = repository.get_meddpicc_detail("contact-1", "tenant-1")
    assert detail["total_score"] > 0
    assert compute_meddpicc_score(make_client_map())[0] > 0


def test_python_package_contract_loads_runtime_components():
    from agent_backend_api import contract

    assert contract.OPERATIONAL_ENDPOINTS == (
        "/health",
        "/readiness",
        "/liveness",
        "/startup",
        "/metrics",
    )
    assert contract.load_app() is main.app
    assert contract.load_runtime_routes() == (
        bcc_routes,
        bob_settings_routes,
        capability_routes,
        client_map_routes,
        training_routes,
    )
    assert contract.load_runtime_repository_classes() == (ClientMapRepository,)
    assert contract.load_runtime_entity_classes() == (
        BccOrganization,
        BccDepartment,
        BccTeam,
        BccRole,
        BobUserSettings,
        CapabilityDefinition,
        UserCapability,
        ClientMap,
        GoldenNote,
        TrainingSession,
        TrainingNote,
        TrainingMissingElement,
    )
