# Plan de refactor CDE vers les normes v1.4

Date: 2026-06-18
Projet: Croo Digital Experience (`app-cde-dev-01`)
Source de vérité: `docs/regles-architecture-deploiement.md`
Skills de conversion: `Cameleon/skills/`
Skills officiels de référence: `.agents/skills/` depuis `croo-dev/code-agent-skills-v1.0`, version `v1.7.0`
Matrice de contrôle: `Cameleon/matrice-validation-conformite-v1.4.md`

## Objectif

Refactorer CDE vers les règles d'architecture et déploiement v1.4. Le plan suit le document officiel: modèle API deux tiers, frontend Angular/NGRX, Kubernetes/gateway, variables repo-locales, conventions projet, observabilité, développement local, Clean Architecture et validation finale au format § 9.

Périmètre actif: conversion vérifiable dans le dépôt et en Docker local. Le CI/CD et Harbor sont volontairement exclus pour cette passe, car les éléments plateforme requis ne sont pas disponibles.

## Principes d'exécution

- Utiliser `docs/regles-architecture-deploiement.md` comme source de vérité unique.
- Utiliser les skills `Cameleon/skills/cde-*` comme guides d'analyse, de création et de check.
- Garder les skills officiels `.agents/skills/` comme référence portable et les skills Cameleon comme guide de conversion.
- Ne pas recréer d'ancien framework local; conserver seulement `.agents/skills/`, `.agents/update-skills.sh`, `.agents/.skills-version` et `AGENTS.md`.
- Piloter chaque MR avec la matrice de conformité: une règle corrigée doit avoir une preuve, une commande ou un fichier témoin.
- Ne pas mélanger refactor structurel et refactor fonctionnel sans preuve de non-régression.
- Ne pas modifier ni suivre le CI/CD/Harbor pendant cette conversion; marquer ces lignes `SKIP_CI_CD` dans la matrice.

## État initial CDE

### Déjà aligné partiellement

- APIs séparées en `apis/exposed/` et `apis/internal/`.
- Backends internes avec dossiers Alembic.
- Frontend isolé dans `frontend/`.
- Présence d'un gateway chart, d'un frontend chart et d'un api chart, à migrer vers le modèle repo partagé.
- `docker-compose.yml` contient PostgreSQL et Redis, à compléter/aligner avec PgBouncer et Alloy.

### Violations déjà observées

- `.gitlab-ci.yml` inclut `infrastructure/ci-templates` au lieu de `croo-dev/ci-cd-unified-template-v1.0`.
- Pipeline contient des stages `migrate-*`, interdits par § 4.2 et § 4.12.
- `deploy/helm/` et `deploy/scripts/` portent de la logique qui doit vivre dans le repo CI/CD partagé (§ 4.1, § 8.3).
- `deploy/helm/api-chart/templates/deployment.yaml` ne contient pas l'initContainer `migrate` avec `scripts/migrate_with_lease.py`.
- `deploy/helm/api-chart` ne contient pas le RBAC Lease Kubernetes requis.
- `deploy/helm/gateway-chart/templates/ingress.yaml` route encore `apiRoutes.apis`; le gateway doit exposer les B4F seulement.
- Plusieurs backends appellent `Base.metadata.create_all(...)` au démarrage, interdit par § 2.7.5.
- Certaines B4F appellent des services externes directement, notamment MS365/Pipedream; la règle v1.4 exige de déplacer ces intégrations côté Backend.
- Le frontend repose surtout sur `shared/services/*.service.ts`; le store NGRX par B4F reste à structurer.
- Un dossier d'outil local `.kilo/` existait à la racine et doit être supprimé selon § 10.3.

## Phase 0 - Skills, source de vérité et matrice

But: rendre le dépôt autonome et aligné avec § 10.3 et § 10.4.

