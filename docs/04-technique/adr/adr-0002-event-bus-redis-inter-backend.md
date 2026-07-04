# ADR-0002 — Event Bus Redis pour la synchro inter-backend

- **Statut** : Accepted (documenté a posteriori) · **Date** : 2026-07-01 · **Décideur** : Alexandre Gauthier
- **Réf. normative** : [`regles-architecture-deploiement.md` (v1.4)](../../regles-architecture-deploiement.md)

## Contexte
Avec des backends CRUD par entité ([ADR-0001](adr-0001-architecture-deux-tiers-b4f-backend.md)), certains ont besoin de réagir aux changements des autres (ex. un workflow déclenché par `contact.created`). Comment synchroniser sans recréer un couplage fort ?

## Décision
Toute synchronisation inter-backend passe par un **Event Bus Redis** partagé :
- **Canal** : `{source-api}.{entity}.{action}` (ex. `contact-backend-api.contact.created`).
- **Contrat** : `{event, timestamp, tenant_id, trace_id, data}`.
- **Sémantique** : fire-and-forget, cohérence éventuelle, subscribers **idempotents**.
- **Interdits** : Backend→Backend en **HTTP direct** ; B4F ne publie ni ne souscrit.
- Redis est **dédié** à l'event bus (les migrations utilisent un Lease Kubernetes, pas Redis).

## Alternatives envisagées
1. **Appels HTTP synchrones Backend→Backend** — simples au départ, mais couplage temporel, cascades de pannes, latence cumulée. Rejeté (monolithe distribué).
2. **Broker lourd (Kafka/RabbitMQ)** — garanties fortes (ordre, persistance, replay), mais surcoût opérationnel injustifié à ce stade. Rejeté pour l'instant (réévaluable si besoin de replay/ordre strict).
3. **Base de données comme file (outbox + polling)** — robuste, mais complexité supplémentaire. Rejeté au profit de Redis déjà présent.

## Conséquences
- ✅ Découplage temporel : un backend down ne bloque pas les autres.
- ✅ `trace_id` propagé dans les events → traçabilité de bout en bout.
- ⚠️ **Cohérence éventuelle** : l'UI peut voir un état transitoire ; à gérer côté produit.
- ⚠️ Pas de garantie d'ordre ni de replay natif (Redis pub/sub) → les subscribers doivent être idempotents et tolérants aux pertes ; **à réévaluer** si un besoin de durabilité forte émerge.
- ⚠️ Intégrité des payloads d'events à sécuriser (voir [Threat Model](../threat-model.md), section Tampering).
