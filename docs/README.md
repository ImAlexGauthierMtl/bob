# 📚 Documentation Produit & Technique — Croo Digital Experience (CDE)

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Dernière MAJ** : 2026-07-01

Ce dossier est le **corpus documentaire** de CDE, structuré comme le ferait une équipe produit/ingénierie d'une grande entreprise tech (Amazon *Working Backwards*, Google *PRD + Design Doc*, ADRs, postmortems). Il a été reconstruit **à rebours** à partir du code réel, puis organisé en couches.

## Principe directeur : la chaîne de traçabilité

Chaque document répond à **une** question, et chaque couche s'appuie sur la précédente. Une décision technique doit toujours pouvoir remonter jusqu'à un problème utilisateur, lui-même au service de la vision.

```
Vision  ──►  Problème  ──►  Exigence  ──►  Design  ──►  Décision technique  ──►  Livraison  ──►  Exploitation
 (00)         (01)          (02)          (03)          (04)                   (05)            (06)
```

## Carte du corpus

| Couche | Question | Documents |
|---|---|---|
| **[00 · Vision](00-vision/)** | Pourquoi existons-nous ? | [Product Vision](00-vision/product-vision.md) · [North Star Metric](00-vision/north-star-metric.md) · [Tenets](00-vision/tenets.md) |
| **[01 · Discovery](01-discovery/)** | Pour qui, quel problème ? | [PR/FAQ](01-discovery/prfaq.md) · [Personas](01-discovery/personas.md) · [Jobs-to-be-Done](01-discovery/jobs-to-be-done.md) · [Analyse concurrentielle](01-discovery/analyse-concurrentielle.md) |
| **[02 · Produit](02-product/)** | Que construit-on ? | [PRD / Cahier des charges](02-product/prd-cahier-des-charges.md) · [Specs par domaine](02-product/specs-domaines/) · [Roadmap](02-product/roadmap.md) · [OKR](02-product/okr.md) |
| **[03 · Design](03-design/)** | À quoi ça ressemble ? | [Principes de design](03-design/design-principles.md) · [User flows](03-design/user-flows.md) |
| **[04 · Technique](04-technique/)** | Comment ça marche ? | [System Design Doc](04-technique/system-design-doc.md) · [Data Model](04-technique/data-model.md) · [Runtime agentique](04-technique/agentic-runtime-design.md) · [Threat Model](04-technique/threat-model.md) · [SLO & Observabilité](04-technique/slo-observability.md) · [ADRs](04-technique/adr/) |
| **[05 · Delivery](05-delivery/)** | Comment on livre ? | [Plan technique](05-delivery/plan-technique.md) · [Release Plan](05-delivery/release-plan.md) · [Launch Readiness](05-delivery/launch-readiness.md) |
| **[06 · Gouvernance](06-gouvernance/)** | Quels risques, quelle conformité ? | [Risk Register](06-gouvernance/risk-register.md) · [Privacy / DPIA](06-gouvernance/privacy-dpia.md) · [Decision Log](06-gouvernance/decision-log.md) |

## Documents techniques préexistants (source de vérité code)

Ces documents vivaient déjà dans le repo et restent la **référence normative** ; le corpus ci-dessus les référence sans les dupliquer :

- [`regles-architecture-deploiement.md`](regles-architecture-deploiement.md) — normes d'architecture & déploiement **v1.4** (contrat d'ingénierie)
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — diagramme et inventaire des services v2.0
- [`api-contracts.md`](api-contracts.md) — contrats d'API public/interne
- [`PIPEDREAM_ARCHITECTURE.md`](PIPEDREAM_ARCHITECTURE.md) — intégration Pipedream
- [`tool-governance-implementation-plan.md`](tool-governance-implementation-plan.md) — gouvernance des outils de Bob
- `../Cameleon/` — plan de refactor et matrice de conformité v1.4
- `../AGENTS.md` — instructions d'agent du dépôt

## Conventions

- **Langue** : français.
- **Statut** d'un document : `Draft` → `Review` → `Approved` → `Living` (mis à jour en continu).
- **DRI** (*Directly Responsible Individual*, façon Apple) : une personne responsable par document.
- **Versionnage** : ces `.md` sont versionnés dans git, au plus près du code qu'ils décrivent. Un changement d'architecture doit s'accompagner d'un ADR et, si besoin, d'une mise à jour du PRD.

## Comment lire ce corpus

- **Nouveau sur le projet ?** → [Product Vision](00-vision/product-vision.md) → [PR/FAQ](01-discovery/prfaq.md) → [PRD](02-product/prd-cahier-des-charges.md).
- **Ingénieur qui arrive ?** → [System Design Doc](04-technique/system-design-doc.md) → [Data Model](04-technique/data-model.md) → [ADRs](04-technique/adr/).
- **Investisseur / partie prenante externe ?** → [Product Vision](00-vision/product-vision.md) → [PR/FAQ](01-discovery/prfaq.md) → [Roadmap](02-product/roadmap.md).
