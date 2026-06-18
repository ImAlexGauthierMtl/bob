---
name: dx_master_check
description: Produit un rapport pass/fail complet de conformité aux règles d'architecture & déploiement, au format du § 9 de la doc. À invoquer quand l'utilisateur demande "vérifie la conformité", "check architecture", "valide le projet contre les règles", "fais le rapport de revue", "le projet est-il conforme". Délègue aux skills intermediate check, en parallèle. Sortie format markdown structuré, prêt à coller dans une MR.
metadata:
  version: 1.0.0
  source: code-agent-skills-v1.0
  reference: docs/architecture/regles-architecture-deploiement.md
---

# dx_master_check — Rapport de conformité

## Rôle

Produire un **verdict** (pass/fail par règle, classifié par criticité) au format
décrit dans la doc § 9 « Format de rapport de revue ». Cible : reviewer humain
ou ingénieur d'astreinte.

Différence avec `dx_master_analyse` :
- `analyse` = diagnostic neutre, exploratoire
- `check` = jugement contre une checklist (§ 8 de la doc)

## Avant de commencer

1. Disposer de la checklist § 8 de `docs/architecture/regles-architecture-deploiement.md`.
2. Repérer l'arborescence et identifier les sections applicables (cf.
   `dx_master_analyse` étape 1).
3. **Ne pas inventer de règle** : si quelque chose n'est pas dans § 8, ne pas en
   faire un point de conformité.

## Workflow d'orchestration

Comme `dx_master_analyse`, **paralléliser par chapitre** via la `task` tool.

### Skills intermediate à invoquer

- `dx_intermediate_check_apis`
- `dx_intermediate_check_frontend_ngrx`
- `dx_intermediate_check_cicd_pipeline`
- `dx_intermediate_check_k8s_config`
- `dx_intermediate_check_env_vars`
- `dx_intermediate_check_registry_to_k8s`
- `dx_intermediate_check_project_conventions`
- `dx_intermediate_check_local_dev`
- `dx_intermediate_check_clean_archi_apis`
- `dx_intermediate_check_cicd_repo` (seulement si on audite le repo partagé)
- `dx_intermediate_check_frontend_clean_archi`

Chaque intermediate retourne :
- liste des points conformes
- liste des violations avec criticité (`critique` / `à corriger`)
- pour chaque violation : numéro de section de la doc + ligne / fichier précis

### Synthèse au format § 9

```markdown
## Revue Architecture & Déploiement

### Architecture APIs
- OK : <points conformes>
- VIOLATION (critique, § X.Y) : <description précise> — fichier <path:line>
- VIOLATION (à corriger, § X.Y) : ...

### Frontend NGRX
...

### Pipeline CI/CD
...

### Configuration K8s
...

### Scoping variables
...

### Registry → K8s
...

### Conventions projet
...

### Observabilité
...

### Développement local
...

### Structure interne (Clean Archi + SOLID)
...

### Repo cicd-templates
...

### Frontend Clean Architecture
...

### Résumé
- Violations critiques : X
- Violations à corriger : Y
- Points conformes : Z

### Variables CI/CD à créer/modifier dans GitLab
| Variable | Scope | Valeur attendue |
|---|---|---|
| ... | ... | ... |
```

## Critères de criticité

- **Critique** : viole une règle qui impacte la sécurité, la stabilité prod, ou
  la possibilité même de déployer. Exemples : DDL au startup, B4F qui accède à
  la DB, kubeconfig hardcodé en variable string, pas de scan Trivy, deploy auto
  staging/prod, tag `latest` en prod.
- **À corriger** : viole une règle de bonne pratique sans risque immédiat.
  Exemples : doc éparpillée hors `/docs`, README sans badge coverage, fichier
  `.cursorrules` traînant, nom d'env `production` au lieu de `prod`.

## Posture recommandée

Cette skill est **read-only**. Si l'agent dispose d'un mode lecture
seule / plan, l'utiliser. Aucune correction pendant le check — c'est
le rôle des skills `create` après revue du rapport.

## Anti-patterns

1. **Verdict sans citation** — chaque violation doit citer la section de la doc.
2. **Inventer des règles** — strict respect de § 8.
3. **Diluer** — pas de "globalement conforme", c'est pass ou fail par règle.
4. **Faire en séquentiel** quand les subagents sont disponibles.
5. **Sauter la table « Variables CI/CD à créer/modifier »** — elle est exigée
   par le format § 9.
