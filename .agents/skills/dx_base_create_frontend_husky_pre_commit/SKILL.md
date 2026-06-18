---
name: dx_base_create_frontend_husky_pre_commit
description: Configure Husky + lint-staged pour exécuter lint + tests unitaires + E2E rapides à chaque commit frontend.
metadata:
  reference: § 3.5
---

# dx_base_create_frontend_husky_pre_commit

## Actions
```bash
cd frontend
npx husky-init && npm install
npx husky add .husky/pre-commit "npm run lint && npm test -- --watch=false && npm run e2e:smoke"
```
