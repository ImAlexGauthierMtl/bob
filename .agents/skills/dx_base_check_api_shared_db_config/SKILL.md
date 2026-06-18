---
name: dx_base_check_api_shared_db_config
description: Vérifie que tous les Backends utilisent les MÊMES DB_HOST, DB_USERNAME, DB_PASSWORD, DB_DATABASE, DB_SSLMODE (un seul cluster PG). Chaque Backend a son schéma, pas sa DB.
metadata:
  reference: § 2.6 + § 8.1
---

# dx_base_check_api_shared_db_config

## Actions
Comparer les values yaml de tous les *-backend-api : DB_HOST, DB_USERNAME, DB_PASSWORD, DB_DATABASE doivent matcher (souvent via valueFrom secretKeyRef commun).
```bash
grep -hE "DB_(HOST|USERNAME|PASSWORD|DATABASE)" deploy/values/*-backend-api-*.yaml | sort -u
```
Plus d'un cluster → FAIL.
