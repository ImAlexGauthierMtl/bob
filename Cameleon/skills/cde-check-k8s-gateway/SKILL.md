---
name: cde-check-k8s-gateway
description: "Audit or refactor Croo Digital Experience Kubernetes values and gateway routing against docs/regles-architecture-deploiement.md. Use for CDE rules M-05 and Kubernetes or gateway checks: one external gateway, frontend at root, B4F APIs under /api, internal Backends only, probes, migrations by initContainer and Kubernetes Lease RBAC. Excludes CI/CD and Harbor execution."
---

# CDE K8s Gateway

## Sources

- Use `docs/regles-architecture-deploiement.md`, sections 5 and 8.4.
- Update the Cameleon matrix with repo-local evidence.
- Do not validate live deployment, CI/CD, Harbor, or registry variables in this phase.

## Workflow

1. Inspect `deploy/`, Helm values, and docker-compose equivalents.
2. Confirm the gateway exposes `/` to frontend and `/api/<service>` to B4F APIs only.
3. Confirm Backends are ClusterIP/internal and absent from public gateway routes.
4. Confirm backend deployments include migration initContainer behavior and Lease RBAC where chart ownership is local.
5. Confirm probes and service ports match API runtime expectations.
6. Record repo-local proof in the matrix; mark external deployment proof as skipped or blocked if it needs missing platform elements.

## Refactor Rules

- Prefer values-only configuration when a shared chart owns templates.
- Remove project-local Helm logic that duplicates shared deployment behavior.
- Keep gateway route names and service names aligned with `apis/exposed/*-b4f-api`.
- Keep Backend API names routable only via internal DNS.

## Useful Checks

- Gateway routes: `rg -n "apiRoutes|/api/|frontend|b4f|backend" deploy docker-compose.yml`
- Public Backend exposure: `rg -n "backend-api|Ingress|ingress" deploy`
- Lease/migration config: `rg -n "initContainer|migrate|Lease|coordination.k8s.io|migrate_with_lease" deploy apis`
- Probe config: `rg -n "liveness|readiness|startup|/health|/metrics" deploy apis`
