---
name: dx_base_check_env_vars_scoped_per_env
description: Vérifie que les variables CI sensibles sont scopées par environnement (dev/staging/prod) dans GitLab Settings.
metadata:
  reference: § 6 + § 8.5
---

# dx_base_check_env_vars_scoped_per_env

## Actions
Inspecter Settings → CI/CD → Variables : DB_PASSWORD, JWT_SECRET, etc., doivent avoir un environment scope. Non vérifiable depuis le repo → documenter dans README.
