# Guide Architectes — Créer les templates manquants

> **Objectif** : Chaque template élimine les décisions du LLM.
> Un bon template = un LLM faible (Qwen 0.5B) peut exécuter la tâche sans improviser.

---

## Comment écrire un TEMPLATE.md

Chaque template vit dans `templates/code/{backend|frontend|fullstack}/{nom-du-pattern}/TEMPLATE.md`.

### Structure obligatoire

```markdown
# Template: [Nom du pattern]

> Recette pour [action]. **Zéro décision** : [ce qui est dicté].

## Input requis
| Paramètre | Description | Exemple |
|-----------|-------------|---------|

## Fichier(s) à créer
[chemin exact]

## Code exact
[Le code complet à copier-adapter, avec les {placeholders}]

## Règles NON-NÉGOCIABLES
1. [Règle 1]
2. [Règle 2]
```

### Checklist pour valider un template

- [ ] Un développeur junior peut-il suivre le template sans poser de questions ?
- [ ] Le code exact est fourni (pas de "adapter selon le besoin")
- [ ] Les règles NON-NÉGOCIABLES sont listées
- [ ] Un exemple réel est référencé (quel fichier de quel projet)
- [ ] Les imports requis sont listés

### Où trouver les exemples

Utiliser les projets existants comme source de vérité :

| Projet | Chemin | Ce qu'il contient |
|--------|--------|-------------------|
| **Stories Teller** | `~/Dev/Stroies Teller/` | CRM, reviews, dashboard, sidebar, auth |
| **Baluchon** | `~/Dev/Baluchon/app-lebaluchon-dev-03/` | PMS hôtelier, vouchers, réservations |
| **Rondeau** | `~/Dev/rondeau/` | CRM courtiers, Angular |
| **ASQ** | `~/Dev/asq-consultant-crm/` | CRM consultants, import Excel |

---

## Templates à créer — Priorisés

### 🔴 Priorité HAUTE (bloquent la majorité des tickets)

#### 1. `templates/code/frontend/page-detail/TEMPLATE.md`
- **Quoi** : Page détail avec onglets, mode view/edit
- **Nommé par** : #67807, #67814, et tous les modules CRUD
- **Exemple source** : `Stroies Teller/frontend/src/app/pages/authenticated/accounts/account-detail.page.ts` (67k lignes)
- **Contenu attendu** :
  - Structure HTML : header + onglets + contenu
  - Mode view vs edit (toggle)
  - Chargement par `id` depuis la route
  - Pattern `loading / error / data`
  - Boutons : Sauvegarder, Annuler, Supprimer

#### 2. `templates/code/frontend/form-create-edit/TEMPLATE.md`
- **Quoi** : Formulaire de création/édition réutilisable
- **Nommé par** : #67822 (vérifier formulaires), #67820 (barre création)
- **Exemple source** : Formulaire account create dans Stories Teller
- **Contenu attendu** :
  - Structure formulaire Angular (Reactive Forms ou template-driven)
  - Validation avec messages d'erreur
  - Boutons : Créer / Sauvegarder / Annuler
  - Pattern pour les champs : input, select, textarea, date

#### 3. `templates/code/frontend/toolbar/TEMPLATE.md`
- **Quoi** : Barre d'action en haut d'une page
- **Nommé par** : #67820 (barre création manquante)
- **Exemple source** : `accounts.page.ts` lignes 12-32
- **Contenu attendu** :
  - Structure HTML : `h-10 bg-white border-b`
  - Boutons : Nouveau, Filtrer, Exporter, Rafraîchir
  - Séparateurs verticaux entre groupes
  - Responsive

#### 4. `templates/code/backend/test-backend/TEMPLATE.md`
- **Quoi** : Tests pytest pour un router CRUD
- **Nommé par** : Tous les modules
- **Exemple source** : `Stroies Teller/backend/tests/`
- **Contenu attendu** :
  - Fixtures : client, db, user auth
  - 6 tests minimum : list, create, get, get_404, update, delete
  - Pattern conftest.py
  - 30% tests négatifs

#### 5. `templates/code/backend/migration-alembic/TEMPLATE.md`
- **Quoi** : Créer une migration Alembic
- **Nommé par** : Tout ajout/modif de modèle
- **Contenu attendu** :
  - Commande exacte `alembic revision --autogenerate`
  - Vérification avant `alembic upgrade head`
  - Pattern de rollback `alembic downgrade -1`

---

### 🟡 Priorité MOYENNE (couvrent des patterns récurrents)

#### 6. `templates/code/frontend/sidebar/TEMPLATE.md`
- **Quoi** : Composant navigation latérale
- **Nommé par** : #67824 (scroll), #67821 (drapeau)
- **Exemple source** : `sidebar.component.ts` (4.7k)
- **Contenu attendu** :
  - Structure HTML avec sections, icônes, links
  - Scroll overflow
  - Active state sur la route courante
  - Collapse/expand

#### 7. `templates/code/frontend/filter-dropdown/TEMPLATE.md`
- **Quoi** : Dropdown de filtre pour les listes
- **Nommé par** : #67817 (séparer par centre)
- **Contenu attendu** :
  - Signal input pour les options
  - Output pour la sélection
  - Reset button

#### 8. `templates/code/frontend/page-list-grouped/TEMPLATE.md`
- **Quoi** : Liste groupée par catégorie
- **Nommé par** : #67817 (séparer SPA par centre)
- **Contenu attendu** :
  - Même pattern que page-list mais avec sections
  - Groupement par un champ
  - Compteur par groupe

#### 9. `templates/code/frontend/component-card/TEMPLATE.md`
- **Quoi** : Composant card réutilisable
- **Exemple source** : `project-card.component.ts` (2.9k)
- **Contenu attendu** :
  - Signal inputs pour titre, description, actions
  - Slot content avec `ng-content`
  - Hover effect

#### 10. `templates/code/fullstack/feature-action/TEMPLATE.md`
- **Quoi** : Feature type action (import, export, sync, batch)
- **Nommé par** : #67818 (import IQWare)
- **Contenu attendu** :
  - Endpoint backend dédié (POST /api/{resource}/action)
  - Service frontend pour l'action
  - Bouton avec loading state
  - Feedback success/error

---

### 🟢 Priorité BASSE (patterns spécialisés)

#### 11. `templates/code/fullstack/auth-flow/TEMPLATE.md`
- JWT login, refresh token, httpOnly cookies, auth guard

#### 12. `templates/code/frontend/component-timer/TEMPLATE.md`
- Timer interactif (Stories Teller: `task-timer.component.ts`)

#### 13. `templates/code/fullstack/file-upload/TEMPLATE.md`
- Upload de fichiers avec preview, progress bar

#### 14. `templates/code/frontend/dashboard/TEMPLATE.md`
- Dashboard avec cards KPI, graphiques, listes récentes

#### 15. `templates/code/infra/docker-compose/TEMPLATE.md`
- docker-compose.yml pour multi-services

#### 16. `templates/code/infra/gitlab-ci/TEMPLATE.md`
- Pipeline .gitlab-ci.yml dev/staging/prod

---

## Workflow de création d'un template

```
1. Choisir un template à créer dans cette liste
2. Trouver l'exemple source dans un projet existant
3. Extraire le pattern générique (remplacer les noms spécifiques par {placeholders})
4. Écrire le TEMPLATE.md avec le code exact
5. Vérifier avec la checklist ci-dessus
6. Commiter : git commit -m "[framework-hdq] feat: add template {nom}"
7. Déplacer la ligne dans docs/missing-templates.md → section "Comblés ✅"
```
