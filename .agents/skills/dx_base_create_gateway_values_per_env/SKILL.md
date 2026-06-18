---
name: dx_base_create_gateway_values_per_env
description: Génère deploy/values/<env>/gateway.yaml pour chaque environnement (dev/staging/prod). host, tls.sourceSecretName, annotations spécifiques.
metadata:
  reference: § 5.11
---

# dx_base_create_gateway_values_per_env

## Contenu
Le `host` est passé via --set INGRESS_HOST par le pipeline (pas dans values).
Mettre seulement les overrides par env : annotations spécifiques (CORS dev, body-size prod...), enableCopyJob (true par défaut).
Routes JAMAIS dans le values — générées par discover-apis.sh.
