---
description: "Vérification visuelle Playwright obligatoire pour tout changement frontend"
---

# Règle — Playwright Auto-Vérification

> [!CAUTION]
> **OBLIGATOIRE** : Tout changement touchant le frontend doit être vérifié visuellement avec Playwright avant le commit.

## Déclencheur

Un changement est considéré comme **touchant le frontend** si l'un de ces fichiers est modifié :

- `frontend/src/app/**/*.html`
- `frontend/src/app/**/*.ts`
- `frontend/src/app/**/*.css`

## Commande

```bash
# Vérifier les pages touchées
// turbo
node frontend/playwright-verify.js /dashboard /contacts

# Vérifier toutes les pages principales
// turbo
node frontend/playwright-verify.js
```

## Critères de succès

- Exit code = 0
- Aucune page ne redirige vers `/login`
- Aucun crash ou timeout
- Les screenshots sont cohérents visuellement (pas de page blanche, pas de layout cassé)

## Intégration dans les workflows

Cette règle est référencée dans :
- `/implante` — Phase B (après tests unitaires)
- `/fix` — Étape 4 (après correction)
- `/refactor` — Étape 5 (vérification finale)
- `/consolidation` — Étape 4 (conformité)
- `/overview` — Ω₅ (qualité)

## Outils

| Fichier | Rôle |
|---------|------|
| `frontend/playwright-helper.js` | Module réutilisable (login, navigateTo, openBob, etc.) |
| `frontend/playwright-verify.js` | Script de vérification rapide par page |
| `frontend/test-bcc-wizard.js` | Test spécifique BCC + Bob wizard |
| `frontend/capture.js` | Captures Zoho ticket |

## Règle de navigation

> **JAMAIS `page.goto()` après le login.** Utiliser `navigateTo()` du helper qui clique les `routerLink` Angular (navigation SPA sans reload).
