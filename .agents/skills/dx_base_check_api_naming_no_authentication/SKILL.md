---
name: dx_base_check_api_naming_no_authentication
description: Vérifie qu'aucun service/API/schéma DB ne porte le nom 'authentication'. Banni au profit du couple iam-backend-api + auth-b4f-api avec schéma DB 'iam'.
metadata:
  reference: § 2.5 + § 8.1
---

# dx_base_check_api_naming_no_authentication

## Règle
Le terme `authentication` est interdit (trop générique). Découper en split iam (backend) + auth (b4f).

## Actions
```bash
find apis/ -name "*authentication*" && echo FAIL
grep -rE "schema.*authentication|search_path.*authentication" apis/ && echo FAIL
```
