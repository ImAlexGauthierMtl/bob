---
description: "Forcer l'arrêt et la réflexion (Δ-point) sur une tâche d'implémentation"
---

# /delta — Protocole Δ-point

// turbo-all

Ce workflow force l'arrêt et une réflexion approfondie avant de continuer.

---

## Niveau 1 — Signaux de déclenchement (σ : QUAND s'arrêter)

- **σ₁ — ABSTRACTION_FRACTURE** : Un concept réel est devenu abstrait sans ancrage vérifié (ex: "déployer", "migrer", "appeler l'API" sans vérifier le chemin réel)
- **σ₂ — IMPLICIT_STACK_OVERFLOW** : Plus de 3 hypothèses non vérifiées empilées
- **σ₃ — THIRD_THOUGHT_SILENCE** : Plus de 50 lignes produites sans projection dans l'espace de l'autre

---

## Niveau 2 — Dimensions d'inspection (Ψ : QUOI vérifier)

1. **Ψ₁ — IMPLICITES** : Lister toutes les hypothèses cachées. Pour chacune : vérifiée empiriquement ou supposée ?

2. **Ψ₂ — USE CASE WALK** : Simuler le parcours complet de l'usager :
   - Usager fait X → Frontend (quel composant ?) → API (quelle route ?) → auth (JWT valide ?) → backend (quelle logique ?) → DB (quel schéma ?) → réponse → UI
   - À chaque flèche : *"ai-je vérifié que cette frontière existe et fonctionne ?"*

3. **Ψ₃ — STACK LAYERS** : Vérifier chaque couche touchée :
   - Backend : routes, use cases, services, repositories, schéma DB
   - Frontend : composants, services HTTP, modèles TypeScript
   - Intégrations : Les services externes sont-ils mockés ou réels ?

4. **Ψ₄ — NORM GATE** : Respecte-t-on les règles ?
   - `.agents/rules/architecture.md`
   - `.agents/rules/backend-python.md`
   - `.agents/rules/testing.md`
   - Conventions nommage, isolation données

5. **Ψ₅ — CI GATE** : Le code passera-t-il le pipeline ?
   - Tests : coverage maintenu ?
   - Migrations : à jour ?
   - Build : valide ?

---

## Revue Architecturale Simulée

*"Cette approche viole-t-elle l'architecture définie dans context/projet.md ?"*
*"Le frontend appelle-t-il directement un service qu'il ne devrait pas ?"*
*"Les données sont-elles bien isolées ?"*

---

## Documentation du Δ

Ajouter une entrée dans `.agents/docs/delta-log.md` (créer si inexistant) :

```markdown
## Δ.[N] | [TYPE].[TITRE] | [DATE_ISO]

σ_trigger: [σ₁ / σ₂ / σ₃ — lequel a déclenché ce Δ]

Ψ₁_implicites { [hypothèses cachées] }
Ψ₂_use_case_walk { [parcours usager complet] }
Ψ₃_stack_layers { [couches touchées] }
Ψ₄_norm_gate { [conformité règles : OK / WARNING / FAIL] }
Ψ₅_ci_gate { [tests, coverage, migrations, pipeline] }

⊳ corrections: [ajustements apportés]
⊳ outcome: [résultat après corrections]
```
