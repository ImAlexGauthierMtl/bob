---
name: dx_base_create_registry_pull_secret
description: Crée le imagePullSecret K8s à partir d'un personal access token GitLab (jamais le compte personnel).
metadata:
  reference: § 7
---

# dx_base_create_registry_pull_secret

## Actions
```bash
kubectl create secret docker-registry gitlab-registry       --docker-server=gitlab.tools.thesmartcrew.com:5050       --docker-username=<bot-user>       --docker-password=<bot-pat>       -n <namespace>
```
