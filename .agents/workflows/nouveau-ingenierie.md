---
description: "Travail exploratoire, R&D, ou décision architecturale complexe"
---

# /nouveau-ingenierie — Exploration & R&D

Ce workflow est déclenché depuis `/start` quand la demande est exploratoire ou nécessite une réflexion architecturale.

---

## Étape 1 — Clarifier l'objectif

Poser les questions suivantes :

| # | Question |
|---|----------|
| 1 | **Objectif** : Que cherches-tu à comprendre ou résoudre ? |
| 2 | **Contexte** : Qu'est-ce qui a mené à cette question ? |
| 3 | **Contraintes connues** : Stack, budget, timeline, compatibilité ? |
| 4 | **Hypothèses** : Quelles pistes as-tu déjà envisagées ? |
| 5 | **Livrable attendu** : Décision ? Prototype ? Documentation ? |

---

## Étape 2 — Classifier le type d'exploration

| Type | Critère | Workflow déclenché |
|------|---------|-------------------|
| **Décision architecturale** | Choix entre 2+ approches incompatibles | → `/big` (thèse/antithèse) |
| **Recherche technique** | Comprendre un outil, une API, un pattern | → Artifact `exploration.md` |
| **Prototypage** | Tester une hypothèse avec du code | → `/implante` léger (sans /overview) |
| **Audit** | Évaluer l'état d'un module existant | → Rule-Gap Analysis étendu |

---

## Étape 3 — Recherche structurée

Si **recherche technique** :

1. Rechercher dans les KI Antigravity (knowledge items existants)
2. Rechercher dans les case studies du framework (`docs/case-studies/`)
3. Explorer le codebase et la documentation externe
4. Produire un artifact `exploration.md` avec :
   - Contexte et besoin
   - Options identifiées (avec avantages/inconvénients)
   - Recommandation
   - Prochaines étapes

---

## Étape 4 — Formaliser

Si une **décision** a été prise :
- Ajouter une entrée dans `.agents/decisions/decisions.md` (format ADR)
- Mettre à jour `context/projet.md` si la stack ou l'architecture change

Si un **gap** a été identifié :
- Logger dans `.agents/docs/gaps.md`