- Versionner `docs/regles-architecture-deploiement.md`.
- Installer `.agents/skills/` depuis `croo-dev/code-agent-skills-v1.0`.
- Ajouter `.agents/update-skills.sh` et `.agents/.skills-version`.
- Valider les skills avec `scripts/validate-skills.sh` du repo central.
- Créer les skills de conversion sous `Cameleon/skills/`: API boundaries, DB/Alembic, K8s/gateway, frontend NGRX, observabilité, dev local, Clean Architecture et validation finale.
- Garder `AGENTS.md` court: source de vérité, cible de refactor, validation.
- Supprimer les dossiers/fichiers d'outils spécifiques interdits par § 10.3.

Skills utiles: `cde-check-local-dev`, `cde-master-validation`.

## Phase 1 - Architecture API deux tiers (§ 2, § 8.1)

But: garantir que B4F, Backends, DB et event bus respectent la séparation stricte.

- Auditer tous les dossiers `apis/exposed/` et `apis/internal/`.
- Confirmer qu'aucune B4F ne possède `alembic/`, modèles DB ou `DATABASE_URL`.
- Confirmer qu'aucune route frontend ou gateway ne cible un Backend.
- Identifier les B4F proxy CRUD 1:1 et décider: enrichir logique B4F ou fusionner/réorganiser.
- Déplacer les appels services externes depuis les B4F vers des Backends.
- Remplacer tout HTTP Backend->Backend par événements Redis.
- Standardiser `apis/exposed/shared/` et `apis/internal/shared/`, sans logique métier.

Skill utile: `cde-check-api-boundaries`.

## Phase 2 - Alembic et DB (§ 2.7, § 8.1)

But: supprimer toute DDL runtime et rendre les migrations réversibles.

- Supprimer tous les `Base.metadata.create_all(...)`.
- Vérifier que la première migration de chaque Backend crée le schéma, les tables, droits et privilèges.
- Vérifier que chaque migration a un `downgrade()` non vide et symétrique.
- Convertir tout `.sql` manuel en migration Alembic.
- Ajouter les tests `alembic downgrade -1 && alembic upgrade head`.
- Confirmer PgBouncer transaction mode, pools bas et prepared statements désactivés.

Skill utile: `cde-check-database-alembic`.

## Phase 3 - CI/CD v1.4 (§ 4, § 8.3) - hors périmètre actif

But documenté dans les règles: remplacer la CI projet par le modèle parent/child du repo partagé.

Décision actuelle: ne pas traiter cette phase dans la conversion active. Les règles CI/CD seront marquées `SKIP_CI_CD` dans la matrice, avec la raison: éléments plateforme/template/variables manquants.

Skill utile pour le suivi documentaire seulement: `cde-master-validation`.

## Phase 4 - Kubernetes, gateway et charts (§ 5, § 8.4)

But: un seul point d'entrée, backends internes, migrations par Lease Kubernetes.

- Migrer `deploy/helm/` et `deploy/scripts/` vers le modèle values-only attendu par le repo partagé.
- Ajouter ou consommer l'initContainer `migrate` des Backends.
- Ajouter le RBAC Lease `coordination.k8s.io`.
- Retirer tout Backend du gateway.
- S'assurer que le gateway route `/` vers le frontend et `/api/<service>/v1` vers les B4F seulement.
- Vérifier HTTPS redirect, wildcard TLS, copie depuis `cert-manager`, namespaces canoniques et kubeconfig par indirection.

Skill utile: `cde-check-k8s-gateway`.

## Phase 5 - Harbor et registry (§ 7, § 8.6) - hors périmètre actif

But documenté dans les règles: Harbor devient la registry primaire, avec robot accounts, scan et signature.

Décision actuelle: ne pas traiter cette phase dans la conversion active. Les règles Harbor seront marquées `SKIP_CI_CD`, car elles dépendent des variables GitLab/Harbor et du template CI/CD.

Skill utile pour le suivi documentaire seulement: `cde-master-validation`.

## Phase 6 - Frontend Angular/NGRX (§ 3, § 14, § 8.2, § 8.12)

But: aligner le frontend avec un service et un feature store par B4F.

