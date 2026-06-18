---
name: cde-check-database-alembic
description: "Audit or refactor Croo Digital Experience database and Alembic rules against docs/regles-architecture-deploiement.md. Use for CDE rules M-02 and DB-01 to DB-09: no runtime DDL, schema-per-backend migrations, grants/default privileges, downgrade symmetry, PgBouncer-safe SQLAlchemy pools, and local upgrade/downgrade validation."
---

# CDE Database Alembic

## Sources

- Use `docs/regles-architecture-deploiement.md`, sections 2.7 and 8.1.
- Update `Cameleon/matrice-validation-conformite-v1.4.md` with proof.
- Keep CI downgrade/upgrade checks out of scope unless the user reopens CI/CD.

## Workflow

1. List all Backends under `apis/internal/*-backend-api`.
2. Confirm no application startup code executes `Base.metadata.create_all`, raw schema creation, or table creation.
3. Confirm all DDL lives in Alembic migrations and the first revision creates schema, grants, default privileges, and tables.
4. Confirm every migration has a real `downgrade()` and avoids irreversible raw SQL unless documented.
5. Validate at least changed Backends locally with upgrade head, downgrade base or previous revision, and upgrade head again.
6. Confirm shared database connection settings are PgBouncer-safe: small pools, `pool_pre_ping=True`, `pool_recycle<=300`, and prepared statements disabled when required.
7. Record exact commands and impacted Backends in the matrix.

## Refactor Rules

- Prefer Alembic operations over raw SQL when possible.
- Keep runtime app startup free of schema mutation.
- Keep Backend models schema-qualified.
- Do not store real database credentials in repo files.
- Do not convert local validation into CI work in this phase.

## Useful Checks

- Runtime DDL: `rg -n "create_all|CREATE SCHEMA|CREATE TABLE|DROP TABLE|ALTER TABLE" apis/internal`
- Empty downgrades: `rg -n "def downgrade|pass$" apis/internal/*-backend-api/alembic/versions`
- SQLAlchemy pool: `rg -n "pool_size|max_overflow|pool_pre_ping|pool_recycle|prepare_threshold" apis/shared apis/internal`
- Alembic config: `rg -n "include_schemas|version_table|script_location" apis/internal/*-backend-api/alembic.ini apis/internal/*-backend-api/alembic/env.py`
