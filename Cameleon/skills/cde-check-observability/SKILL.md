---
name: cde-check-observability
description: "Audit or refactor Croo Digital Experience observability against docs/regles-architecture-deploiement.md. Use for CDE rules M-08 and O-01 to O-06: JSON logs to stdout or stderr, liveness readiness startup health metrics endpoints, health dependencies, OpenTelemetry to Alloy, traceparent propagation, and trace_id in Redis events."
---

# CDE Observability

## Sources

- Use `docs/regles-architecture-deploiement.md`, sections 5.8 to 5.10 and 8.8.
- Update the Cameleon matrix with route checks, local tests, or file evidence.

## Workflow

1. Confirm every API configures shared structured logging and emits JSON by default.
2. Confirm `/liveness`, `/readiness`, `/startup`, `/health`, and `/metrics` are registered consistently.
3. Confirm `/liveness` stays cheap and does not call external dependencies.
4. Confirm `/health` reports dependencies such as database, Redis, and OTel where applicable.
5. Confirm inbound `traceparent` and `x-request-id` are preserved or generated and outbound HTTP clients forward them.
6. Confirm Redis/domain events carry a 32-character W3C trace id when a request context exists.
7. Add focused tests for changed shared middleware, logging, health, metrics, clients, or event bus behavior.

## Refactor Rules

- Put cross-cutting observability behavior in shared infrastructure modules.
- Do not duplicate route implementations across every API if a shared router exists.
- Keep event payloads small and trace metadata explicit.
- Prefer deterministic local FastAPI tests over live deployment checks in this phase.

## Useful Checks

- Logging setup: `rg -n "configure_logging|JSONRenderer|stdout|stderr" apis`
- Probes and metrics: `rg -n "liveness|readiness|startup|health|metrics" apis`
- Trace propagation: `rg -n "traceparent|trace_id|x-request-id|bind_trace_context" apis`
- Event metadata: `rg -n "Event\\(|to_dict|from_dict|trace_id" apis/shared apis/internal`
