---
description: "Implémenter une nouvelle feature ou modifier une feature existante"
---

# /feature — Nouvelle feature ou modification

// turbo-all

## Étape 1 — Clarification de la feature

Poser ces questions :

1. **Quoi ?** Décris la feature en une phrase
2. **Quel type ?**

| # | Type | Description | Exemples |
|---|------|-------------|----------|
| 1 | **Ajout UI** | Nouveau composant, bouton, page | Badge, dialog, card, onglet |
| 2 | **Modification UI** | Changer un composant existant | Ajouter une colonne, modifier un formulaire |
| 3 | **Ajout backend** | Nouvel endpoint, service, logique | Endpoint d'export, calcul métier |
| 4 | **Modification backend** | Changer une route, un modèle | Ajouter un champ, modifier un filtre |
| 5 | **Full-stack** | Backend + Frontend ensemble | Nouveau CRUD → utiliser `/nouveau-module` |

3. **Où ?** Quels fichiers/modules sont touchés ?

---

## Étape 2 — Recherche de template

Chercher dans `templates/code/` si un template existe pour ce type de travail :

```
templates/code/
├── backend/
│   ├── model-sqlalchemy/        ← Ajouter un modèle ?
│   ├── schemas-pydantic/        ← Ajouter des schemas ?
│   ├── router-crud/             ← Nouveau router CRUD ?
│   ├── router-action/           ← Endpoint spécifique ?
│   └── service-domain/          ← Service logique métier ?
│
├── frontend/
│   ├── model-typescript/        ← Nouvelle interface ?
│   ├── service-http/            ← Nouveau service HTTP ?
│   ├── store-ngrx/              ← Nouveau store ?
│   ├── page-list/               ← Page liste ?
│   ├── page-detail/             ← Page détail ? ⚠️ UNRULED
│   ├── component-badge/         ← Badge de statut ?
│   ├── component-dialog/        ← Dialog de confirmation ?
│   └── component-card/          ← Card ? ⚠️ UNRULED
│
└── fullstack/
    ├── crud-module/             ← Module CRUD complet ?
    └── feature-action/          ← Action spécifique ? ⚠️ UNRULED
```

---

## Étape 3 — Rule-Gap Analysis

Catégoriser chaque action nécessaire :

### Actions RULED ✅ (template trouvé)
| Action | Template source |
|--------|----------------|
| [action] | [chemin du template] |

### Actions UNRULED ⚠️ (pas de template)
| Action | Ce que le LLM fera seul | Gap à combler |
|--------|-------------------------|---------------|
| [action] | [décision LLM] | [type de template manquant] |

> **Si UNRULED détecté** : ajouter dans `docs/missing-templates.md`

---

## Étape 4 — Présentation de la route HDQ

Présenter à l'utilisateur :

```
📋 Route HDQ — [titre feature]

RULED ✅ (templates suivis) :
  • [action 1] → templates/code/backend/router-crud/
  • [action 2] → templates/code/frontend/page-list/

UNRULED ⚠️ (pas de template — LLM décide) :
  • [action 3] — Raison : pas de template pour [X]
  • [action 4] — Raison : logique métier spécifique

Étapes estimées : [N]
Workflow : /feature → /implante ([N] étapes) → /overview × [N] → /consolidation
```

---

## Étape 5 — Approbation

> ✅ **Approuves-tu cette route ?** (oui / ajuster)

Si oui → déclencher `/implante` avec le plan généré.

---

## Étape 6 — Exécution

Pour chaque action **RULED** :
- Ouvrir le `TEMPLATE.md` correspondant
- Suivre les instructions **pas-à-pas**
- Le code est **dicté** par le template

Pour chaque action **UNRULED** :
- Le LLM code selon son meilleur jugement
- **Signaler clairement** : "⚠️ Pas de template pour cette action"
- Appliquer les règles générales (`context/projet.md`)

Déclencher `/implante` pour la boucle Code → Test → /overview → Commit.
