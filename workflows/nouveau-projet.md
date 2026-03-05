---
description: "Bootstrap un nouveau projet avec la structure .agents/ HDQ complète"
---

# /nouveau-projet — Bootstrap Projet HDQ

// turbo-all

Ce workflow est déclenché depuis `/start` quand on crée un nouveau projet from scratch.

---

## Étape 1 — Questionnaire projet

Poser les questions suivantes :

| # | Question | Exemple |
|---|----------|---------|
| 1 | **Nom du projet** | Le Baluchon |
| 2 | **Domaine** | Hôtellerie, CRM, ERP, SaaS... |
| 3 | **Stack backend** | FastAPI + PostgreSQL / autre |
| 4 | **Stack frontend** | Angular 20+ / autre |
| 5 | **Architecture** | Monorepo / Micro-services / BFF / Simple API |
| 6 | **Repo GitLab** | URL du repo |
| 7 | **Intégrations externes** | Zenoti, IQware, Zoho, Stripe... |
| 8 | **Environnements** | Dev, staging, prod — URLs |

---

## Étape 2 — Copier le framework

```bash
cp -r ~/Dev/framework/framework-hdq/ .agents/
rm -rf .agents/.git
```

---

## Étape 3 — Générer context/projet.md

À partir des réponses, remplir le template `context/projet.template.md` :
- Identité du projet
- Stack technique (tableau)
- Architecture (diagramme)
- APIs actives (tableau avec ports)
- Intégrations externes
- Environnements
- Conventions

Sauvegarder dans `.agents/context/projet.md`.

---

## Étape 4 — Initialiser les fichiers projet

1. Créer `.agents/decisions/decisions.md` avec le premier ADR :
   ```markdown
   # ADR-001 — Structure .agents/ HDQ
   - **Date** : [DATE_ISO]
   - **Status** : Accepté
   - **Decision** : Adoption du framework HDQ pour la collaboration IA
   - **Rationale** : Standardisation des normes, workflows, et skills
   ```

2. Créer `.agents/docs/gaps.md` (vide, avec header)
3. Créer `HDQ.md` à la racine du projet (copier le template)

---

## Étape 5 — Commit initial

```bash
git add .agents/ HDQ.md
git commit -m "[project] chore: initialize HDQ framework structure"
```

---

## Étape 6 — Confirmer

Afficher la structure créée et confirmer avec l'utilisateur.
