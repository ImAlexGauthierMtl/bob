---
description: "Protocole d'implémentation structuré avec /overview et /delta intégrés à chaque étape"
---

# /implante — Implémentation Structurée

// turbo-all

Ce workflow structure l'implémentation d'un plan approuvé en étapes atomiques avec des checkpoints intégrés.

> [!CAUTION]
> **RÈGLE ABSOLUE** : Ne jamais passer à l'étape suivante sans avoir complété le /overview de l'étape courante.

---

## Pré-requis

- Un `implementation_plan.md` approuvé doit exister
- La branche git doit être à jour

```bash
git branch --show-current
git status --short
```

---

## Boucle d'implémentation

Pour **chaque étape** du plan, exécuter dans l'ordre :

### Phase A — Implémentation

1. **Annoncer l'étape** : Mettre à jour `task.md` avec `[/]` sur l'item courant
2. **Coder** : Implémenter l'étape selon le plan
3. **Pas de code sans test** : Écrire les tests associés à l'étape

### Phase B — Vérification technique

4. **Exécuter les tests** de l'étape :
```bash
# Backend Python
python -m pytest tests/ -v --tb=short 2>&1 | tail -30

# Frontend Angular
npx ng test --watch=false --browsers=ChromeHeadless 2>&1 | tail -30
```

5. **Si frontend touché → Playwright auto-vérification** (voir `rules/regle-playwright.md`) :
```bash
// turbo
node frontend/playwright-verify.js [pages touchées]
```
> [!IMPORTANT]
> Ne JAMAIS skip cette étape. L'auto-vérification visuelle est obligatoire pour tout changement frontend.

6. **Vérifier les imports et la syntaxe** :
```bash
# Backend
python -c "import app; print('OK')"

# Frontend
npx ng build --configuration=development 2>&1 | tail -20
```

6. Si un test échoue → **corriger avant de continuer** (boucle debug)

### Phase C — /overview (vue d'altitude)

7. **Déclencher /overview** : exécuter le workflow `/overview` complet
   - Bilan d'étape (Σ)
   - 5 questions Ω (cohérence, scope, dépendances, risques, qualité)
   - Verdict : CONTINUE / CORRIGER / Δ-STOP

8. **Si verdict = CONTINUE** → passer à l'étape suivante
9. **Si verdict = CORRIGER** → corriger puis re-/overview
10. **Si verdict = Δ-STOP** → exécuter `/delta` complet, notifier l'utilisateur

### Phase D — Commit atomique

11. **Commiter l'étape** avec message sémantique :
```bash
git add -A
git commit -m "[service] type: description de l'étape"
```

---

## Fin d'implémentation

Une fois toutes les étapes complétées :

1. **Exécuter tous les tests** :
```bash
# Backend
python -m pytest tests/ -v --cov

# Frontend
npx ng test --watch=false --code-coverage
```

2. **Déclencher /consolidation** : walkthrough, dette technique, conformité

3. **Push et notifier l'utilisateur** :
```bash
git push origin $(git branch --show-current)
```

---

## Résumé visuel

```
Pour chaque étape du plan :

  ┌─────────────────────────┐
  │  A. Implémenter + Tests │
  └───────────┬─────────────┘
              ▼
  ┌─────────────────────────┐
  │  B. Debug (tests pass?) │──── NON ──→ Fix & retry
  └───────────┬─────────────┘
              ▼ OUI
  ┌─────────────────────────┐
  │  C. /overview (Ω₁-Ω₅)  │──── CORRIGER ──→ Fix & re-overview
  └───────────┬─────────────┘──── Δ-STOP ──→ /delta complet
              ▼ CONTINUE
  ┌─────────────────────────┐
  │  D. Commit atomique     │
  └───────────┬─────────────┘
              ▼
        Étape suivante
```
