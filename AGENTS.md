## Source De Vérité

- La source de vérité architecture et déploiement est `docs/regles-architecture-deploiement.md`, version 1.4.
- Les skills portables `dx_*` versionnés dans `.agents/skills/` restent la référence officielle; les skills de conversion CDE vivent dans `Cameleon/skills/`.
- Mettre à jour les skills avec `./.agents/update-skills.sh`; ne pas modifier un `SKILL.md` localement.
- Les anciens workflows locaux, règles Playwright locales et templates d'agent ne sont plus applicables.
- Les documents historiques du dépôt, dont `docs/ARCHITECTURE.md` et les README d'API, servent seulement de contexte. Pour les intégrations actives, utiliser `docs/PIPEDREAM_ARCHITECTURE.md`. En cas de conflit, appliquer `docs/regles-architecture-deploiement.md`.

## Cible De Refactor

- Conserver la structure CDE existante quand elle est déjà conforme: `apis/exposed/`, `apis/internal/`, `frontend/`, `deploy/values/`.
- Refactorer vers le modèle deux tiers: B4F exposées par le gateway, Backends internes, aucun accès Backend direct depuis le frontend.
- Supprimer toute DDL applicative au démarrage; toute création ou modification DB passe par Alembic avec downgrade testé.
- Remplacer les migrations CI/manuelles par l'initContainer Kubernetes avec Lease.
- Ne pas traiter le CI/CD ni Harbor dans la conversion active tant que les éléments plateforme manquent; marquer ces règles `SKIP_CI_CD` dans la matrice Cameleon.
- Déplacer la logique externe hors des B4F quand elle viole la séparation B4F/Backend.
- Valider le refactor avec `Cameleon/matrice-validation-conformite-v1.4.md` et produire le rapport au format du § 9.

## Validation

- Après chaque changement, exécuter la validation locale pertinente avant d'annoncer que c'est terminé.
- Après chaque changement de code, déclencher un subagent de certification indépendant qui évalue le résultat contre `Cameleon/matrice-certification-regles-architecture-v1.5.md` et attribue un score sur 10. Si le score est inférieur à 10/10, le subagent doit retourner à l'agent principal les critères non conformes, les preuves manquantes et les corrections attendues; l'agent principal doit corriger puis relancer la certification avant de déclarer le travail terminé.
- Pour les changements UI, valider dans un navigateur et conserver les captures dans `captures/`, dossier gitignoré.
- Une capture d'erreur, de page blanche, de login bloqué ou d'écran non lié ne compte pas comme validation.
- Inclure les captures pertinentes dans la conversation lorsque l'UI est touchée.
