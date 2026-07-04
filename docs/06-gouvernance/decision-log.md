# Decision Log — CDE

> **Statut** : Living · **DRI** : Alexandre Gauthier · **Couche** : 06 · Gouvernance · **Dernière MAJ** : 2026-07-01
> Journal chronologique des **décisions** (produit, business, organisation) qui ne sont pas des décisions d'architecture pure (celles-ci vivent dans les [ADRs](../04-technique/adr/)). But : tracer *quoi*, *quand*, *pourquoi*, *par qui* — et ne pas rejouer les mêmes débats.

## Comment l'utiliser
- Une ligne par décision. On **n'efface pas** ; une décision annulée est marquée `Révoquée` avec un renvoi vers celle qui la remplace.
- Les **questions ouvertes** (non tranchées) sont listées en bas ; elles remontent du [PRD §9](../02-product/prd-cahier-des-charges.md#9-hors-périmètre--questions-ouvertes).

## Décisions actées

| # | Date | Décision | Pourquoi | Type | Réf. |
|---|---|---|---|---|---|
| D-001 | 2026-07-01 | Adopter la norme d'architecture **v1.4** comme contrat non négociable | cohérence, imposable, qualité | Archi | [v1.4](../regles-architecture-deploiement.md) |
| D-002 | 2026-07-01 | Reconstruire **la documentation à rebours** en corpus 7 couches | projet démarré sans plan ; besoin de traçabilité | Organisation | [README](../README.md) |
| D-003 | 2026-07-01 | Placer **Bob (exécution agentique) au centre** du produit, pas un chatbot greffé | différenciateur vs CRM+IA classiques | Produit | [Vision](../00-vision/product-vision.md) |
| D-004 | 2026-07-01 | **Confirmation humaine obligatoire** sur toute action sensible | confiance = actif n°1 | Produit / Sûreté | [Tenet 1](../00-vision/tenets.md) |
| D-005 | 2026-07-01 | NSM = **actions Bob validées / semaine active** | mesure la valeur acceptée, pas l'activité | Produit | [NSM](../00-vision/north-star-metric.md) |
| D-006 | 2026-07-01 | **Vertical B2B d'abord**, refuser le générique « pour le principe » | focus, profondeur > largeur | Produit | [Tenet 6](../00-vision/tenets.md) |
| D-007 | 2026-07-01 | Lancer d'abord un **pilote fermé**, pas une prod grand public | 4 bloquants ouverts | Delivery | [Launch Readiness](../05-delivery/launch-readiness.md) |

*(Décisions d'architecture associées : [ADR-0001](../04-technique/adr/adr-0001-architecture-deux-tiers-b4f-backend.md) à [ADR-0005](../04-technique/adr/adr-0005-dual-provider-email-pipedream-ms365.md).)*

## Questions ouvertes (à trancher)

| # | Question | Impact | Piste |
|---|---|---|---|
| Q-001 | **Modèle de tarification** définitif (siège + usage ? seuils ?) | Business (R11) | déduire du ledger + plans ; valider par entretiens |
| Q-002 | Quand ouvrir le mode **`auto`** par défaut (seuil de risque acceptable) ? | Produit / Sûreté | après instrumentation NSM + contre-métriques |
| Q-003 | Stratégie de **rename `membrane_*`** (migration + backfill) | Technique | planifier en NEXT |
| Q-004 | Généraliser **résumé/action-items IA** à tous les providers email | Produit | NEXT |
| Q-005 | Priorité **BCC/multi-agents** vs approfondissement du cœur | Roadmap | arbitrer avec données d'usage |
| Q-006 | **Consolidation de services** vs automatisation de l'ops (R4) | Ops | selon capacité équipe |
| Q-007 | **PostgreSQL RLS** en défense en profondeur du multi-tenant ? | Sécurité | évaluer en durcissement (R1) |
| Q-008 | **Génération d'articles KB par LLM** : implémenter ou retirer l'exigence ? | Produit | trancher (EF-KB-7) |

## Convention d'ajout
Nouvelle décision → nouvelle ligne (date, décision, pourquoi, type, réf.). Décision structurante d'architecture → écrire un **ADR** et référencer ici. Question tranchée → passer de la table « ouvertes » à « actées ».
