---
description: "Refactoring structuré — améliorer le code sans changer le comportement"
---

# /refactor — Refactoring structuré

// turbo-all

## Étape 1 — Qualification

1. **Quoi ?** Qu'est-ce qui doit être refactoré ?
2. **Pourquoi ?** Dette technique, lisibilité, performance, conformité aux normes ?
3. **Risque ?** Quel est le risque de régression ?
4. **Scope ?** Combien de fichiers touchés ?

---

## Étape 2 — Sécurité avant refactoring

**AVANT de toucher au code :**

```bash
# S'assurer que les tests passent AVANT
python -m pytest tests/ -v --tb=short 2>&1 | tail -20

# Frontend
npx ng build --configuration=development 2>&1 | tail -10
```

> Si les tests ne passent pas AVANT → corriger les tests d'abord (/fix)

---

## Étape 3 — Plan de refactoring

Lister les changements prévus :

| # | Fichier | Action | Risque |
|---|---------|--------|--------|
| 1 | [fichier] | [extraction, renommage, split, merge] | [LOW/MED/HIGH] |

---

## Étape 4 — Exécution

Pour chaque changement :
1. Faire le changement
2. Exécuter les tests → doivent toujours passer
3. Commiter atomiquement

```bash
git add -A
git commit -m "[service] refactor: description"
```

## Étape 5 — Vérification finale

```bash
# Tous les tests doivent passer exactement comme avant
python -m pytest tests/ -v --tb=short
```

**Si frontend touché → Playwright auto-vérification** (voir `rules/regle-playwright.md`) :
```bash
// turbo
node frontend/playwright-verify.js [pages refactorées]
```

Déclencher `/overview` puis `/consolidation`.
