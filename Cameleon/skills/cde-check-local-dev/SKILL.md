---
name: cde-check-local-dev
description: "Audit or refactor Croo Digital Experience local development, environment, and repository convention rules against docs/regles-architecture-deploiement.md. Use for CDE rules M-06, M-09, L-01 to L-07: root wrappers, per-API scripts, docker-compose services, .env.example, no real secrets or client data, docs placement, and no tool-specific project rules."
---

# CDE Local Dev

## Sources

- Use `docs/regles-architecture-deploiement.md`, sections 6, 10, and 11.
- Update Cameleon matrix rows for environment variables, local dev, docs, and secrets.
- Keep CI/CD variables out of scope unless the user reopens that work.

## Workflow

1. Verify root wrappers exist for local run, migration, API tests, frontend run, frontend tests, and frontend e2e.
2. Verify each Backend has the expected local scripts for run, tests, and migrations.
3. Verify `docker-compose.yml` can support local Postgres, PgBouncer, Redis, and Alloy where rules require them.
4. Verify `.env.example` documents local-only variable names without production secrets.
5. Scan for real secrets, customer data, tool-specific rules, and misplaced docs.
6. Record findings and commands in the Cameleon matrix.

## Refactor Rules

- Use examples and placeholders, never real credentials.
- Keep docs under `docs/` except the active Cameleon working folder during conversion.
- Keep `Cameleon/` as the conversion workspace and final evidence area.
- Remove old project-rule folders that are not part of the standard.
- Do not add tool-specific instructions or references.

## Useful Checks

- Local wrappers: `find . -maxdepth 2 -type f -name "run*.sh" -o -name "migrate*.sh" | sort`
- Env files: `find . -maxdepth 4 -name "*.env*" -o -name ".env.example" | sort`
- Secret scan seed: `rg -n "password|secret|token|api[_-]?key|PRIVATE KEY|BEGIN RSA|client_secret" .`
- Tool-specific folders: `find . -maxdepth 3 -type d \\( -name ".kilo" -o -name ".cursor" -o -name ".windsurf" -o -name ".claude" \\) -print`
