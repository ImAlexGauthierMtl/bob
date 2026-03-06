---
description: "Ajouter un module backend + frontend à un projet existant"
---

# /nouveau-module — Ajout de Module

// turbo-all

Ce workflow est déclenché depuis `/start` quand on ajoute un module à un projet existant.

---

## Étape 1 — Questionnaire module

Poser les questions suivantes :

| # | Question | Exemple |
|---|----------|---------|
| 1 | **Nom de la ressource** (singulier) | Reservation, Voucher, Contact |
| 2 | **Champs principaux** | nom, date, montant, statut... |
| 3 | **Relations** | Appartient à Company, a plusieurs LineItems... |
| 4 | **Endpoints nécessaires** | CRUD complet, filtres, recherche... |
| 5 | **Logique métier spécifique** | Calculs, validations, workflows... |
| 6 | **UI nécessaire** | Liste, détail, formulaire, dashboard... |

---

## Étape 2 — Rule-Gap Analysis

Exécuter l'analyse Rule-Gap (voir `/start` étape 4) spécifiquement pour :

- **Backend** : skill `backend-python` couvre-t-il le pattern ?
- **Frontend** : skill `frontend-angular` couvre-t-il les composants demandés ?
- **Testing** : skill `testing` couvre-t-il les cas ?
- **Domaine** : existe-t-il des normes métier pour cette ressource ?

---

## Étape 3 — Générer le plan d'implémentation

Utiliser le skill `implementation-planning` pour produire un `implementation_plan.md` structuré :

1. **Contexte & logique métier**
2. **Database & modèle de domaine** (SQLAlchemy)
3. **Backend** (schemas → repository → service → use cases → routes)
4. **Frontend** (models → service → NGRX store → composants UI)
5. **Tests** (positifs + 30% négatifs)
6. **Checklist HDQ**

Soumettre le plan pour approbation.

---

## Étape 4 — Déclencher /implante

Une fois le plan approuvé, déclencher le workflow `/implante` pour l'implémentation structurée.
