# Spec produit — Platform (Workflows · Analytics · Usage)

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Couche** : 02 · Produit · **Dernière MAJ** : 2026-07-01
> Parent : [PRD §4.5](../prd-cahier-des-charges.md#45-platform-workflows--analytics--usage--spec-détaillée)

## 1. Objet

La couche « plateforme » outille les managers et opérateurs : automatiser des process ([JTBD-5](../../01-discovery/jobs-to-be-done.md)), piloter la performance et les coûts ([JTBD-7](../../01-discovery/jobs-to-be-done.md)). Exposée par `platform-b4f-api`.

## 2. Workflows / automatisations

- **Modèle** (`workflow-backend-api`) : `Workflow` (name, `level` ∈ {system, company, department, user}, `owner_type`, `trigger_type` ∈ {manual, event-driven, scheduled}, `trigger_config` JSON, `execution_mode` ∈ {suggest, auto, require_approval}, `required_capabilities`, hiérarchie via `overrides_workflow_id`, `module`, `is_active`, `is_template`).
- **Steps** (`WorkflowStep`) : DAG — `step_order`, `step_type`, `agent_node`, `config`, routage conditionnel (`on_success`, `on_failure`), `is_entry_point`.
- **Exécution** (`WorkflowExecution` + `WorkflowStepExecution`) : statut (running/completed/failed/paused), IO JSON, `duration_ms`, `steps_completed/total`, `agent_mode_used`, `confidence_score`, `error`.
- **Déclenchement** : manuel (`POST /workflows/{id}/run`), événementiel (via webhooks communication B4F sur `contact.*`, `opportunity.*`…), planifié (🟡 à consolider).
- **Modes** : *suggest* (Bob propose), *auto* (exécute), *require_approval* (attend validation) — cohérent avec le tenet 1.

## 3. Usage & facturation

- **Ledger** (`UsageTransaction`, append-only, immuable) : `timestamp`, `user_id/email`, `tenant_id`, `service_type` ∈ {LLM, STT, TTS, VOIP, SEARCH, ENRICHMENT, WORKFLOW, TOOL, RETRIEVAL}, `provider`, `model`, unités (`input/output_tokens`, `audio_seconds`, `characters`, `voip_minutes`), `is_billable`, `billing_category`, `cogs_amount/currency`, traçabilité (`trigger_source`, `trigger_id`, `correlation_id`, `correlation_label`, `metadata`, `duration_ms`).
- **Cost rate cards** (`CostRateCard`) : `provider`, `model`, `service_type`, `unit_type`, `rate_per_unit`, `effective_from/to` → prix historisé pour recalcul de COGS.
- **APIs** : self-service tenant (`/usage`, `/usage/summary` avec filtres) et admin cross-tenant (`/admin/usage`, `/admin/usage/summary`, `/admin/usage/by-intent`).

## 4. Analytics

Dashboard combinant métriques CRM (via crm-b4f) et plateforme : compteurs (orgs, contacts, opportunités ouvertes, activités en attente), répartition d'usage par service/catégorie/date, COGS par période, synthèse par intent (`correlation_label`).

## 5. Settings & configuration (transverse)

Sections observées : Profile, My Tools, Bob, Integrations, MS365, Team, Roles, Platform Access (entitlements), Tool Governance, Knowledge, Automation (builder), Bob Capabilities, BCC, Products. Réglages Bob stockés via `platform-b4f` (conversation/voice) ; config tenant dans `Tenant.settings` (JSON : feature flags, rate limits, compliance).

## 6. Exigences & priorités
Voir [PRD §4.5](../prd-cahier-des-charges.md#45-platform-workflows--analytics--usage--spec-détaillée). Must : EF-PLT-1,3,4,5,6. À consolider : déclenchement planifié (2, 🟡), analytics (8, 🟡).

## 7. Gaps & décisions
- **Moteur de workflow** : le modèle (DAG, steps, exécutions) est riche ; l'orchestrateur d'exécution événementiel est à finaliser (lien webhooks → run → steps).
- **Entitlements / plans** : relier `Tenant.plan` (STARTER/PRO/ENTERPRISE) aux feature flags et rate limits effectifs.

## 8. Métriques
Nb de workflows actifs, taux de succès d'exécution, économie de temps estimée, COGS total et par action, marge (revenu vs COGS) — entrée directe pour le pilotage business (persona Alex, super-admin).
