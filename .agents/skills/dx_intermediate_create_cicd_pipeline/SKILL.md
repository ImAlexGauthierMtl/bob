---
name: dx_intermediate_create_cicd_pipeline
description: Crée le .gitlab-ci.yml minimal du projet (uniquement include vers le repo central versionné), génère les values Helm par environnement et par API dans deploy/values/, configure les variables CI/CD GitLab requises. À invoquer quand on bootstrap le pipeline d'un projet. Suppose que le repo ci-cd-unified-template-v1.0 existe — sinon invoque dx_intermediate_create_cicd_repo en amont.
metadata:
  reference: § 4 + § 5.5 (variables) de docs/architecture/regles-architecture-deploiement.md
---

# dx_intermediate_create_cicd_pipeline

## Prérequis

Le repo `ci-cd-unified-template-v1.0` doit exister et publier un tag (au minimum
`v1` ou `v1.0.0`). Si non, **arrêter et inviter à invoquer
`dx_intermediate_create_cicd_repo`**.

## Paramètres requis

- Liste des APIs du projet (nom + tier B4F/Backend)
- Liste des environnements (toujours `dev`, `staging`, `prod` — pas `production`)
- Version du repo central à pinner (typiquement `v1`)

## Workflow

### 1. `.gitlab-ci.yml` du projet

```yaml
include:
  - project: 'croo-dev/ci-cd-unified-template-v1.0'
    ref: v1
    file: '/templates/parent.yml'
```

C'est tout. Aucun stage, aucun job, aucun script.

### 2. Values Helm par environnement et par API

Pour chaque API × {dev, staging, prod} :

`deploy/values/<env>/<api>.yaml` avec :
- `serviceName: <api>`
- `apiTier: backend | b4f` (le chart conditionne l'ingress et l'initContainer migrate)
- `image:` (résolu au runtime via tag)
- `replicas:` (1 en dev, 2+ en prod)
- `resources:`
- Probes (cf. § 5.10) — typiquement déjà dans le chart, override possible
- Variables OTel injectées par le chart (cf. § 5.8)

### 3. Variables CI/CD GitLab requises

Lister explicitement ce qui doit être configuré (cf. § 5.5 et § 7.5).
Produire en sortie la table :

```markdown
| Variable | Scope | Type | À configurer où |
|---|---|---|---|
| NAMESPACE | global | Variable | Settings > CI/CD > Variables |
| NAMESPACE | staging | Variable | ... |
| ... | ... | ... | ... |
```

L'agent **ne crée pas** les variables (pas d'accès à l'admin GitLab) — il
produit la table.

### 4. Convention namespace `<projet>-<env>`

Ex. projet `asq` : namespaces `asq-dev`, `asq-staging`, `asq-prod`. Le namespace
prod n'est **jamais** juste `asq` (§ 5.3).

### 5. Wildcard TLS

Le chart du repo central supporte les deux modes (wildcard vs spécifique). Pas
de manipulation côté projet : c'est le pipeline qui détecte et copie le
wildcard si dispo (§ 5.7).

## Base skills

- `dx_base_create_cicd_minimal_gitlab_yml`
- `dx_base_create_cicd_minimal_gitlab_yml_canonical` — version v1.2+ (un seul include)
- `dx_base_create_cicd_migrate_project_includes` — migration v1.1 → v1.2 (suppression du 2e include)
- `dx_base_create_cicd_values_per_env_per_api`
- `dx_base_create_cicd_variables_table`

## Anti-patterns

1. Inliner un stage `script:` dans le `.gitlab-ci.yml` du projet
2. `include: ref: main` (instabilité)
3. Réutiliser des values d'un autre projet sans relire les contraintes
4. Renommer un environnement (toujours dev/staging/prod)
5. **Ajouter un 2e include pour `kaniko.yml`** — chargé par parent.yml depuis v1.2
6. **Référencer `infrastructure/ci-templates`** — n'existe plus depuis v1.2, tout est dans `croo-dev/ci-cd-unified-template-v1.0`
