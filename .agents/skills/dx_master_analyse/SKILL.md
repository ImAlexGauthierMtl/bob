---
name: dx_master_analyse
description: Lance une analyse complète d'un projet existant (APIs, frontend, pipeline CI/CD, K8s, conventions, local dev, Clean Architecture) selon les règles d'architecture & déploiement. À invoquer quand l'utilisateur demande "audite mon projet", "analyse l'architecture", "fais un diagnostic", "qu'est-ce qui ne va pas dans ce repo", "où sont les violations". Délègue aux skills intermediate par chapitre, en parallèle quand possible.
metadata:
  version: 1.0.0
  source: code-agent-skills-v1.0
  reference: docs/architecture/regles-architecture-deploiement.md
---

# dx_master_analyse — Analyse architecturale complète

## Rôle

Orchestrer une analyse exhaustive d'un projet existant selon les 14 chapitres de
`docs/architecture/regles-architecture-deploiement.md`. Produire un diagnostic
structuré, **pas** un rapport pass/fail (c'est le rôle de `dx_master_check`).

Différence avec `dx_master_check` :
- `analyse` = description neutre de ce qui existe + identification des sujets
  qui méritent attention. Sert à comprendre l'état d'un projet inconnu.
- `check` = verdict pass/fail strict, format du § 9 de la doc. Sert à auditer.

## Avant de commencer

1. Lire `docs/architecture/regles-architecture-deploiement.md` complètement (ou
   au moins les sommaires des chapitres) si l'agent ne l'a pas déjà en contexte.
2. Repérer l'arborescence du projet : `tree -L 3 -a` ou équivalent.
3. Identifier quels chapitres sont applicables. Un projet sans frontend ne
   déclenche pas les intermediate frontend.

## Workflow d'orchestration

Les **chapitres sont indépendants** → paralléliser via subagents.

### Étape 1 — détecter l'applicabilité

Pour chaque chapitre, déterminer si une intermediate doit tourner :

| Chapitre | Applicabilité |
|---|---|
| 2 — APIs | Si `apis/` existe |
| 3 — Frontend NGRX | Si `frontend/` existe |
| 4 — CI/CD | Si `.gitlab-ci.yml` ou pipeline détecté |
| 5 — K8s | Si manifests / `deploy/values/` détectés |
| 6 — Env vars | Toujours (audit variables CI/CD) |
| 7 — Registry → K8s | Si CI/CD avec deploy K8s |
| 10 — Conventions | Toujours (doc, data, outils IA) |
| 11 — Local dev | Toujours (scripts racine, docker-compose, .env) |
| 12 — Clean Archi APIs | Si `apis/` existe |
| 13 — cicd-templates | Uniquement si l'utilisateur audite le repo *partagé* lui-même |
| 14 — Frontend Clean Archi | Si `frontend/` existe |

### Étape 2 — invoquer les intermediate analyse en parallèle

Pour chaque chapitre applicable, **utiliser la `task` tool pour lancer un
subagent qui invoque la skill intermediate correspondante**. Les subagents
travaillent en parallèle sans interférence (chacun a son propre contexte).

Skills à invoquer (sélectionner selon l'applicabilité) :

- `dx_intermediate_analyse_apis`
- `dx_intermediate_analyse_frontend_ngrx`
- `dx_intermediate_analyse_cicd_pipeline`
- `dx_intermediate_analyse_k8s_config`
- `dx_intermediate_analyse_env_vars`
- `dx_intermediate_analyse_registry_to_k8s`
- `dx_intermediate_analyse_project_conventions`
- `dx_intermediate_analyse_local_dev`
- `dx_intermediate_analyse_clean_archi_apis`
- `dx_intermediate_analyse_cicd_repo` (seulement si pertinent)
- `dx_intermediate_analyse_frontend_clean_archi`

**Mode d'invocation préféré** :

```
Lance N subagents en parallèle via la task tool, un par chapitre applicable.
À chacun donne la consigne :
  "Invoque la skill <nom> sur ce projet. Rends un rapport structuré."
Récupère les rapports et synthétise.
```

Si l'agent courant n'a pas accès aux subagents, exécuter séquentiellement, mais
en signalant la limitation dans le rapport final.

### Étape 3 — synthèse

Format de sortie :

```markdown
## Analyse architecturale du projet <nom>

### Vue d'ensemble

<paragraphe court : type de projet, technos détectées, taille>

### Par chapitre

#### Chapitre 2 — APIs
<résumé du diagnostic de dx_intermediate_analyse_apis>

#### Chapitre 3 — Frontend NGRX
...

### Sujets transverses qui méritent attention

- <point #1, ex. "le terme 'authentication' apparaît encore dans 12 fichiers">
- <point #2, ex. "le pipeline n'a pas de stage smoke-test alors que les APIs exposent /health">

### Suggestions de skills pour aller plus loin

- Si tu veux un verdict pass/fail strict → lance `dx_master_check`
- Si tu veux corriger les violations détectées → lance les `dx_intermediate_create_*` ciblées
- Si le sujet est précis (ex. "fixer le pool SQLAlchemy") → invoque directement
  la base skill `dx_base_check_api_db_pool_size`
```

## Posture recommandée

Cette skill est **read-only** : aucun fichier ne doit être modifié pendant
l'analyse. Si l'agent dispose d'un mode lecture seule / plan, l'utiliser.

## Anti-patterns à éviter dans cette analyse

1. **Reformuler la doc** dans le rapport — toujours référencer par numéro de
   section (`cf. § 4.10`).
2. **Émettre un verdict** — ce n'est pas le rôle de `analyse`. Laisser à
   `check` les pass/fail.
3. **Aller au-delà des règles écrites** — si une chose n'est pas dans la doc,
   ne pas la signaler comme "à corriger". Au mieux, la mentionner comme
   observation neutre.
4. **Tout faire séquentiellement** quand les subagents sont disponibles.
