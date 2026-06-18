---
name: dx_intermediate_check_k8s_config
description: Verdict pass/fail de la config K8s selon § 5 et § 8.4. Convention d'env, NAMESPACE depuis variable scopée, kubeconfig en variable File (pas base64), wildcard TLS, observabilité Alloy + OTel, sampling 0.1 en prod, 5 endpoints de santé non authentifiés, /liveness sans appel externe, /health sans pool applicatif.
metadata:
  reference: § 5 + § 8.4 + § 8.8 de docs/architecture/regles-architecture-deploiement.md
---

# dx_intermediate_check_k8s_config

## Périmètre

Checklist § 8.4 (config K8s) + § 8.8 (observabilité).

## Base skills (parallélisables)

Mêmes que `dx_intermediate_analyse_k8s_config` mais résultat pass/fail.

- `dx_base_check_k8s_env_names_canonical`
- `dx_base_check_k8s_namespace_from_variable`
- `dx_base_check_k8s_namespace_convention`
- `dx_base_check_k8s_kubeconfig_indirection`
- `dx_base_check_k8s_kubeconfig_type_file`
- `dx_base_check_k8s_no_base64_decode`
- `dx_base_check_k8s_tls_wildcard_first`
- `dx_base_check_k8s_tls_chart_supports_both_modes`
- `dx_base_check_k8s_observability_alloy_otlp`
- `dx_base_check_k8s_logs_stdout_json`
- `dx_base_check_k8s_metrics_endpoint`
- `dx_base_check_k8s_no_proprietary_agents`
- `dx_base_check_k8s_otel_sampling`
- `dx_base_check_k8s_traceparent_propagation`
- `dx_base_check_k8s_trace_id_in_events`
- `dx_base_check_k8s_trace_id_in_logs`
- `dx_base_check_k8s_health_endpoints`
- `dx_base_check_k8s_health_unauthenticated`
- `dx_base_check_k8s_liveness_no_external_calls`
- `dx_base_check_k8s_health_no_app_pool`

### Gateway centralisé + Frontend chart (v1.1)

- `dx_base_check_gateway_routes_frontend_root`
- `dx_base_check_gateway_routes_apis_under_api_prefix`
- `dx_base_check_gateway_https_redirect`
- `dx_base_check_gateway_uses_wildcard_tls`
- `dx_base_check_b4f_no_individual_ingress`
- `dx_base_check_frontend_chart_exists`
- `dx_base_check_frontend_no_ingress`
- `dx_base_check_frontend_api_base_url_is_api`
- `dx_base_check_gateway_chart_exists`
- `dx_base_check_cert_copy_job_exists`
- `dx_base_check_cert_copy_rbac_minimal`
- `dx_base_check_gateway_deployed_last`
- `dx_base_check_gateway_discover_apis_routes`
- `dx_base_check_no_certificate_in_api_chart`

Format § 9 standard.
