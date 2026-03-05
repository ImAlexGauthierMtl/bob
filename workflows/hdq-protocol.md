---
description: "Protocole de collaboration HDQ Omega — cycle Explorer → Construire → Consolider"
---

# Protocole HDQ Omega

Ce document définit le cycle de travail pour chaque feature ou tâche significative.

## Pré-requis

Avant de commencer, lire :
1. `.agents/context/projet.md` — le Ω:CONTEXT du projet
2. `.agents/rules/architecture.md` — règles fondamentales
3. `.agents/decisions/decisions.md` — les décisions architecturales actives

## Phase 1 — Explorer (désorganisation contrôlée)

1. Écouter le besoin en langage naturel
2. Poser des questions de clarification
3. Reformuler pour exposer les contradictions ou ambiguïtés
4. Identifier les vrais enjeux vs. les faux problèmes
5. Produire un artifact `exploration.md` si le besoin est complexe

## Phase 1.5 — Revue Architecturale

1. Se demander : *"Cette approche respecte-t-elle l'architecture définie ?"*
2. Vérifier contre `.agents/rules/architecture.md`
3. Produire formellement l'avis critique *avant* de soumettre le plan final

> Note : L'usage des commandes `/delta` ou `/big` déclenche automatiquement cette phase.

## Phase 2 — Construire (stabilisation assistée)

1. Rédiger un `implementation_plan.md` avec diffs précis
2. Soumettre le plan pour approbation
3. Implémenter itérativement — tester chaque composant
4. Mettre à jour le `task.md` au fur et à mesure
5. **100% coverage** obligatoire avant de passer à la phase 3

## Phase 3 — Consolider (structuration réflexive)

1. Vérifier le bon fonctionnement (tests, build, pipeline CI/CD)
2. Produire un `walkthrough.md` avec preuves
3. Mettre à jour `decisions.md` si une décision architecturale a été prise
4. Mettre à jour `context/projet.md` si la stack ou les intégrations ont changé
5. Commiter avec le format `[service] type: description`

## Signaux de transition

- **Explorer → Construire** : Le besoin est clair, l'architecture validée
- **Construire → Explorer** : Complexité imprévue, besoin de re-clarifier
- **Construire → Consolider** : 100% tests, code fonctionne, pipeline vert
- **Consolider → Explorer** : Le test révèle un problème fondamental
