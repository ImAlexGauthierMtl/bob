---
description: "Corriger un bug — diagnostic structuré avant correction"
---

# /fix — Correction de bug

// turbo-all

## Étape 1 — Qualification du bug

1. **Quoi ?** Décris le symptôme (pas la cause)
2. **Où ?** Backend, frontend, intégration, les deux ?
3. **Depuis quand ?** Régression récente ou bug existant ?
4. **Ticket Zoho ?** Si oui, quel numéro → peut déclencher `/zoho` pour contexte
5. **Reproductible ?** Toujours, parfois, une seule fois ?

---

## Étape 2 — Diagnostic

### 2a. Localiser le bug

```bash
# Voir les commits récents (si régression)
git log --oneline -10

# Chercher dans le code
grep -rn "mot_clé" backend/ frontend/src/

# Vérifier les logs
# Backend
tail -50 backend/logs/app.log

# Frontend
# Console du navigateur
```

### 2b. Identifier la couche touchée

| Couche | Fichiers typiques | Comment vérifier |
|--------|-------------------|-----------------|
| **Route/API** | `routers/*.py` | Tester avec curl/Postman |
| **Logique métier** | `services/*.py` | Test unitaire isolé |
| **Base de données** | `models.py`, migrations | Vérifier le schéma |
| **Frontend service** | `services/*.service.ts` | Console réseau |
| **Frontend composant** | `pages/*.page.ts` | Inspecter le DOM |
| **Store NGRX** | `store/*.ts` | Redux DevTools |

### 2c. Formuler une hypothèse

> "Le bug est causé par [X] dans [fichier] parce que [Y]"

---

## Étape 3 — Recherche de template

Le fix touche-t-il un pattern couvert par un template ?

- Si le fix implique de **recréer** un composant → utiliser le template correspondant
- Si le fix est un **ajustement** → pas besoin de template, mais vérifier les règles

---

## Étape 4 — Correction

1. **Écrire le test qui expose le bug** (RED)
```bash
# Le test DOIT échouer avant la correction
python -m pytest tests/test_{module}.py::test_{bug_case} -v
```

2. **Corriger le code** (GREEN)

3. **Vérifier que le test passe** (REFACTOR)
```bash
python -m pytest tests/test_{module}.py -v
```

4. **Si frontend touché → Playwright auto-vérification** (voir `rules/regle-playwright.md`)
```bash
// turbo
node frontend/playwright-verify.js [pages du bug]
```

5. **Vérifier qu'aucune régression n'est introduite**
```bash
python -m pytest tests/ -v --tb=short
```

---

## Étape 5 — Commit

```bash
git add -A
git commit -m "[service] fix: description du bug corrigé

Ref: ZOHO-#XXXXX (si applicable)"
```

Déclencher `/overview` pour vérification, puis `/consolidation`.
