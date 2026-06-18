---
name: dx_intermediate_create_k8s_config
description: Crée la configuration K8s d'un projet — values Helm par env/API (§ 4 + § 5), instructions pour les variables CI/CD globales/staging/prod, KUBECONFIG_VARIABLE en indirection, scoping wildcard TLS, injection OTel et traceparent dans les APIs. Génère également la table des variables à configurer côté admin GitLab.
metadata:
  reference: § 5 de docs/architecture/regles-architecture-deploiement.md
---

# dx_intermediate_create_k8s_config

## Paramètres requis

- Nom du projet (slug)
- Domaine de base (ex. `asq.example.com`)
- Liste des APIs (B4F + Backend)
- Endpoint OTLP Alloy par env (par défaut `http://alloy.observability.svc.cluster.local:4317`)

## Workflow

### 1. Variables CI/CD à demander à l'admin

Produire un script `glab` (cf. § 7.5) qui crée :

- Variables globales (dev + review) : `NAMESPACE`, `INGRESS_HOST`, `KUBECONFIG_VARIABLE`, `DB_HOST`, `DB_USERNAME`, `DB_PASSWORD`, `DB_DATABASE`, `DATABASE_SSLMODE`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `PROMETHEUS_URL`
- Variables scopées `staging` : mêmes noms, valeurs staging
- Variables scopées `prod` : mêmes noms, valeurs prod, **toutes protégées**

Variables système (admin GitLab) à demander si pas déjà fait :
- `OVH_KUBECONFIG` (type **File**)
- `OVH_KUBECONFIG_STAGING` (type **File**)
- `OVH_KUBECONFIG_PROD` (type **File**)

### 2. Values Helm

Pour chaque API et chaque env, des values qui :
- Pointent le chart `api-chart` du repo central
- Définissent `serviceName`, `apiTier`
- Configurent les probes par défaut (héritées du chart)
- Injectent `OTEL_SERVICE_NAME = <api>` et `OTEL_TRACES_SAMPLER_ARG` (1.0 en dev, 0.1 en prod)
- N'ajoutent l'`ingress` que pour les B4F

### 3. TLS

**Ne rien faire de spécifique** — le chart du repo central gère wildcard vs
spécifique automatiquement via `tls.strategy`. Mentionner dans la doc projet
que le wildcard doit exister côté `cert-manager`.

### 4. Endpoints de santé

Confirmer que chaque API expose `/liveness`, `/readiness`, `/startup`,
`/metrics`, `/health` (§ 5.10) — déléguer la création à
`dx_intermediate_create_apis` qui a la responsabilité du squelette d'API.

## Base skills

- `dx_base_create_k8s_variables_glab_script`
- `dx_base_create_k8s_values_per_api_env`

## Anti-patterns

1. Utiliser `production` au lieu de `prod` (§ 5.1)
2. Hardcoder `OVH_KUBECONFIG` dans un script (§ 5.4)
3. `base64 -d` sur le kubeconfig (§ 5.4)
4. Émettre un certificat spécifique sans tester le wildcard (§ 5.7)
5. Sampling OTel à 1.0 en prod (§ 5.8)
