# Spec produit — Domaine Inbox / Communication

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Couche** : 02 · Produit · **Dernière MAJ** : 2026-07-01
> Parent : [PRD §4.2](../prd-cahier-des-charges.md#42-inbox--communication--spec-détaillée) · Réf. : [`PIPEDREAM_ARCHITECTURE.md`](../../PIPEDREAM_ARCHITECTURE.md)

## 1. Objet

Amener l'email **dans** le CRM, contextualisé et exploitable par Bob. Couvre [JTBD-2](../../01-discovery/jobs-to-be-done.md) (inbox contextualisée).

## 2. Architecture dual-provider

CDE synchronise l'email via **deux sources**, avec abstraction unifiée côté frontend (`UnifiedEmail`) :

| Provider | Rôle | Mécanisme | Table |
|---|---|---|---|
| **Pipedream** (moderne) | primaire | webhooks signés HMAC-SHA256 + actions (send/reply/forward/sync) | `membrane_synced_emails` |
| **Microsoft 365** (legacy) | fallback | OAuth direct, delta sync, webhooks subscription | `synced_emails` |

Le frontend distingue les deux via `isMembraneEmail()` (présence de `provider_message_id` sans `ms_message_id`) et masque la complexité.

## 3. Modèle de données email

Champs clés (communs) : `subject`, `body_preview`, `body_html`, `from_address/name`, `to_addresses[]`, `cc_addresses[]`, `received_at`, `is_read`, `importance`, `has_attachments`, `attachments_meta[]`, `folder`, `conversation_id`, **liaison CRM** (`linked_contact_id`, `linked_organization_id`), **IA** (`smart_label`, `ai_summary`, `ai_action_items[]` — présents côté MS365, à généraliser).

## 4. Smart labels

- **Modèle** : `name`, `color`, `description`, `keywords[]` (matching simple), `prompt_hint` (hint pour classification LLM), **hiérarchie** via `parent_id` (label / sous-labels).
- **Usage** : classement automatique de la boîte selon les catégories métier du tenant ; filtrage dans l'inbox.
- **CRUD** : `/api/v1/smart-labels` (backend) exposé via `/inbox/labels` (B4F).

## 5. Webhooks entrants

- **Pipedream → email-backend** (`/api/v1/provider/pipedream/webhook`) : signature `x-pipedream-signature` (HMAC-SHA256, secret `pipedream_webhook_secret`), payload `{event_type, type, external_user_id, app}` → validation → 200 (traitement async).
- **Communication B4F → workflows** (`/webhooks/trigger` JWT, `/webhooks/trigger/public` API key) : déclenche des workflows sur événements `contact.*`, `organization.*`, `opportunity.*`, `quote.*`, `activity.*`. Réponse : `{status, event, executions_triggered, execution_ids[], received_at}`.

## 6. Parcours utilisateur

1. **Connexion** : l'admin connecte MS365 / Pipedream (Settings › Integrations / MS365).
2. **Réception** : un email arrive → webhook → stocké → rattaché au contact/org → labellisé.
3. **Traitement** : l'utilisateur filtre (dossier/label/non-lu/important), lit (reading pane), répond/transfère/compose.
4. **Vue d'ensemble** : `/integrations/overview` agrège connexions actives + stats labels par provider.

## 7. Surfaces UI

`inbox-overview` (orchestrateur), `inbox-sidebar` (filtres), `email-list` (pagination), `email-reading-pane` (détail + actions), `email-compose`. Store NGRX `inbox` (+ `communication` pour l'overview).

## 8. Exigences & priorités
Voir [PRD §4.2](../prd-cahier-des-charges.md#42-inbox--communication--spec-détaillée). Must : EF-INB-1,2,4,5,6. À consolider : liaison auto (3, 🟡), résumé/action-items IA (8).

## 9. Gaps & décisions ouvertes
- **Nommage `membrane_*`** : tables temporaires, rename à planifier (Q3 du PRD).
- **Résumé IA généralisé** : porter `ai_summary`/`ai_action_items` sur le provider Pipedream.
- **Liaison auto contact/org** : fiabiliser le matching (email → contact).

## 10. Métriques
Taux d'emails rattachés automatiquement, précision des smart labels (corrections manuelles), délai de sync (webhook → visible), volume traité / utilisateur.
