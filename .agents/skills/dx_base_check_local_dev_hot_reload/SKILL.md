---
name: dx_base_check_local_dev_hot_reload
description: Vérifie que le compose monte les sources en volume pour hot-reload (uvicorn --reload, ng serve).
metadata:
  reference: § 11
---

# dx_base_check_local_dev_hot_reload

## Actions
```bash
grep -E "volumes:|--reload|ng serve" docker-compose.yml | head -20
```
