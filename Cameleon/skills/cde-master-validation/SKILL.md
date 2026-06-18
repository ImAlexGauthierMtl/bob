---
name: cde-master-validation
description: "Produce the final Croo Digital Experience Cameleon validation package after refactor work. Use when consolidating CDE conversion branches, filling Cameleon/matrice-validation-conformite-v1.4.md, writing the final report required by docs/regles-architecture-deploiement.md section 9, and running local Docker validation while CI/CD and Harbor are skipped."
---

# CDE Master Validation

## Sources

- Use `docs/regles-architecture-deploiement.md`, section 9.
- Use all `Cameleon/skills/cde-check-*` skills for focused checks.
- Use `Cameleon/matrice-validation-conformite-v1.4.md` as the acceptance matrix.

## Workflow

1. Merge or rebase the conversion branches into one final branch as requested by the user.
2. Re-run local repository checks for API boundaries, DB/Alembic, Kubernetes values, frontend, observability, local dev, and Clean Architecture.
3. Mark CI/CD and Harbor rows as skipped or blocked by missing platform elements if they remain outside scope.
4. Run local Docker validation and capture the exact result.
5. Fill every matrix row with `OK`, `VIOLATION`, `A_VERIFIER`, `SKIP_CI_CD`, or `BLOQUE`.
6. Produce the final report with summary, completed changes, remaining gaps, skipped CI/CD items, local validation evidence, and next actions.

## Refactor Rules

- Do not claim compliance without a file, command, test, or Docker evidence.
- Keep API and frontend screenshots only when visible UI changed.
- Keep the final report in `Cameleon/` unless the user asks to move it under `docs/`.
- Do not follow pipelines or edit CI/CD during this skipped phase.

## Useful Checks

- Matrix gaps: `rg -n "VIOLATION|A_VERIFIER|BLOQUE|SKIP_CI_CD" Cameleon/matrice-validation-conformite-v1.4.md`
- Working tree: `git status --short --branch`
- Docker config: `docker compose --env-file .env.example config`
- Docker run: `docker compose --env-file .env.example up --build`
