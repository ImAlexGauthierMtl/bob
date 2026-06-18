# Audit API boundaries v1.4

Date: 2026-06-18
Projet: Croo Digital Experience (`app-cde-dev-01`)
Source: `docs/regles-architecture-deploiement.md`, sections 2.1 a 2.4 et table d'ecarts section 8.1

## Portee

Cet audit couvre les regles A-06 et A-07 de la matrice Cameleon:

- A-06: une B4F ne doit pas etre seulement un miroir CRUD 1:1 sans logique de domaine.
- A-07: chaque Backend doit posseder une entite principale avec des entites secondaires liees.

Le CI/CD, Harbor et les validations registry restent hors perimetre actif.

## Inventaire APIs

### B4F exposees

| B4F | Domaine frontend | Lecture |
|---|---|---|
| `auth-b4f-api` | Auth/session/admin IAM | Conforme au domaine frontend; `auth_routes.py` contient JWT, refresh, rate limit et session courante. Les routes admin user/tenant/role restent surtout des facades CRUD. |
| `crm-b4f-api` | CRM | Partiellement corrige: `/dashboard/summary` compose contacts, organisations, opportunites, activites et produits en une reponse UI. Des routes CRUD directes restent presentes comme facades de support. |
| `communication-b4f-api` | Communication/integrations | Conforme A-08 apres refactor provider. Partiellement corrige A-06: `/integrations/overview` compose settings, connexions MS365/Membrane et smart labels. Les routes provider minces sont une delegation volontaire pour garder `email-backend-api` invisible. |
| `ai-agent-b4f-api` | Agent/Bob | Conforme A-06 au niveau B4F: `bob_chat_routes.py` gere session/titre/reponse Bob et `client_map_routes.py` orchestre l'analyse comportementale; les routes BCC/training/capability/settings sont des facades de support. |
| `platform-b4f-api` | Workflows/usage/platform | Corrige: `/overview` compose workflows, monitoring, executions recentes et usage; `workflow_routes.py` contient aussi une logique d'override. `enrichment_routes.py` reste une placeholder non migree, mais pas une facade CRUD. |
| `kb-b4f-api` | Knowledge base | Partiellement corrige: `/kb/home` compose categories, articles recents, articles populaires et stats. Les routes CRUD/search restent des facades de support. |

Conclusion A-06: conforme au niveau B4F. Chaque B4F expose maintenant au moins une responsabilite de domaine, composition ou orchestration alignee frontend. Des facades CRUD restent presentes, mais elles ne constituent plus l'unique comportement de leur B4F.

## Cartographie backend A-07

| Backend | Entite principale | Entites secondaires liees | Statut A-07 |
|---|---|---|---|
| `user-backend-api` | User/IAM | tenants, roles, permissions, assignments | OK |
| `contact-backend-api` | Contact | aucune famille non liee relevee | OK |
| `org-backend-api` | Organization | departments, user_departments | OK |
| `opportunity-backend-api` | Opportunity | quotes, opportunity_products | OK |
| `activity-backend-api` | Activity | aucune famille non liee relevee | OK |
| `product-backend-api` | Product | aucune famille non liee relevee | OK |
| `email-backend-api` | Email provider account/data | connections, synced emails/events, contacts, smart labels, integration settings, provider variants MS365/Membrane | OK |
| `agent-backend-api` | Bob/agent knowledge and capability model | BCC taxonomy, capabilities, training, client maps, Bob settings | OK avec domaine large; a surveiller si le module grossit encore |
| `workflow-backend-api` | Workflow | steps, executions, step executions | OK |
| `kb-backend-api` | Knowledge base article | categories, feedback/stat endpoints via backend | OK |
| `usage-backend-api` | Usage transaction | cost rate cards | OK |

Conclusion A-07: conforme au niveau ownership fonctionnel. Aucun backend ne depend d'une autre famille de tables backend dans son dossier `domain/entities`; les entites secondaires relevees appartiennent au meme domaine fonctionnel que l'entite principale.

## Preuves locales

Commandes utilisees:

```bash
find apis/exposed -maxdepth 2 -type d -name '*-b4f-api'
find apis/internal -maxdepth 2 -type d -name '*-backend-api'
find apis/exposed -path '*/app/presentation/routes/*.py' -type f
find apis/internal -path '*/app/domain/entities/*.py' -type f
rg -n "proxy|Proxy|simple proxy|1:1|create_service_client|_client\\.(get|post|put|patch|delete)" apis/exposed -g '*.py' -g '!**/tests/**'
rg -n "from app\\.domain\\.entities|from .*backend|apis/internal|schema *=|__tablename__" apis/internal/*-backend-api/app/domain/entities -g '*.py'
```

## Suite recommandee A-06

1. `crm-b4f-api`: fait pour le premier niveau avec `/dashboard/summary`; poursuivre avec `/contacts/{id}/summary` ou `/opportunities/{id}/workspace` si le frontend en a besoin.
2. `kb-b4f-api`: fait pour le premier niveau avec `/kb/home`; poursuivre avec des compositions de recherche guidee si le frontend en a besoin.
3. `ai-agent-b4f-api`: garder `bob_chat_routes.py` et `client_map_routes.py` comme points B4F metier; separer les routes BCC de pure administration si le module grossit.
4. `communication-b4f-api`: fait pour le premier niveau avec `/integrations/overview`; garder les routes provider comme delegation externe obligatoire.
5. `platform-b4f-api`: fait pour le premier niveau avec `/overview`; completer ou retirer `enrichment_routes.py` placeholder dans une passe fonctionnelle dediee.
