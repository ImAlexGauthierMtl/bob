# Data Model — CDE

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Couche** : 04 · Technique · **Dernière MAJ** : 2026-07-01
> Modèle de données logique, reconstruit depuis les modèles SQLAlchemy réels. **Un schéma PostgreSQL par backend**. Toutes les entités métier portent `TenantMixin` + `AuditMixin` (+ `SoftDeleteMixin` pour la plupart).

## 1. Conventions transverses

- **Multi-tenant** : `tenant_id: String(36)` (index, défaut `"default"`) sur chaque entité. Filtré à chaque requête.
- **Audit** : `created_at`, `updated_at`, `created_by`. **Soft-delete** : `deleted_at`, `deleted_by` (pas de DELETE physique).
- **Clés** : `id: String(36)` (UUID) partout.
- **Events** : chaque mutation publie `{service}.{entity}.{created|updated|deleted}` sur Redis.
- **Isolation physique** : `CREATE SCHEMA <service>` par backend ; table de version Alembic dans `public` préfixée (`<service>_alembic_version`).

## 2. Domaine Identité & Tenant (`user`, `org`)

```
Tenant (facturation/contrat)                 User
 ├ id, name, slug (unique)                    ├ id, email, password_hash
 ├ status: TRIAL|ACTIVE|SUSPENDED|CANCELLED   ├ tenant_id (immuable)
 ├ plan: STARTER|PRO|ENTERPRISE               ├ active_organization_id (contexte CRM)
 ├ owner_email, owner_name, max_users         ├ is_super_admin
 ├ subscription_start / _end                  └ (roles via UserRole)
 └ settings (JSON: flags, limits, compliance)

RBAC :  Permission (globale, resource:action)  ──<  RolePermission  >──  Role (tenant-scoped, is_system)
        Role  ──<  UserRole  >──  User
```
- **Tenant ≠ Organization** : `Tenant` = ligne d'abonnement SaaS ; `Organization` = société cliente dans le CRM. Un user → 1 tenant, N organisations accessibles (contexte actif sélectionnable).

## 3. Domaine CRM (`contact`, `org`, `opportunity`, `activity`, `product`)

```
Organization ─1:N─► Contact ─N:1─► Organization
     │                  ▲
     │ 1:N              │ N:1
     ▼                  │
Opportunity ─N:1─► Contact (primary)
     │ 1:N (cascade)
     ▼
OpportunityProduct ──(product_id)──► Product
     │
Opportunity ─1:N─► Quote ─N:1─► Organization

Activity ─N:N─► {Contact, Organization, Opportunity}   (via JSON arrays)
```

| Entité | Champs signature | Enums |
|---|---|---|
| **Contact** | first/last_name, email, phone, job_title, `contact_profile` (JSON enrichi), organization_id, owner_id | status: ACTIVE/INACTIVE/LEAD |
| **Organization** | name, industry, website, adresse, `organization_profile`, linkedin_*, ai_enriched | status: ACTIVE/INACTIVE/PROSPECT/CUSTOMER/CHURNED · type: CORPORATION/SMB/STARTUP/GOVERNMENT/NONPROFIT/OTHER |
| **Department** | name, manager_user_id (+ UserDepartment: user_id, is_manager) | — |
| **Opportunity** | name, amount, probability, close_date, source, organization_id, contact_id, owner_id | stage: PROSPECTING→QUALIFICATION→PROPOSAL→NEGOTIATION→CLOSED_WON/LOST · priority: LOW/MEDIUM/HIGH/CRITICAL |
| **OpportunityProduct** | opportunity_id (FK, cascade), product_id, quantity, unit_price, discount_percent | — |
| **Quote** | subtotal, discount_percent, tax_percent, total, valid_until, terms, opportunity_id, organization_id | status: DRAFT/SENT/ACCEPTED/REJECTED/EXPIRED |
| **Activity** | subject, due_date, completed_at, assigned_to, `contact_ids`/`organization_ids`/`opportunity_ids` (JSON) | type: CALL/EMAIL/MEETING/TASK/NOTE · status: PENDING/IN_PROGRESS/COMPLETED/CANCELLED · priority: LOW/MEDIUM/HIGH/URGENT |
| **Product** | name, category, unit_price, currency(CAD), sku, billing_cycle, license_type, max_users, parent_product_id (add-ons)… | category: SOFTWARE/SERVICE/ADD_ON/CONSULTING/HARDWARE · billing_cycle · license_type: PERPETUAL/SUBSCRIPTION/USAGE_BASED |

**Pipeline ouvert** (dashboard) = {PROSPECTING, QUALIFICATION, PROPOSAL, NEGOTIATION}.
**Calcul devis** : `subtotal = Σ(qty × unit_price × (1−discount))` → remise → taxe → `total`.

## 4. Domaine Communication (`email`)

