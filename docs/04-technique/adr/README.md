# Architecture Decision Records (ADR) — CDE

> **Couche** : 04 · Technique · **Dernière MAJ** : 2026-07-01

Un **ADR** capture une décision d'architecture **structurante** : son contexte, les options envisagées, le choix retenu et ses conséquences. Format léger (Michael Nygard). Un ADR est **immuable** une fois accepté ; on ne le modifie pas, on le **remplace** par un nouveau (statut `Superseded by ADR-XXXX`).

## Pourquoi des ADRs
- Garder la **mémoire du « pourquoi »** : dans 6 mois, on saura pourquoi tel choix a été fait.
- Éviter de rejouer sans fin les mêmes débats.
- Onboarder vite : lire les ADRs = comprendre l'ossature.

## Statuts
`Proposed` → `Accepted` → (`Deprecated` | `Superseded by ADR-XXXX`)

## Index

| # | Titre | Statut |
|---|---|---|
| [0001](adr-0001-architecture-deux-tiers-b4f-backend.md) | Architecture à deux tiers B4F / Backend | Accepted |
| [0002](adr-0002-event-bus-redis-inter-backend.md) | Event Bus Redis pour la synchro inter-backend | Accepted |
| [0003](adr-0003-multi-tenant-jwt-tenant-id.md) | Multi-tenant par `tenant_id` porté dans le JWT | Accepted |
| [0004](adr-0004-runtime-agentique-maison-vs-langgraph.md) | Runtime agentique maison plutôt que LangGraph | Accepted |
| [0005](adr-0005-dual-provider-email-pipedream-ms365.md) | Email dual-provider (Pipedream + Microsoft 365) | Accepted |

> Ces ADRs **documentent a posteriori** des décisions déjà prises et visibles dans le code. Les prochains ADRs devront être écrits **avant** implémentation. Modèle de fichier : copier un existant et adapter (Contexte / Décision / Alternatives / Conséquences).
