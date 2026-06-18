---
name: dx_base_create_deploy_gateway_script
description: Génère deploy/scripts/deploy-gateway.sh : scanne apis/exposed/, génère la liste des routes, lance helm upgrade --install api-gateway avec --set host, tls.sourceSecretName, etc.
metadata:
  reference: § 5.11
---

# dx_base_create_deploy_gateway_script

## Variables requises
ENV, NAMESPACE, INGRESS_HOST, WILDCARD_SOURCE_SECRET, WILDCARD_SOURCE_NS (default cert-manager), WILDCARD_TARGET_SECRET (default wildcard-tls), PROJECT_DIR.

## Logique
1. mktemp routes.yml + scan `apis/exposed/*-b4f-api/` pour générer `routes.apis: [{name, service}]`
2. helm upgrade --install api-gateway --values routes.yml --set host, tls.*, env
3. Vérifier post-deploy : secret TLS présent + force-ssl-redirect annotation == "true"