- Cartographier B4F -> service Angular -> feature NGRX.
- Déplacer les appels HTTP vers Effects + Services.
- Éliminer les services injectés directement dans les components pour chargement d'état.
- Mapper les DTO HTTP vers modèles domaine avant stockage NGRX.
- Ajouter Playwright E2E dans `frontend/e2e/`, hors pipeline CI.
- Ajouter un hook pre-commit smoke E2E pour changements frontend.

Skill utile: `cde-check-frontend-ngrx`.

## Phase 7 - Observabilité et probes (§ 5.8 à § 5.10, § 8.8)

But: rendre les APIs observables et smoke-testables.

- Vérifier `/liveness`, `/readiness`, `/startup`, `/health`, `/metrics` sur chaque API.
- S'assurer que `/liveness` n'appelle aucun service externe.
- S'assurer que `/health` liste toutes les dépendances avec statut et latence.
- Propager `traceparent` et `trace_id` sur HTTP, logs et événements Redis.
- Configurer OTel vers Alloy, sampling dev/prod et logs JSON stdout/stderr.

Skill utile: `cde-check-observability`.

## Phase 8 - Développement local et conventions (§ 10, § 11, § 12)

But: rendre un checkout local reproductible et uniforme.

- Ajouter/aligner `run_all_apis.sh`, `migrate_all_apis.sh`, `run_all_apis_tests.sh`, `run_frontend.sh`, `run_frontend_tests.sh`, `run_frontend_e2e.sh`.
- Vérifier `run_api.sh`, `run_tests.sh`, et `migrate.sh` uniquement dans les Backends.
- Aligner `docker-compose.yml` avec `postgres`, `pgbouncer`, `redis`, `alloy`.
- Ajouter `.env.example`, sans secret de production.
- Appliquer la structure Clean Architecture: `domain/`, `application/`, `infrastructure/`, `presentation/`.
- Ajouter import-linter ou équivalent pour bloquer les dépendances interdites.

Skills utiles: `cde-check-local-dev`, `cde-check-clean-architecture`.

## Phase 9 - Validation finale et rapport (§ 8, § 9)

But: prouver la conformité après refactor.

- Exécuter `Cameleon/skills/cde-master-validation` comme guide de revue complète.
- Remplir `Cameleon/matrice-validation-conformite-v1.4.md`.
- Produire le rapport au format § 9.
- Fusionner toutes les branches de conversion ensemble.
- Monter le projet en Docker local et documenter le résultat.
- Joindre les preuves: commandes, fichiers, captures UI si frontend touché, smoke-test local ou Docker local si disponible.
- Classer chaque écart restant: `critique`, `à corriger`, `non applicable`, `bloqué`.
- Classer CI/CD et Harbor comme `SKIP_CI_CD` tant que les éléments plateforme restent absents.

## Ordre recommandé des MRs

1. Règles, skills Cameleon, matrice et hygiène du dépôt.
2. Helm/values/gateway vérifiables localement, sans suivi CI/CD.
3. Suppression DDL runtime et durcissement Alembic.
4. Gateway: frontend + B4F seulement.
5. Déplacement services externes hors B4F.
6. Event bus Redis entre Backends.
7. Probes, observabilité et trace context.
8. Frontend NGRX par B4F.
9. Dev local, Clean Architecture, fusion finale des branches et Docker local.

## Définition de terminé

- `docs/regles-architecture-deploiement.md` est versionné et appliqué.
- `.agents/skills/` contient les skills `dx_*` officiels et validés.
- `Cameleon/skills/` contient les skills de conversion CDE validés.
- `.agents/update-skills.sh` et `.agents/.skills-version` sont présents.
- Aucun ancien workflow local ou dossier d'outil spécifique interdit ne reste actif.
- La matrice de conformité est remplie avec preuves.
- Le rapport final suit le format § 9.
- Les branches de conversion sont fusionnées ensemble.
- Docker local a été monté et le résultat est documenté.
- Chaque violation critique est corrigée ou explicitement bloquée avec cause vérifiable.
