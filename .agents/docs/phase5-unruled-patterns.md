# Phase 5 — Patterns UNRULED pour revue architectes

> **Date** : 2026-03-06
> **Phase** : Phase 5 — Backend Foundation (FastAPI + PostgreSQL + Auth + CRUD)
> **Auteur** : Antigravity AI
> **Pour** : Architectes senior — revue et création de templates

---

## Contexte

27 fichiers backend créés pour le scaffolding FastAPI. **8 templates HDQ existants** ont été utilisés. Ce document liste les **8 patterns UNRULED** — des patterns de code qui n'avaient PAS de template d'exécution et qui ont été implémentés ad-hoc.

Chaque pattern ci-dessous devrait devenir un template dans `.agents/templates/code/`.

---

## Patterns UNRULED rencontrés

### 1. TenantMixin — Multi-tenant par `tenant_id`

**Fichier** : `backend/app/domain/entities/base.py`

```python
class TenantMixin:
    tenant_id = Column(String(36), nullable=False, index=True, default="default")
```

- **Besoin** : Chaque entity doit être isolée par tenant (ADR-007)
- **Décision ad-hoc** : Mixin hérité par tous les models
- **Questions pour les architectes** :
  - Le `tenant_id` devrait-il être UUID ou string libre ?
  - Faut-il un `__table_args__` avec index composite `(tenant_id, id)` ?
  - Comment gérer le tenant_id dans les migrations Alembic ?

---

### 2. AuditMixin — Champs d'audit réutilisables

**Fichier** : `backend/app/domain/entities/base.py`

```python
class AuditMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(100), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, default=1)
```

- **Besoin** : Le template `auth-jwt` avait ces champs en dur dans User — pas réutilisable
- **Décision ad-hoc** : Extraction en mixin
- **Questions pour les architectes** :
  - Garder `version` pour optimistic locking, ou supprimer ?
  - `created_by` / `updated_by` : string (email) ou FK vers users ?

---

### 3. SoftDeleteMixin — Suppression douce

**Fichier** : `backend/app/domain/entities/base.py`

- **Besoin** : Même problème que AuditMixin — inline dans auth-jwt
- **Questions pour les architectes** :
  - Middleware SQLAlchemy pour filtrer automatiquement `is_deleted == False` ? (vs query-level)

---

### 4. Tenant-scoped queries dans les repositories

**Fichier** : `backend/app/infrastructure/persistence/organization_repository.py`

```python
def get_by_id(self, org_id: str, tenant_id: str) -> Optional[Organization]:
    return self.db.query(Organization).filter(
        Organization.id == org_id,
        Organization.tenant_id == tenant_id,
        Organization.is_deleted == False,
    ).first()
```

- **Besoin** : Chaque query CRUD doit filtrer par `tenant_id`
- **Décision ad-hoc** : `tenant_id` passé explicitement à chaque méthode
- **Questions pour les architectes** :
  - Un `BaseRepository` avec tenant_id intégré automatiquement ?
  - Un middleware SQLAlchemy qui injecte `tenant_id` dans toutes les queries ?

---

### 5. `get_current_user` avec injection de `tenant_id`

**Fichier** : `backend/app/presentation/routes/auth_routes.py`

```python
def get_current_user(...) -> dict:
    # ... verify JWT
    user = UserRepository(db).get_by_id(user_id)
    return {
        "user_id": user_id,
        "email": payload.get("email"),
        "tenant_id": user.tenant_id,  # ← tenant from DB
    }
```

- **Besoin** : Le tenant_id doit être propagé à tous les endpoints
- **Décision ad-hoc** : Lecture du user pour obtenir le tenant_id
- **Questions pour les architectes** :
  - Mettre le `tenant_id` directement dans le JWT (plus rapide, pas de query) ?
  - Un `CurrentUser` Pydantic model au lieu d'un dict ?

---

### 6. docker-compose pour PostgreSQL local

**Besoin** : Non créé dans cette phase — PostgreSQL non disponible localement
- **Questions pour les architectes** :
  - docker-compose avec PG + Redis pour le dev local ?
  - Inclure pgAdmin dans le compose ?

---

### 7. Frontend ↔ Backend auth wiring

**Besoin** : Non implémenté dans cette phase
- Angular `AuthService` + `HttpInterceptor` JWT
- Token storage (localStorage vs httpOnly cookie)
- Auth guard sur les routes protégées
- **Questions pour les architectes** :
  - httpOnly cookie (plus sécurisé) ou localStorage (plus simple) ?
  - Refresh token silencieux ?

---

### 8. pgvector / Apache AGE setup

**Besoin** : Non implémenté dans cette phase (Phase 6+)
- Extensions PostgreSQL à activer
- Vector column type pour embeddings
- Graph schema AGE
- **Questions pour les architectes** :
  - Dockerfile PostgreSQL custom avec extensions pré-installées ?
  - Migrations Alembic pour les extensions ?

---

## Templates HDQ utilisés (RULED ✅)

| Template | Fichiers produits |
|---|---|
| `api-bootstrap` | `main.py`, structure `app/` |
| `auth-jwt` | User entity, auth schemas, auth routes, seed |
| `database-config` | `database.py` |
| `model-sqlalchemy` | Organization entity |
| `schemas-pydantic` | Organization schemas |
| `router-crud` | Organization routes |
| `repository-pattern` | Organization repository |
| `config-settings` | `config.py` |

## Recommandation

Les patterns **1-5** (mixins + tenant-scoped) sont les plus critiques à templater — ils seront utilisés sur **chaque nouveau module** (Contacts, Opportunities, Quotes, Activities).
