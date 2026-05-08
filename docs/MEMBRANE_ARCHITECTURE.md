# Membrane Integration — Architecture (validée 2026-05-08)

Ce document décrit comment CDE (Croo Digital Experience) s'intègre à
[getmembrane.com](https://getmembrane.com) comme plateforme
d'intégration tierce, et comment les modèles de données des deux systèmes
se mappent l'un sur l'autre.

## 1. Modèles de données — côte à côte

### 1.1 CDE
- **Tenant** = un client CDE (= une entreprise qui utilise Croo).
  Ligne dans `user-backend-api.tenants`.
- **User** = un employé du Tenant (`users.tenant_id` non-null, indexé).
- **Organization** = *un compte CRM* (un client/prospect que le Tenant
  vend à). **N'est PAS un sub-tenant.**
- **Role / Permission** = RBAC tenant-scopé (pas dans le JWT, refetché
  à chaque requête).
- **Isolation :** application-level via `tenant_id` (pas de RLS
  Postgres). JWT CDE contient :
  `{sub: user_id, email, tenant_id, active_organization_id, type, exp}`.

### 1.2 Membrane
- **Organization (Hub)** = ton compte Membrane (Croo Inc.).
- **Workspace** = un environnement d'intégration runtime
  (config OAuth apps, connectors, actions, flows).
- **Tenant (= "Customer" dans la doc)** = unité d'isolation à
  l'intérieur d'un workspace. Identifié par `tenantKey` (chaîne libre
  fournie par Croo).
- **Connection** = OAuth/API credentials pour un external app, scopée
  à **exactement un** tenant Membrane.
- **Isolation :** forte, enforced DB-level entre tenants Membrane.

### 1.3 Mapping — architecture retenue (Option A : **Single Workspace**)

```
┌────────────────────────────────────────────────────────────────────┐
│ Membrane Workspace "croo-prod" (1 seul, partagé)                   │
│ ├── OAuth apps configurées une fois par Croo (HubSpot, Gmail, …)   │
│ ├── Intégrations / Connectors / Actions / Flows       [shared]     │
│ └── Tenants (un par combinaison tenant-CDE × scope)                │
│      ├── "t:acme"                       (per-tenant scope)         │
│      ├── "t:acme:u:alex-user-id"        (per-user scope)           │
│      ├── "t:acme:o:customer-org-id"     (per-org scope)            │
│      ├── "t:globex"                                                │
│      └── "t:globex:u:alice-user-id"                                │
└────────────────────────────────────────────────────────────────────┘
```

**Pourquoi Option A plutôt que « un workspace Membrane par tenant CDE » :**
- Les OAuth apps (HubSpot, Gmail, Slack, …) sont des secrets Croo
  partagés par tous les tenants CDE → setup unique.
- L'isolation Membrane par `tenantKey` est suffisante (DB-level).
- Migration vers Option B (workspace provisioning) possible plus tard
  pour un plan Enterprise si besoin de white-label OAuth.

## 2. Convention `tenantKey`

**Tous** les tenantKey générés par CDE sont préfixés par le tenant CDE
pour empêcher toute collision dans le workspace partagé :

| Scope             | Format                              | Exemple                       |
|-------------------|-------------------------------------|-------------------------------|
| per-user          | `t:{tenant_id}:u:{user_id}`         | `t:acme:u:alex-123`           |
| per-organization  | `t:{tenant_id}:o:{org_id}`          | `t:acme:o:customer-abc`       |
| per-tenant        | `t:{tenant_id}`                     | `t:acme`                      |

Implémentation : `_build_tenant_key()` dans
`apis/exposed/communication-b4f-api/app/presentation/routes/membrane_routes.py`.

**Fallback** : si scope = `per-organization` mais que l'utilisateur n'a
pas d'`active_organization_id`, on retombe sur `per-user` (sinon un user
isolé ne pourrait rien connecter).

## 3. Scope par défaut par catégorie d'intégration

