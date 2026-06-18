---
name: dx_intermediate_create_frontend_ngrx
description: Crée le squelette d'un frontend Angular + NGRX conforme au chapitre 3, ou ajoute une nouvelle feature de store (actions/reducer/effects/selectors + service par B4F). Met aussi en place les tests E2E Playwright dans frontend/e2e et le hook git pre-commit husky pour les tests @smoke. À invoquer pour bootstrap frontend ou pour ajouter une feature.
metadata:
  reference: § 3 de docs/architecture/regles-architecture-deploiement.md
---

# dx_intermediate_create_frontend_ngrx

## Modes de fonctionnement

1. **Bootstrap complet** : créer le squelette `frontend/src/app/` avec `store/`,
   `services/`, `pages/`, `components/` + Playwright dans `frontend/e2e/`
2. **Ajouter une feature** : créer un nouveau feature de store + service Angular
   pour une B4F nouvelle ou existante

## Paramètres requis

- Nom de feature (kebab-case, ex. `rooms`, `clients`)
- B4F cible (URL ou nom de service, ex. `rooms-b4f-api`)
- Bootstrap complet ou ajout ?

## Workflow

### Bootstrap

1. `ng new frontend` ou structure équivalente
2. Installer `@ngrx/store`, `@ngrx/effects`, `@ngrx/store-devtools`
3. Créer `store/index.ts` (root)
4. Configurer ESLint avec les `no-restricted-imports` qui bloquent `@angular/*`,
   `@ngrx/*`, `rxjs` dans `domain/` et `application/` (cf. § 14 et le template
   dans `cicd-templates/lint/eslintrc-template.js`)
5. Créer `frontend/e2e/` avec `playwright.config.ts`, un test `auth.spec.ts`
   minimal tagué `@smoke`
6. Configurer husky : `frontend/package.json` avec script
   `test:e2e:changed` qui invoque `playwright test --grep @smoke`
7. Créer `scripts/pre-commit-frontend.sh` qui détecte les changements
   `frontend/` et lance les `@smoke`
8. Créer `frontend/api.config.ts` (ou équivalent) avec **uniquement** des URLs
   `*-b4f-api`

### Ajouter une feature

Pour la feature `<feature>`, créer en parallèle :

| Subagent | Fichier |
|---|---|
| 1 | `services/<feature>.service.ts` (HttpClient vers B4F) |
| 2 | `store/<feature>/<feature>.actions.ts` (load/success/failure) |
| 3 | `store/<feature>/<feature>.reducer.ts` |
| 4 | `store/<feature>/<feature>.effects.ts` (appelle le service) |
| 5 | `store/<feature>/<feature>.selectors.ts` |

Puis :
6. Enregistrer le reducer dans `store/index.ts`
7. Enregistrer les effects dans `provideEffects()`

## Base skills

- `dx_base_create_frontend_feature_full`
- `dx_base_create_frontend_e2e_test_skeleton`
- `dx_base_create_frontend_husky_pre_commit`

## Anti-patterns

1. **Injecter un service dans un component** — viole § 3.6.
2. **Mettre une URL `*-backend-api` dans la config** — interdit (§ 2.9).
3. **Tests E2E dans `frontend/src/`** — toujours dans `frontend/e2e/`.
4. **Tests E2E dans le pipeline CI** — manuel uniquement (§ 3.8).
5. **Pre-commit qui lance la suite complète** — utiliser `@smoke`.
