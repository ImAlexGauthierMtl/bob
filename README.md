# Croo Digital Experience

Croo Digital Experience est l'application CDE à refactorer vers les règles d'architecture et de déploiement v1.4.

## Source De Vérité

- Règles architecture et déploiement: `docs/regles-architecture-deploiement.md`
- Instructions agent du dépôt: `AGENTS.md`
- Plan de conversion: `Cameleon/plan-refactor-cde-normes-v1.4.md`
- Matrice de validation: `Cameleon/matrice-validation-conformite-v1.4.md`
- Skills portables: `.agents/skills/`, version suivie dans `.agents/.skills-version`

Les anciens workflows locaux et anciennes règles d'agent ne sont pas des sources applicables pour ce dépôt. Les skills `dx_*` sont synchronisées depuis le repo central avec `./.agents/update-skills.sh`.

## Structure Actuelle

- `apis/exposed/`: APIs B4F exposées via le gateway.
- `apis/internal/`: APIs backend internes avec Alembic.
- `apis/shared/`: utilitaires partagés sans logique métier.
- `frontend/`: application Angular.
- `deploy/`: valeurs de déploiement projet et artefacts historiques à migrer vers le template CI/CD partagé.

## Cible

Le refactor doit conserver ce qui est déjà aligné avec la norme v1.4 et corriger les écarts: CI/CD, migrations, gateway, séparation B4F/Backend, règles DB Alembic, frontend Angular/NGRX et validation locale.
