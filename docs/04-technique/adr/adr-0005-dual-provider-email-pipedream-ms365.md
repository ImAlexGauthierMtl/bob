# ADR-0005 — Email dual-provider (Pipedream + Microsoft 365)

- **Statut** : Accepted (documenté a posteriori) · **Date** : 2026-07-01 · **Décideur** : Alexandre Gauthier
- **Réf.** : [Spec Inbox](../../02-product/specs-domaines/inbox-communication.md) · [`PIPEDREAM_ARCHITECTURE.md`](../../PIPEDREAM_ARCHITECTURE.md)

## Contexte
L'inbox contextualisée est un job cœur ([JTBD-2](../../01-discovery/jobs-to-be-done.md)). Une première intégration **Microsoft 365** (OAuth Graph, delta sync, webhooks) existait. Le besoin d'élargir (Gmail, connecteurs multiples) et de simplifier l'intégration a conduit à adopter **Pipedream** comme provider moderne, sans jeter l'existant MS365.

## Décision
Supporter **deux providers email en parallèle**, avec une **abstraction unifiée** côté frontend :
- **Pipedream** (moderne, primaire) : webhooks signés HMAC-SHA256, actions send/reply/forward/sync, multi-provider (Outlook/Gmail) → table `membrane_synced_emails` (`provider_message_id`).
- **Microsoft 365** (legacy, fallback) : OAuth Graph direct → table `synced_emails` (`ms_message_id`).
- Le frontend expose un modèle `UnifiedEmail` et distingue la source via `isMembraneEmail()`.

## Alternatives envisagées
1. **Tout MS365, direct** — contrôle fin, mais un connecteur par service à construire/maintenir, périmètre limité à Microsoft. Rejeté pour l'extensibilité.
2. **Tout Pipedream, migration immédiate** — plus simple à terme, mais aurait cassé l'intégration MS365 existante et fonctionnelle. Rejeté (risque + gaspillage).
3. **Dual-provider transitoire** — deux chemins à maintenir un temps, mais migration sans rupture. **Retenu.**

## Conséquences
- ✅ Extensibilité (Gmail et autres via Pipedream) sans réécrire un connecteur par service.
- ✅ Pas de rupture pour l'existant MS365.
- ✅ Webhooks signés (HMAC) → sécurité d'ingestion.
- ⚠️ **Dette transitoire** : deux modèles de données, tables `membrane_*` au **nommage temporaire** (rename + backfill à planifier — Q3 du [PRD](../../02-product/prd-cahier-des-charges.md)).
- ⚠️ Fonctionnalités IA inégales (`ai_summary`/`ai_action_items` présents côté MS365, à porter côté Pipedream).
- ⚠️ Dépendance à Pipedream (coût, rate-limit, rupture d'API) — voir [Risk Register](../../06-gouvernance/risk-register.md).
- ➡️ Cible : converger vers un modèle unique une fois la parité atteinte.
