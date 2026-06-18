---
name: dx_intermediate_analyse_k8s_config
description: Analyse la configuration Kubernetes du projet — convention des noms d'environnement (dev/staging/prod), namespaces, indirection KUBECONFIG_VARIABLE, certificats TLS wildcard vs spécifique, observabilité Alloy + OTel, propagation traceparent, probes K8s et endpoints de santé. À invoquer pour comprendre comment K8s est câblé dans un projet.
metadata:
  reference: § 5 de docs/architecture/regles-architecture-deploiement.md
---

# dx_intermediate_analyse_k8s_config

## Périmètre

- Noms d'environnement canoniques `dev`, `staging`, `prod` (§ 5.1)
- Stratégie de scoping (§ 5.2) : global (dev + review) vs scope env spécifique
- Convention namespace `<projet>-<env>` (§ 5.3)
- Indirection KUBECONFIG_VARIABLE → variable File (§ 5.4)
- Stratégie TLS wildcard vs spécifique (§ 5.7)
- Observabilité Alloy + OTel (§ 5.8) — endpoint OTLP, sampling, agent propriétaire
- Tracing distribué : `traceparent`, `trace_id` dans payload events Redis (§ 5.9)
- Probes K8s et 5 endpoints de santé (§ 5.10)

## Base skills (parallélisables)

- `dx_base_check_k8s_env_names_canonical`
- `dx_base_check_k8s_namespace_convention`
- `dx_base_check_k8s_kubeconfig_indirection`
- `dx_base_check_k8s_kubeconfig_type_file`
- `dx_base_check_k8s_no_base64_decode`
- `dx_base_check_k8s_tls_wildcard_first`
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

## Format de sortie

Synthèse par section § 5.x.
