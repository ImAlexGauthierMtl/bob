---
name: dx_intermediate_create_frontend_clean_archi
description: Bootstrap ou refactor une feature Angular en Clean Architecture selon le chapitre 14. À invoquer pour créer features/<feature>/{domain,application,infrastructure,presentation}/ avec un use case d'exemple, un port, son impl HTTP, le store NGRX en infrastructure/store/, des components smart/dumb et l'ESLint no-restricted-imports.
metadata:
  reference: § 14 de docs/architecture/regles-architecture-deploiement.md
---

# dx_intermediate_create_frontend_clean_archi

## Périmètre

Pour une feature `<feature>` (= un B4F, cf. § 3.4), créer :

```
features/<feature>/
├── domain/
│   ├── models/<entity>.model.ts
│   ├── errors/<entity>.errors.ts
│   └── ports/<entity>.repository.ts
├── application/
│   ├── use-cases/{load,book,cancel}-<entity>.use-case.ts
│   └── dtos/
├── infrastructure/
│   ├── api/
│   │   ├── <entity>.http.ts          # implémente Repository via HttpClient
│   │   └── <entity>.dto.ts           # DTO ↔ Model
│   └── store/
│       ├── <entity>.actions.ts
│       ├── <entity>.reducer.ts
│       ├── <entity>.effects.ts       # appelle les use cases
│       └── <entity>.selectors.ts
└── presentation/
    ├── pages/<entity>-list.page.ts   # smart : dispatch + select
    ├── components/<entity>-card.component.ts  # dumb : @Input/@Output
    └── facades/<entity>.facade.ts    # optionnel
```

Plus :
- `<feature>.module.ts` avec `providers: [{ provide: <Entity>Repository, useClass: <Entity>HttpRepository }]`
- `.eslintrc.js` du projet avec `no-restricted-imports` ciblant `**/domain/**` et `**/application/**`
- Spécifications par couche : `*.spec.ts` dans chaque répertoire

## Base skills (séquence + parallélisme)

1. `dx_base_create_frontend_archi_directory_skeleton`
2. En parallèle :
   - `dx_base_create_frontend_archi_domain_example`
   - `dx_base_create_frontend_archi_application_use_cases`
   - `dx_base_create_frontend_archi_infrastructure_http`
   - `dx_base_create_frontend_archi_infrastructure_store`
   - `dx_base_create_frontend_archi_presentation_smart_dumb`
   - `dx_base_create_frontend_archi_test_skeletons`
   - `dx_base_create_frontend_archi_eslint_config`
3. `dx_base_create_frontend_archi_module_wiring` (providers DI, dépend de l'étape 2)

## Garde-fous

- Refuser la création si le nom de feature ne correspond pas à un B4F existant (cf. § 3.4)
- Refuser l'ajout d'imports `@angular/*` dans les fichiers générés sous `domain/` ou `application/`
- Le `store/` est créé en `infrastructure/`, jamais ailleurs

## Format de sortie

Liste des fichiers créés, commande de validation ESLint, snapshot de l'arborescence finale.
