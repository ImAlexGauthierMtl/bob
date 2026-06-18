---
name: cde-check-clean-architecture
description: "Audit or refactor Croo Digital Experience API Clean Architecture against docs/regles-architecture-deploiement.md. Use for CDE rules M-10 and CA-01 to CA-06: uniform domain application infrastructure presentation layers, framework-free domain and application layers, thin routes, pure entities, and import boundary enforcement."
---

# CDE Clean Architecture

## Sources

- Use `docs/regles-architecture-deploiement.md`, section 12.
- Update the Cameleon matrix with per-API evidence.
- Keep this separate from B4F/Backend responsibility checks; this skill validates internal layering.

## Workflow

1. Map each API folder to the expected four layers: `domain/`, `application/`, `infrastructure/`, and `presentation/`.
2. Verify domain code has no FastAPI, SQLAlchemy, HTTP client, or Pydantic framework dependency.
3. Verify application code orchestrates use cases without depending on FastAPI routes or infrastructure implementation details.
4. Verify routes/controllers are thin: request parsing, dependency wiring, use-case call, response mapping.
5. Verify domain entities do not inherit from SQLAlchemy declarative bases or Pydantic `BaseModel`.
6. Verify import-linter or an equivalent boundary check exists, or record it as a remaining gap.
7. Add focused tests or import checks when refactoring boundaries.

## Refactor Rules

- Move framework adapters outward, not inward.
- Keep persistence models and API schemas out of domain entities.
- Introduce use-case services only when they reduce route or repository coupling.
- Avoid broad rewrites unless the matrix row needs the changed behavior.

## Useful Checks

- Layer inventory: `find apis -maxdepth 4 -type d \\( -name domain -o -name application -o -name infrastructure -o -name presentation \\) | sort`
- Domain framework leakage: `rg -n "fastapi|sqlalchemy|pydantic|httpx|requests" apis/**/domain`
- Application framework leakage: `rg -n "fastapi|APIRouter|Depends|sqlalchemy|Session" apis/**/application`
- Entity inheritance: `rg -n "class .*\\((Base|BaseModel)" apis/**/domain`
