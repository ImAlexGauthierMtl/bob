# Checklist Qualité HDQ

> Vérifier chaque item avant de merger. Un seul ❌ = pas de merge.

## Architecture

- [ ] L'architecture définie dans `context/projet.md` est respectée
- [ ] Les couches sont bien séparées (Routes → Use Cases → Services → Repositories)
- [ ] Pas de logique métier dans les routes
- [ ] Pas d'accès DB dans les use cases
- [ ] Le frontend n'appelle que les APIs autorisées

## Backend

- [ ] Type hints sur toutes les fonctions
- [ ] Pydantic schemas pour input/output (pas de dict)
- [ ] Use Cases retournent des types spécifiques (pas de generics)
- [ ] No N+1 queries (selectinload / joined load)
- [ ] CamelCase pour les réponses JSON (CamelModel)
- [ ] Structlog pour le logging (jamais `print()`)
- [ ] Gestion d'erreurs avec exceptions typées
- [ ] tenant_id / isolation des données respectée

## Frontend

- [ ] Composants standalone (pas de modules)
- [ ] `inject()` au lieu de constructor injection
- [ ] Signal inputs/outputs (pas de @Input/@Output decorators)
- [ ] Syntaxe template moderne (`@if`, `@for`, `@defer`)
- [ ] État géré via NGRX Store (pas de state local pour les données)
- [ ] Pas de `any` en TypeScript (strict mode)
- [ ] Labels UI en français, code en anglais

## Tests

- [ ] 100% coverage backend (ou justification dans dette-technique.md)
- [ ] 80% coverage frontend minimum
- [ ] 30% des tests couvrent des cas négatifs (erreurs, edge cases)
- [ ] Fixtures réutilisables (conftest.py / TestBed)
- [ ] Mocks pour services externes

## Sécurité

- [ ] JWT validé sur chaque endpoint protégé
- [ ] Pas de secrets dans le code
- [ ] Input validation (Pydantic / Angular validators)
- [ ] Pas de données sensibles dans les logs

## CI/CD

- [ ] Pipeline vert
- [ ] Migrations commitées si changement de schéma
- [ ] Commit sémantique `[service] type: description`
