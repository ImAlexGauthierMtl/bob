## Source De Vérité

- La source de vérité architecture et déploiement est `docs/regles-architecture-deploiement.md`, version 1.4.
- Les skills applicables sont les skills portables `dx_*` versionnés dans `.agents/skills/`, synchronisés depuis `croo-dev/code-agent-skills-v1.0`.
- Mettre à jour les skills avec `./.agents/update-skills.sh`; ne pas modifier un `SKILL.md` localement.
- Les anciens workflows locaux, règles Playwright locales et templates d'agent ne sont plus applicables.
- Les documents historiques du dépôt, dont `docs/ARCHITECTURE.md`, `docs/MEMBRANE_ARCHITECTURE.md` et les README d'API, servent seulement de contexte. En cas de conflit, appliquer `docs/regles-architecture-deploiement.md`.

## Cible De Refactor

- Conserver la structure CDE existante quand elle est déjà conforme: `apis/exposed/`, `apis/internal/`, `frontend/`, `deploy/values/`.
- Refactorer vers le modèle deux tiers: B4F exposées par le gateway, Backends internes, aucun accès Backend direct depuis le frontend.
- Supprimer toute DDL applicative au démarrage; toute création ou modification DB passe par Alembic avec downgrade testé.
- Remplacer les migrations CI/manuelles par l'initContainer Kubernetes avec Lease.
- Migrer la CI/CD vers `croo-dev/ci-cd-unified-template-v1.0` avec Harbor/Cosign, sans stage `migrate-*` séparé.
- Déplacer la logique externe hors des B4F quand elle viole la séparation B4F/Backend.
- Valider le refactor avec `Cameleon/matrice-validation-conformite-v1.4.md` et produire le rapport au format du § 9.

## Validation

- Après chaque changement, exécuter la validation locale pertinente avant d'annoncer que c'est terminé.
- Pour les changements UI, valider dans un navigateur et conserver les captures dans `captures/`, dossier gitignoré.
- Une capture d'erreur, de page blanche, de login bloqué ou d'écran non lié ne compte pas comme validation.
- Inclure les captures pertinentes dans la conversation lorsque l'UI est touchée.
