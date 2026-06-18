---
name: dx_base_create_shared_auth_rbac_audit
description: Génère/complète les primitives transverses dans apis/shared : validation d'auth (JWT/session), moteur RBAC, émetteur d'audit, logger JSON avec trace_id. Expose des Ports côté domain des APIs pour injection.
metadata:
  reference: § 2.10
---

# dx_base_create_shared_auth_rbac_audit

## Sortie attendue dans apis/shared/
- `auth/` : `verify_token()`, extraction d'identité + claims (pas de logique métier)
- `rbac/` : moteur de décision `is_allowed(actor, action, resource) -> bool`
- `audit/` : `emit(actor, action, resource, tenant_id, trace_id, timestamp)`
- `logging/` : logger JSON structuré injectant `trace_id`/`span_id` du span actif
- `errors/`, `pagination/`, `middleware/` : transverses HTTP

## Côté API
- Définir les Ports abstraits en `domain/ports/` : `AuthorizationPort`, `AuditPort`
- Implémenter les adapters en `infrastructure/security/` qui délèguent à `apis.shared`
- Câbler le middleware d'auth en `presentation/deps.py` (depuis `apis.shared` / `apis.exposed.shared`)

## Refus
- Refuser de mettre une règle d'autorisation métier dans `apis/shared/` (elle va dans le `domain/` de l'API via Port)
- Refuser de réimplémenter un logger ou un validateur de token par API
