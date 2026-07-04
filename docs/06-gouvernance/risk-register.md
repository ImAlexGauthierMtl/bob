# Risk Register — CDE

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Couche** : 06 · Gouvernance · **Dernière MAJ** : 2026-07-01
> Registre des risques. Cotation : **Probabilité** (1-5) × **Impact** (1-5) = **Score**. Statut mis à jour en revue. Un risque sans **propriétaire** et sans **mitigation datée** est un risque non géré.

## Matrice de synthèse (top risques)

| # | Risque | P | I | Score | Catégorie |
|---|---|---|---|---|---|
| R1 | Fuite de données inter-tenant | 2 | 5 | **10** | Sécurité |
| R2 | Bob exécute une action non désirée (perte de confiance) | 3 | 5 | **15** | Produit / IA |
| R3 | Dépendance à Fireworks (coût/rate-limit/rupture) | 3 | 4 | **12** | Externe |
| R4 | Complexité opérationnelle (22 services, petite équipe) | 4 | 3 | **12** | Ops |
| R5 | Migration runtime hors LangGraph inachevée | 3 | 3 | 9 | Technique |
| R6 | Coût d'inférence non maîtrisé à l'échelle | 3 | 4 | **12** | Coût |
| R7 | Prompt injection via contenu externe (emails) | 3 | 4 | **12** | Sécurité / IA |
| R8 | Non-conformité RGPD (rétention, effacement) | 3 | 4 | **12** | Conformité |
| R9 | Dépendance Pipedream / MS Graph | 2 | 4 | 8 | Externe |
| R10 | Dette `membrane_*` / modèle email double | 3 | 2 | 6 | Technique |
| R11 | Marché/business model non validé | 3 | 4 | **12** | Business |
| R12 | Départ de la connaissance (bus factor = 1) | 3 | 4 | **12** | Organisation |

## Détail des risques majeurs

### R2 — Bob exécute une action non désirée · Score 15 · 🔴
- **Description** : une action erronée (email envoyé à tort, donnée corrompue) détruit la confiance ; l'utilisateur reprend tout à la main → le produit perd sa raison d'être.
- **Mitigations présentes** : gating de confirmation (tenet 1), readback, gouvernance d'outils, narration/traçabilité (tenet 2), bornes de boucle.
- **Actions** : instrumenter taux d'annulation/reprise ; kill-switch par tenant ; défense prompt-injection (voir R7) ; n'ouvrir le mode `auto` que sur faible risque et mesuré.
- **Propriétaire** : Fondateur · **Échéance** : NOW.

### R1 — Fuite inter-tenant · Score 10 · 🔴
- **Mitigations** : `tenant_id` filtré, backends non exposés, sensibilité RAG.
- **Actions (bloquantes)** : **tests anti-fuite en CI** ; envisager PostgreSQL RLS ; chiffrement au repos. Voir [Threat Model](../04-technique/threat-model.md), [ADR-0003](../04-technique/adr/adr-0003-multi-tenant-jwt-tenant-id.md).
- **Propriétaire** : Fondateur · **Échéance** : NOW (avant tout pilote).

### R3 — Dépendance Fireworks · Score 12 · 🟠
- **Mitigations** : abstraction provider + **fallback local**, `AGENT_RUNTIME_PROVIDER=auto`.
- **Actions** : capacité multi-provider (autre LLM en secours) ; alerte sur pic de fallback ; suivi coût/quota.

### R4 — Complexité opérationnelle · Score 12 · 🟠
- **Actions** : automatiser l'ops (scaffolding, templates) ; runbooks ; envisager consolidation de services peu sollicités ; dashboards santé.

### R6 — Coût d'inférence · Score 12 · 🟠
- **Mitigations** : bornes de boucle, ledger + `CostRateCard`.
- **Actions** : quotas/budget par tenant (lié aux plans) ; suivi COGS/action ; alerte anomalie.

### R7 — Prompt injection · Score 12 · 🟠
- **Actions** : traiter le contenu externe (emails, tickets) comme **non-fiable** ; sanitation/segmentation ; allow-list destinataires ; le gating limite déjà l'impact.

### R8 — RGPD · Score 12 · 🟠
- **Actions** : politique de rétention/purge (emails, mémoire `expires_at`, ledger), droit à l'effacement, DPA clients. Voir [DPIA](privacy-dpia.md).

### R11 — Business model non validé · Score 12 · 🟠
- **Actions** : entretiens utilisateurs (voir [Personas](../01-discovery/personas.md)), validation du willingness-to-pay, formaliser la tarification (`[À VALIDER]` récurrents).

### R12 — Bus factor · Score 12 · 🟠
- **Description** : la connaissance repose sur une personne. Ce corpus documentaire **est** une mitigation (réduit R12) — à maintenir vivant.
- **Actions** : garder la doc à jour, documenter les runbooks, envisager un binôme sur le runtime.

## Revue
Registre revu à chaque jalon (et en revue hebdo/mensuelle). Croisé avec [Launch Readiness](../05-delivery/launch-readiness.md). Un risque qui se matérialise → incident → postmortem → action corrective ajoutée ici.
