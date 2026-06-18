---
name: dx_master_create
description: Bootstrap un nouveau projet conforme aux règles d'architecture & déploiement, ou orchestre la création coordonnée de plusieurs éléments (APIs + frontend + pipeline + chart values + scripts locaux). À invoquer quand l'utilisateur demande "crée un nouveau projet", "bootstrap selon nos règles", "monte un projet from scratch", "ajoute toute l'infra conforme". Délègue aux skills intermediate create, certaines en parallèle, d'autres séquentielles.
metadata:
  version: 1.0.0
  source: code-agent-skills-v1.0
  reference: docs/architecture/regles-architecture-deploiement.md
---

# dx_master_create — Bootstrap projet conforme

## Rôle

Orchestrer la création d'un projet (ou d'un sous-ensemble cohérent) qui respecte
**dès la première commit** les règles d'architecture & déploiement. Cible : un
développeur qui démarre un nouveau service / une nouvelle stack.

## Avant de commencer

Cette skill **a besoin de paramètres** que l'agent doit confirmer avec
l'utilisateur :

1. **Nom du projet** (slug kebab-case, ex. `front-office`)
2. **Périmètre** : quelles parties créer (APIs ? frontend ? les deux ? pipeline
   uniquement ?)
3. **Liste des APIs souhaitées** : pour chaque API, son nom et son tier (B4F ou
   Backend). Rappel : un B4F = un domaine frontend, un Backend = une entité
   principale.
4. **Le repo `ci-cd-unified-template-v1.0` est-il déjà en place ?** (URL : `git@gitlab.tools.thesmartcrew.com:croo-dev/ci-cd-unified-template-v1.0.git`)
   - Si non : invoquer aussi `dx_intermediate_create_cicd_repo` (séquentiel, en
     premier).
5. **Environnement cible** : noms canoniques `dev`, `staging`, `prod` (jamais
   `production`, cf. § 5.1).

Si l'un de ces points est ambigu, **demander** plutôt qu'inventer.

## Workflow d'orchestration

Il y a des **dépendances d'ordre** dans la création — pas tout peut paralléliser.

### Étape 1 (séquentielle) — repo cicd-templates

Si le repo partagé n'existe pas encore :

```
Invoque dx_intermediate_create_cicd_repo
```

Il pose :
- arborescence du repo central (templates parent/child, deploy/scripts, deploy/helm/api-chart)
- chart Helm `api-chart` avec initContainer migrate, probes, ingress conditionnel
- scripts deploy / migrate_with_lease.py / smoke-test
- templates pipeline (build Kaniko + verify Harbor, smoke-test, rollback manuel)
- `harbor-cve-whitelist.yaml`, `importlinter-template.toml`, `eslintrc-template.js`
- versioning Semver

Tout le reste **dépend** que ce repo existe et soit accessible par le projet via
`include:` du `.gitlab-ci.yml`.

### Étape 2 (séquentielle) — squelette projet

Invoquer `dx_intermediate_create_project_conventions` pour poser :
- arborescence racine (`apis/`, `frontend/`, `deploy/values/`, `docs/`, `data/`)
- `.gitlab-ci.yml` minimal qui `include:` le repo partagé sur tag versionné
- `README.md` avec badges pipeline/coverage
- `AGENTS.md` projet
- nettoyage de tous les outillages IA spécifiques (cf. § 10.3)

### Étape 3 (parallèle) — création des éléments fonctionnels

Pour chaque API, frontend, infra locale, lancer en **parallèle** via subagents :

| Subagent | Skill |
|---|---|
| Pour chaque Backend demandé | `dx_intermediate_create_apis` avec param tier=backend, nom=… |
| Pour chaque B4F demandé | `dx_intermediate_create_apis` avec param tier=b4f, nom=… |
| Si frontend demandé | `dx_intermediate_create_frontend_ngrx` puis `dx_intermediate_create_frontend_clean_archi` |
| Toujours | `dx_intermediate_create_local_dev` (scripts racine, docker-compose, .env.example) |
| Toujours | `dx_intermediate_create_k8s_config` (values par env, observabilité) |
| Toujours | `dx_intermediate_create_cicd_pipeline` (values pipeline si non couverts par squelette) |
| Toujours | `dx_intermediate_create_registry_to_k8s` (provision-registry-access) |

### Étape 4 (séquentielle finale) — vérification

Une fois tout en place :

```
Invoque dx_master_check
```

et corriger les éventuels écarts. **Ne pas se déclarer terminé avant que
`dx_master_check` ne sorte sans violation critique.**

## Règles non négociables pendant la création

1. **Le terme `authentication` est banni** (§ 2.5). Toute API d'auth est splittée
   d'emblée en `auth-b4f-api` + `iam-backend-api`. Schéma DB = `iam`.
2. **Pas de DB dans les B4F** (§ 2.2), **pas d'ingress sur les Backend** (§ 2.3).
3. **PgBouncer en transaction mode** dans `docker-compose.yml` (§ 11.3) ET dans
   le chart (§ 2.7.4).
4. **Initialisation DB par migration Alembic uniquement** (§ 2.7.5) — jamais de
   `create_all()` au boot. L'initContainer migrate du Deployment utilise
   `migrate_with_lease.py` du repo partagé.
5. **Toutes les APIs exposent les 5 endpoints de santé** dès la première
   itération (§ 5.10).
6. **Aucun préfixe `DEV_`/`STAGING_`/`PROD_`** sur les variables CI/CD (§ 6.1).
7. **Kubeconfig en type File**, jamais en string base64 (§ 5.4).
8. **Pas de `latest`** dans les tags d'image (§ 4.12).

## Posture recommandée

Cette skill **modifie** le projet : l'agent doit disposer d'un accès en
écriture. Demander confirmation avant toute création massive (>10 fichiers).


## Anti-patterns

1. **Partir d'un template d'une équipe précédente** sans le passer par
   `dx_master_check` — généralement non conforme à la version actuelle de la
   doc.
2. **Sauter `dx_intermediate_create_cicd_repo`** quand le repo n'existe pas. Le
   projet aura un `.gitlab-ci.yml` qui pointe dans le vide.
3. **Créer la B4F avant la Backend** lors d'un split d'un monolithe (§ 2.8 :
   l'ordre est Backend → B4F → gateway → frontend).
4. **Ne pas lancer `dx_master_check` à la fin** — la skill `create` n'est pas
   complète tant que le projet n'est pas vert.
5. **Tout faire séquentiellement** quand l'étape 3 peut paralléliser sans
   conflit (chaque API a son sous-dossier).
