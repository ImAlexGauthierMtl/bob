# OKR — CDE

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Couche** : 02 · Produit · **Dernière MAJ** : 2026-07-01
> Objectives & Key Results (Google/Intel). L'**Objective** est qualitatif et ambitieux ; les **Key Results** sont mesurables. Cadence trimestrielle. Les cibles chiffrées sont à poser après les premières données de prod `[À VALIDER]`.

## Comment on utilise les OKR ici
- 1 objectif = 1 cap trimestriel. 3-4 KR max, chacun chiffré et vérifiable.
- Un KR n'est pas une tâche (« livrer X »), c'est un **résultat** (« X% des Y font Z »).
- Score en fin de trimestre : 0.0–1.0. Viser 0.7 (si tout est à 1.0, les OKR n'étaient pas assez ambitieux).
- Tout KR se relie à l'[arbre de métriques](../00-vision/north-star-metric.md).

---

## T3 2026 — « Fiabiliser et passer en production »

### Objective 1 — CDE est en production et digne de confiance
- **KR1.1** — Pipeline CI/CD complet vert (test→build→verify→deploy→smoke) sur dev **et** staging. `[cible : 100%]`
- **KR1.2** — Taux de runs Bob en échec/dégradés **< 2 %** sur 2 semaines glissantes.
- **KR1.3** — **0** incident d'isolation inter-tenant ; **0** action irréversible exécutée sans confirmation.
- **KR1.4** — Latence run Bob **P95 < [cible ms]** `[À VALIDER via SLO]`.

### Objective 2 — Les premiers utilisateurs tirent de la valeur réelle
- **KR2.1** — **N** tenants actifs avec ≥ 1 action Bob validée / semaine `[cible N]`.
- **KR2.2** — *Time-to-first-value* médian **< [cible]** (création tenant → 1ʳᵉ action validée).
- **KR2.3** — Taux de confirmation (proposé→validé) **> [cible %]**.

---

## T4 2026 — « Approfondir la délégation en sécurité »

### Objective 3 — L'utilisateur délègue plus, sans perdre confiance
- **KR3.1** — Actions Bob validées / utilisateur actif **× [facteur]** vs T3 (NSM en hausse).
- **KR3.2** — Taux d'annulation au gate **< [cible %]** ET taux d'action reprise/corrigée **< [cible %]** (la hausse de volume ne dégrade pas la qualité).
- **KR3.3** — Mode `auto` activé sur les tâches faible risque pour **X %** des tenants, sans hausse des incidents.

### Objective 4 — L'email est pleinement contextualisé
- **KR4.1** — **> [cible %]** des emails entrants rattachés automatiquement au bon contact/org.
- **KR4.2** — Résumé IA + action items disponibles sur **100 %** des providers (Pipedream + MS365).

---

## T1 2027 — « Outiller les managers & préparer le multi-agents »

### Objective 5 — Les managers pilotent avec des données fiables
- **KR5.1** — **X %** des tenants « manager » consultent l'analytics/usage chaque semaine.
- **KR5.2** — COGS par action validée **≤ [cible]** (marge sous contrôle).
- **KR5.3** — **N** workflows d'équipe actifs déclenchés par événement, taux de succès **> [cible %]**.

---

## Traçabilité OKR → Vision

| Objective | Sert le tenet / l'objectif produit | NSM impactée |
|---|---|---|
| O1 Production & confiance | Tenets 1,2,4 · O5 PRD | Contre-métriques (fiabilité) |
| O2 Valeur réelle | O1,O3 PRD | NSM directe |
| O3 Déléguer plus | Différenciateur (JTBD-4) | NSM directe |
| O4 Email contextualisé | O2 PRD (JTBD-2) | Input : actions proposées |
| O5 Managers & multi-agents | O4 PRD (JTBD-7) | Rétention, marge |

> **Discipline OKR** : on ne rajoute pas un objectif en cours de trimestre. Les cibles `[À VALIDER]` sont posées lors du premier *planning* avec données réelles, puis revues en revue trimestrielle. Voir [Decision Log](../06-gouvernance/decision-log.md).
