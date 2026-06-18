---
name: cde-check-api-boundaries
description: "Audit or refactor Croo Digital Experience API boundaries against docs/regles-architecture-deploiement.md. Use for CDE rules M-01 and A-01 to A-09: B4F versus Backend separation, gateway exposure, no DB or external services in B4F, no HTTP Backend-to-Backend, Redis event bus ownership, and backend entity ownership."
---

# CDE API Boundaries

## Sources

- Use `docs/regles-architecture-deploiement.md` as the source of truth.
- Update `Cameleon/matrice-validation-conformite-v1.4.md` with status and evidence.
- Inspect the local repository only. Do not add tool-specific or cross-project references.
- Skip CI/CD and Harbor evidence unless the user explicitly reopens that scope.

## Workflow

1. Map every API under `apis/exposed/` and `apis/internal/`.
2. Verify each B4F is externally routed only through the gateway and has no database, Alembic, SQLAlchemy model, repository, or direct external-service client.
3. Verify each Backend owns one primary entity family, its schema, migrations, repositories, and external integrations.
4. Verify B4F -> Backend calls use internal service DNS and Backend -> Backend synchronization uses Redis events, not HTTP.
5. Verify gateway and frontend routes do not target internal Backends directly.
6. Record each finding in the Cameleon matrix with concrete file paths, commands, or tests.

## Refactor Rules

- Move external clients found in B4F APIs into the owning Backend.
- Keep B4F logic focused on aggregation, validation, orchestration, and frontend-specific composition.
- Replace direct Backend-to-Backend HTTP with domain events through `shared.event_bus`.
- Keep shared packages technical only; do not put business logic in `shared/`.
- Add or update focused tests for any changed route, client, publisher, or subscriber.

## Useful Checks

- Search B4F database leakage: `rg -n "DATABASE_URL|create_engine|SessionLocal|alembic|Base\\.metadata|sqlalchemy" apis/exposed`
- Search B4F external clients: `rg -n "httpx|requests|graph\\.microsoft|pipedream|membrane|openai|stripe|twilio" apis/exposed`
- Search Backend HTTP coupling: `rg -n "http://.*backend|backend-api|HTTPClient" apis/internal`
- Search event bus usage: `rg -n "event_bus|Event\\(" apis/internal apis/shared`
