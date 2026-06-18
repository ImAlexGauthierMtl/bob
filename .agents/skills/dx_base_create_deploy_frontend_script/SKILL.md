---
name: dx_base_create_deploy_frontend_script
description: Génère deploy/scripts/deploy-frontend.sh : helm upgrade --install frontend du chart frontend-chart, avec values deploy/values/<env>/frontend.yaml.
metadata:
  reference: § 5.12
---

# dx_base_create_deploy_frontend_script

## Variables requises
ENV, NAMESPACE, IMAGE, VALUES_FILE, KUBECONFIG.

## Logique
helm upgrade --install frontend frontend-chart --values deploy/values/<env>/frontend.yaml --set image.repository, image.tag, env --atomic --wait
