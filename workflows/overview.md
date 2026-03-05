---
description: "Vue d'altitude forcée — Δ-point systématique à chaque étape d'implémentation"
---

# /overview — Vue d'Altitude

// turbo-all

Ce workflow force un Δ-point en altitude : une prise de recul sur le travail accompli et à venir.

---

## Quand déclencher

- **Automatiquement** : à la fin de chaque étape dans un `/implante`
- **Manuellement** : quand on veut une vue d'ensemble avant de continuer

---

## Étapes obligatoires

### 1. Bilan d'étape (Σ — ce qui est fait)

Faire un inventaire des fichiers touchés :
```bash
git diff --stat HEAD
git status --short
```

Résumer en une phrase : **"J'ai fait X, Y, Z."**

### 2. Δ-altitude (Ω — vue du dessus)

Se poser les questions suivantes — répondre à chacune en **une ligne** :

| # | Question | Réponse |
|---|---|---|
| Ω₁ | **Cohérence** : Ce que j'ai construit est-il cohérent avec l'objectif global ? | |
| Ω₂ | **Scope** : Ai-je dérivé du scope ? Ai-je ajouté des choses non demandées ? | |
| Ω₃ | **Dépendances** : L'étape suivante dépend-elle de quelque chose que je n'ai pas fait ? | |
| Ω₄ | **Risques** : Qu'est-ce qui pourrait casser ? (tests, imports circulaires, migrations) | |
| Ω₅ | **Qualité** : Le code livré est-il testable, lisible, et conforme aux normes du projet ? | |

### 3. Validation ou correction

- Si toutes les réponses Ω sont **OK** → passer à l'étape suivante
- Si un Ω est **WARNING** → corriger avant de continuer
- Si un Ω est **FAIL** → déclencher un `/delta` complet

### 4. Mise à jour du task.md

Marquer l'étape comme `[x]` et mettre à jour le statut de l'étape suivante `[/]`.

---

## Format de sortie

```
## Overview | [ÉTAPE] | [DATE_ISO]

Σ_bilan: [résumé une phrase]

| Ω₁ cohérence    | ✅/⚠️/❌ — [détail] |
| Ω₂ scope        | ✅/⚠️/❌ — [détail] |
| Ω₃ dépendances  | ✅/⚠️/❌ — [détail] |
| Ω₄ risques      | ✅/⚠️/❌ — [détail] |
| Ω₅ qualité      | ✅/⚠️/❌ — [détail] |

⊳ verdict: [CONTINUE / CORRIGER / Δ-STOP]
⊳ next: [prochaine étape]
```