Un admin Croo peut toujours override via `IntegrationSetting.scope_mode`
(CRUD sur `/api/v1/integration-settings`). Sans override, on applique ces
défauts (fonction `_default_scope_for`) :

| Catégorie             | Intégrations                                                | Scope par défaut     |
|-----------------------|-------------------------------------------------------------|----------------------|
| **CRM**               | HubSpot, Salesforce, Pipedrive, Zoho-CRM, Dynamics, Attio, Monday, Jira, Confluence | `per-organization` |
| **Email / Calendar**  | Gmail, Microsoft-Outlook                                    | `per-user`           |
| **Files**             | Google-Drive, OneDrive, Dropbox, Box, SharePoint, Google-Sheets | `per-user`         |
| **Messaging / Other** | Slack, Mailchimp, Quickbooks, Xero, Stripe                  | `per-user`           |

## 4. Authentification — les 3 types de tokens Membrane utilisés

### 4.1 Client Token (service-to-service)
- **Usage :** lecture workspace-level (`/integrations`, templates
  catalogue).
- **Obtention :** une fois, dans la Console Membrane → Settings →
  Access → Client Tokens → Long-lived Token.
- **Stockage :** variable `MEMBRANE_CLIENT_TOKEN` dans le `.env`
  (prod : secrets store).
- **Exemple de payload** (décodé) :
  ```json
  {
    "workspaceKey": "43db80da-...",
    "isAdmin": false,
    "subject": {"type": "service", "id": "cde-...", "name": "CDE"},
    "tenantId": "...",
    "clientTokenId": "...",
    "iss": "membrane"
  }
  ```

### 4.2 Tenant Token (per-request, généré à chaque appel)
- **Usage :** `/connections`, `/actions/{key}/run`, `/connect-url`
  (tout ce qui est scopé à un user/org CDE).
- **Obtention :** généré backend-side par `generate_membrane_token()`,
  signé avec `MEMBRANE_WORKSPACE_SECRET` (HS512) :
  ```python
  jwt.encode({
      "workspaceKey": settings.membrane_workspace_key,
      "tenantKey": "t:acme:u:alex-123",
      "name": "alex@acme.com",
      "fields": {"croo_user_id": "...", "croo_tenant_id": "acme"},
      "iat": now,
      "exp": now + timedelta(minutes=120),
  }, secret, algorithm="HS512")
  ```
- **Durée :** 5 à 120 minutes selon l'usage.
- **⚠️ Règle d'or :** jamais généré côté frontend. Le
  `workspaceSecret` ne quitte **jamais** le backend.

### 4.3 Admin Token (workspace management)
- **Usage :** listing/archiving de tenants Membrane, admin ops.
- **Obtention :** `isAdmin: true` + pas de `tenantKey` dans le JWT.
- **Non utilisé côté CDE** pour l'instant (Membrane crée les tenants
  automatiquement au premier appel JWT).

## 5. Flow utilisateur complet

```
┌──────────┐                ┌──────────┐                ┌──────────┐
│ Frontend │                │   CDE    │                │ Membrane │
│ (Angular)│                │ Backend  │                │   API    │
└─────┬────┘                └────┬─────┘                └────┬─────┘
      │                          │                            │
      │ 1. Login (email/pwd)     │                            │
      ├─────────────────────────>│                            │
      │<── JWT CDE {tenant_id} ──┤                            │
      │                          │                            │
      │ 2. GET /settings/integrations                         │
      ├─────────────────────────>│                            │
      │                          │ GET /integrations          │
      │                          │   [Client Token service]   │
      │                          ├───────────────────────────>│
      │                          │<── 20 integrations ────────│
      │<── catalog ──────────────┤                            │
      │                          │                            │
      │ 3. Click "Connect HubSpot"                             │
      ├─────────────────────────>│                            │
      │                          │ resolve scope(hubspot)     │
      │                          │ = per-organization         │
      │                          │ tenantKey =                │
      │                          │ "t:acme:o:customer-123"    │
      │                          │                            │
      │                          │ sign JWT (HS512)           │
      │                          │ with workspaceSecret       │
      │<─ {connect_url, jwt} ────┤                            │
      │                          │                            │
      │ 4. window.location =                                   │
      │    membrane hosted UI + jwt                            │
      ├───────────────────────────────────────────────────────>│
      │      (OAuth flow with HubSpot managed by Membrane)     │
      │<──── redirect ?membrane=connected ─────────────────────│
      │                          │                            │
      │ 5. GET /connections      │                            │
      ├─────────────────────────>│                            │
      │                          │ resolve same tenantKey     │
      │                          │ sign fresh JWT (5min)      │
      │                          ├───────────────────────────>│
      │                          │<── [{HubSpot: active}] ────│
      │<── status UI ────────────┤                            │
```

