---
name: dx_base_create_frontend_feature_full
description: Bootstrap une feature NGRX complète : module, actions, reducer, effects, selectors, service, smart component, dumb component, route, tests.
metadata:
  reference: § 3 + § 14
---

# dx_base_create_frontend_feature_full

## Actions
Générer via schematics + ajustement manuel :
```bash
ng g feature features/<name>
ng g service services/<name>
# puis créer actions/reducer/effects/selectors dans infrastructure/store/
```
Wire les providers (`useClass: <Name>HttpRepository`).
