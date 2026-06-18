---
name: cde-check-frontend-ngrx
description: "Audit or refactor Croo Digital Experience Angular and NGRX rules against docs/regles-architecture-deploiement.md. Use for CDE rules M-03 and F-01 to F-08: one frontend service and feature store per B4F, HTTP through services and effects, DTO-to-domain mapping, async templates, Playwright e2e folder, and local smoke hooks outside CI."
---

# CDE Frontend NGRX

## Sources

- Use `docs/regles-architecture-deploiement.md`, sections 3, 8.2, 8.12, and 14.
- Update the Cameleon matrix with concrete frontend files and commands.
- Browser screenshots are required only when UI behavior changes.

## Workflow

1. Map every B4F route/domain to a frontend service and NGRX feature.
2. Verify components do not perform direct HTTP orchestration or own backend DTO state.
3. Verify HTTP calls live in services and state transitions live in effects/reducers/selectors.
4. Verify DTOs are mapped into domain models before entering store state.
5. Verify templates use observable state patterns such as `| async`.
6. Verify Playwright e2e tests live under `frontend/e2e/` and are local-only for this phase.
7. Update the matrix and add focused frontend tests where behavior changes.

## Refactor Rules

- Keep a predictable folder per feature: actions, effects, reducer, selectors, models, and service wiring.
- Do not add e2e jobs to CI/CD in this phase.
- Do not hide business rules in components.
- Keep UI validation browser-backed when visible screens change and store screenshots in root `captures/`.

## Useful Checks

- HTTP usage: `rg -n "HttpClient|\\.get\\(|\\.post\\(|\\.put\\(|\\.delete\\(" frontend/src`
- Store coverage: `find frontend/src -path "*store*" -type f | sort`
- Component service injection: `rg -n "constructor\\(|inject\\(" frontend/src/app --glob "*.component.ts"`
- Async templates: `rg -n "\\| async" frontend/src/app --glob "*.html"`
