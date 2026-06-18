---
name: dx_base_check_gateway_deployed_last
description: Vérifie que le job deploy:<env>:gateway a `needs:` sur tous les deploys (APIs + frontend) du même env.
metadata:
  reference: § 5.11
---

# dx_base_check_gateway_deployed_last

## Actions
Inspecter la pipeline générée par discover-apis.sh :
```bash
bash /tmp/cicd-templates/deploy/scripts/discover-apis.sh > /tmp/child.yml
# Lister les needs du job gateway pour chaque env
for env in dev staging prod; do
  yq ".\"deploy:${env}:gateway\".needs[]" /tmp/child.yml || echo "FAIL: pas de needs pour deploy:${env}:gateway"
done
```
Le set des needs doit être ⊇ {tous les deploy:${env}:* sauf le gateway lui-même}.
