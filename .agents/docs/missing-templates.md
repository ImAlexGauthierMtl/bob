# Templates manquants — À créer par les architectes

> Ce registre documente les patterns de code qui n'ont PAS encore de template d'exécution.
> Quand `/start` détecte un pattern UNRULED, il l'ajoute ici.
> Les architectes/ingénieurs créent ensuite le template dans `templates/code/`.

## Comment ajouter un template manquant

Ajouter une ligne au tableau ci-dessous. Quand le template est créé, le déplacer dans la section "Comblés".

---

## Templates manquants (UNRULED)

| Date | Pattern manquant | Contexte (d'où vient le besoin) | Priorité | Assigné |
|------|------------------|---------------------------------|----------|---------|
| 2025-03-05 | Login / Auth flow (JWT) | Chaque nouveau projet | HIGH | — |
| 2025-03-05 | File upload + attachments | Stories Teller, Baluchon | MED | — |
| 2025-03-05 | Dashboard / graphiques | Stories Teller dashboard | MED | — |
| 2025-03-05 | Chat / real-time (WebSocket) | Stories Teller chat | LOW | — |
| 2025-03-05 | Page détail avec onglets | account-detail (67k lignes) | HIGH | — |
| 2025-03-05 | Formulaire create/edit | Tous les modules CRUD | HIGH | — |
| 2025-03-05 | CI/CD pipeline config (.gitlab-ci.yml) | Déploiement | MED | — |
| 2025-03-05 | Docker / docker-compose | Conteneurisation | MED | — |
| 2025-03-05 | Sidebar / navigation layout | Layout principal | MED | — |
| 2025-03-05 | Pagination / infinite scroll | Listes longues | MED | — |
| 2025-03-05 | Tests backend (pytest fixtures) | Tous les modules | HIGH | — |
| 2025-03-05 | Tests frontend (TestBed) | Tous les composants | MED | — |
| 2025-03-05 | Migration Alembic | Ajout de tables/colonnes | HIGH | — |

## Templates comblés (RULED) ✅

| Date comblé | Pattern | Template créé |
|-------------|---------|---------------|
| 2025-03-05 | Modèle SQLAlchemy | `templates/code/backend/model-sqlalchemy/` |
| 2025-03-05 | Schemas Pydantic | `templates/code/backend/schemas-pydantic/` |
| 2025-03-05 | Router CRUD FastAPI | `templates/code/backend/router-crud/` |
| 2025-03-05 | Interface TypeScript | `templates/code/frontend/model-typescript/` |
| 2025-03-05 | Service HTTP Angular | `templates/code/frontend/service-http/` |
| 2025-03-05 | Store NGRX (5 fichiers) | `templates/code/frontend/store-ngrx/` |
| 2025-03-05 | Page liste | `templates/code/frontend/page-list/` |
| 2025-03-05 | Badge de statut | `templates/code/frontend/component-badge/` |
| 2025-03-05 | Dialog de confirmation | `templates/code/frontend/component-dialog/` |
| 2025-03-05 | Module CRUD full-stack | `templates/code/fullstack/crud-module/` |
