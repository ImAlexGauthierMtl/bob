---
name: dx_base_check_backend_owns_infrastructure
description: Vérifie que l'accès infrastructure (base de données, services externes, fichiers/stockage) vit dans les Backend uniquement, jamais dans les B4F.
metadata:
  reference: § 2.3 + § 2.8
---

# dx_base_check_backend_owns_infrastructure

## Règle
DB, services externes et fichiers = **Backend uniquement**. Le B4F délègue tout accès infrastructure.

## Actions
```bash
# 1. Aucun accès fichier/stockage dans un B4F
for d in apis/exposed/*-b4f-api/; do
  [ -d "$d/src" ] || continue
  name=$(basename "$d")
  grep -rqE "open\(|pathlib|boto3|minio|s3\.|aiofiles|smtplib|aiosmtplib" "$d/src" 2>/dev/null \
    && echo "FAIL: $name (B4F) accède à un fichier/stockage/SMTP — doit déléguer à un Backend"
  grep -rqE "DATABASE_URL|sqlalchemy|asyncpg|psycopg" "$d/src" 2>/dev/null \
    && echo "FAIL: $name (B4F) référence la DB"
done

# 2. L'accès infra existe bien côté Backend (au moins la persistance)
for d in apis/internal/*-backend-api/; do
  [ -d "$d/src" ] || continue
  name=$(basename "$d")
  [ -d "$d/src"/*/infrastructure/persistence ] 2>/dev/null \
    || echo "WARN: $name (Backend) sans infrastructure/persistence/"
done
```