```
synced_emails (MS365)            membrane_synced_emails (Pipedream)
 ├ ms_message_id (unique)          ├ provider_message_id (unique)
 ├ ms365_connection_id             ├ membrane_connection_id, provider
 ├ subject, body_html, from/to     ├ (mêmes champs de base)
 ├ smart_label, ai_summary,        └ (ai_summary/action_items à porter)
 │  ai_action_items
 └ linked_contact_id, linked_organization_id

smart_labels : name, color, keywords[], prompt_hint, parent_id (hiérarchie)
```
> ⚠️ Les tables `membrane_*` sont temporaires (rename à planifier). Le frontend unifie via `UnifiedEmail` (`isMembraneEmail()`).

## 5. Domaine Knowledge Base (`kb`)

```
kb_categories ─1:N─► kb_articles
 ├ name, slug, icon,      ├ title, slug (unique), excerpt, content
 │ color, sort_order,     ├ category_id, tags[], visibility (internal/shared/public)
 │ article_count          ├ required_module, required_role
 └                        ├ author_*, read_time_minutes
                          ├ view_count, helpful_yes, helpful_no
                          └ is_published, is_featured, deleted_at
```

## 6. Domaine Agentique (`conversation`, `agent-runtime`, `agent-memory`, `agent`)

```
Conversation (session) ─1:N─► Message
AgentRun ─1:N─► AgentConfirmation
RuntimeCatalogItem (collection: agents|skills|tools|tool_policies|user_tool_preferences)
MemoryEntry ──(vector_id)──► Milvus chunks (bob_private / organization / support_procedure / zoho_ticket)
KnowledgeDatabase ─► KnowledgeCollection ─► KnowledgeSource / KnowledgeProcedure / KnowledgeChunk
```

| Entité | Champs signature | Notes |
|---|---|---|
| **AgentRun** | id (`run_*`), tenant/user/session_id, input_message_id, status, mode, trace_id, assistant_content, idempotency_key, **metadata** (provider, model, tool_calls, tool_loop, routing, pending/confirmed), **narration_steps**, actions, artifacts | cœur du runtime |
| **AgentConfirmation** | id (`confirm_*`), run_id, status (pending/confirmed/cancelled), label (ex. `bob_mcp_gateway/slack/draft-send/write`) | gate de sûreté |
| **MemoryEntry** | id (`mem_*`), scope_type (PRIVATE_USER/ORGANIZATION/SHARED_CLEAN), memory_type, title, content, source_type, **sensitivity** (internal/private_user/public), status, expires_at | RAG |
| **RuntimeCatalogItem** | collection, name, payload (JSON), payload_hash | catalogue extensible |
| **Vecteurs** | vector_id, embedding_model (`qwen3-embedding-8b`), dimension 4096 | Milvus optionnel |

## 7. Domaine Platform (`workflow`, `usage`)

| Entité | Champs signature | Enums |
|---|---|---|
| **Workflow** | name, level, owner_type, trigger_config (JSON), required_capabilities, overrides_workflow_id, module, is_active, is_template | level: system/company/department/user · trigger: manual/event-driven/scheduled · mode: suggest/auto/require_approval |
| **WorkflowStep** | workflow_id, step_order, step_type, agent_node, config, on_success/on_failure, is_entry_point | DAG |
| **WorkflowExecution** | workflow_id, triggered_by, status, input/output_data, steps_completed/total, duration_ms, error | status: running/completed/failed/paused |
| **WorkflowStepExecution** | execution_id, step_id, status, IO, agent_mode_used, confidence_score, duration_ms | — |
| **UsageTransaction** (append-only) | timestamp, user_id/email, service_type, provider, model, input/output_tokens, audio_seconds, characters, voip_minutes, is_billable, billing_category, cogs_amount/currency, trigger_source/id, **correlation_id/label**, metadata, duration_ms | service: LLM/STT/TTS/VOIP/SEARCH/ENRICHMENT/WORKFLOW/TOOL/RETRIEVAL |
| **CostRateCard** | provider, model, service_type, unit_type, rate_per_unit, effective_from/to | prix historisé |

## 8. Choix de modélisation & compromis

| Décision | Raison | Compromis |
|---|---|---|
| **1 schéma / backend** | isolation, migrations indépendantes | jointures cross-domaine impossibles en SQL → composition en B4F |
| **Relations N:N en JSON** (activités) | simplicité, pas de table de jonction | non requêtable/indexable relationnellement ; cohérence applicative |
| **Pas de FK OpportunityProduct→Product** | découplage inter-domaines | intégrité gérée par l'application |
| **Ledger append-only** (usage) | auditabilité, facturation fiable | volume croissant → stratégie d'archivage à prévoir |
| **`tenant_id` défaut `"default"`** | bootstrap/admin | veiller à ne jamais laisser `"default"` en prod pour un vrai tenant |
| **Soft-delete généralisé** | récupération, audit | filtrer `deleted_at IS NULL` partout ; purge RGPD à outiller ([DPIA](../06-gouvernance/privacy-dpia.md)) |

## 9. Chantiers data
- Rename `membrane_*` → nommage définitif (migration + backfill).
- Politique de rétention/purge (RGPD) sur emails, mémoire (`expires_at`), ledger.
- Éventuelle normalisation des relations N:N d'activités si le besoin de requêtage apparaît.