## 6. Webhooks Membrane → CDE

Les flows Membrane (email sync, CRM events, etc.) envoient des POST à
`POST /api/v1/membrane/webhook` sur le `communication-b4f-api`.

Le payload contient `tenant_key` (même format que ci-dessus), donc le
backend peut :
1. Parser `t:{tenant_id}:...` pour retrouver le tenant CDE.
2. Router l'événement au backend interne approprié (`email-backend-api`,
   `crm-backend`, etc.).

**Webhook URI à configurer dans Membrane Console :**
`{INGRESS_URL}/api/v1/membrane/webhook` (exposé publiquement).

## 7. Gestion des secrets (production)

| Secret                        | Rôle                                        | Rotation |
|-------------------------------|---------------------------------------------|----------|
| `MEMBRANE_WORKSPACE_KEY`      | Identifiant public du workspace             | Jamais   |
| `MEMBRANE_WORKSPACE_SECRET`   | Signe les tenant tokens JWT                 | Trimestrielle (Membrane Console) |
| `MEMBRANE_CLIENT_TOKEN`       | Long-lived service token                    | Annuelle (Membrane Console)      |

En dev : variables d'environnement dans `.env` racine.
En prod : **secrets store** (AWS Secrets Manager, Doppler, Vault, …).

## 8. Variables d'environnement

```bash
# .env
MEMBRANE_WORKSPACE_KEY=43db80da-f637-47a4-b7d7-7e301a4f4a62
MEMBRANE_WORKSPACE_SECRET=pat-xxxxxxxx     # pour signer les JWT tenant
MEMBRANE_CLIENT_TOKEN=eyJhbGciOiJIUzI1NiI...  # pour les calls service
MEMBRANE_API_URL=https://api.getmembrane.com
```

## 9. Points ouverts / TODO

- [ ] **Secrets store** : migrer les 3 secrets hors du `.env` en prod.
- [ ] **Webhook signature verification** : Membrane signe les webhooks
      avec un HMAC. Vérifier la signature dans `membrane_webhook()`.
- [ ] **Tenant archival** : quand un tenant CDE est soft-deleted, appeler
      `PATCH /tenants/{key}` sur Membrane pour archiver le tenant
      correspondant (désactive toutes ses connections).
- [ ] **Workspace provisioning flow (Option B)** : prévoir si un plan
      Enterprise veut white-label OAuth apps.
- [ ] **Rate-limiting per CDE tenant** : configurer les rate limits
      per-tenant dans la Console Membrane pour éviter qu'un tenant CDE
      en consomme trop.
- [ ] **Unit tests** pour `_build_tenant_key` et `_resolve_tenant_key`
      (il y a un script ad-hoc, pas encore de suite pytest).

## 10. Références

- Membrane docs Tenants : https://docs.getmembrane.com/docs/tenants
- Membrane docs Authentication : https://docs.getmembrane.com/docs/authentication
- Membrane docs Architecture : https://docs.getmembrane.com/docs/architecture
- Membrane Workspace Provisioning (Option B future) :
  https://docs.getmembrane.com/reference/Workspace%20Provisioning
- Code principal :
  - `apis/exposed/communication-b4f-api/app/presentation/routes/membrane_routes.py`
  - `apis/exposed/communication-b4f-api/app/infrastructure/external/membrane_service.py`
  - `apis/shared/config/__init__.py` (settings)
