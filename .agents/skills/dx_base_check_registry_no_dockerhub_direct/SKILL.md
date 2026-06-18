---
name: dx_base_check_registry_no_dockerhub_direct
description: Vérifie qu'aucun Dockerfile ne référence directement docker.io / docker.hub (doit passer par le proxy).
metadata:
  reference: § 7
---

# dx_base_check_registry_no_dockerhub_direct

## Actions
```bash
grep -rE "FROM docker\.(io|hub)/" apis/ frontend/ && echo "WARN: pull direct Docker Hub"
```
Le Kaniko wrappé règle ça transparent → souvent pas un FAIL hard, mais bon de signaler.
