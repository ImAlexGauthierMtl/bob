# Plan technique d'exécution — CDE

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Couche** : 05 · Delivery · **Dernière MAJ** : 2026-07-01
> Comment on construit et livre. Relie la [Roadmap](../02-product/roadmap.md) produit aux chantiers d'ingénierie concrets, avec leur définition de « terminé ».

## 1. Stratégie d'ingénierie

- **Contrat d'architecture** : la norme [v1.4](../regles-architecture-deploiement.md) est non négociable ; tout écart passe par un [ADR](../04-technique/adr/).
- **Trunk-based léger** + revue ; CI bloquante (tests ≥ 85 %, import-linter 0 violation).
- **Qualité outillée** : Clean Architecture vérifiée par import-linter, coverage badge, E2E Playwright sur parcours critiques.
- **Livraison incrémentale** : dev auto, staging/prod manuel ; migrations Alembic via Lease K8s.

## 2. Environnements

| Env | Déploiement | Usage |
|---|---|---|
| **Local** | `docker-compose` (postgres, pgbouncer, redis, alloy + 22 services) | dev quotidien |
| **Dev (K8s)** | auto sur merge (Helm) | intégration continue |
| **Staging** | manuel | validation pré-prod |
| **Prod** | manuel | clients |

## 3. Pipeline CI/CD (existant)

`discover` (génère le child pipeline en scannant `apis/`) → **child** : `test` → `build` (Kaniko→Harbor, tag SHA) → `verify` (Trivy + Cosign) → `deploy` (Helm) → `smoke-test` → (`rollback` manuel). Template partagé `ci-cd-unified-template v1.0.70`.

## 4. Chantiers techniques (alignés Roadmap NOW/NEXT)

### NOW — Fiabiliser & mettre en prod
| Chantier | Definition of Done |
|---|---|
| **Durcir CI/CD prod** | pipeline vert de bout en bout sur dev+staging ; Harbor + robot accounts ; secrets GitLab/K8s configurés ; TLS wildcard via cert-manager |
| **Runtime Bob v2** | stubs de contrat remplacés par tests provider réels/fakes ; imports langchain/langgraph retirés ; invariants de sûreté couverts par tests |
| **Mémoire RAG prod** | Milvus provisionné ; recherche + sensibilité fiabilisées ; jobs de rebuild opérationnels |
| **Observabilité IA** | traces OTel par appel provider ; dashboards Santé/Runtime/Usage ; alertes P0-P2 |
| **Instrumentation NSM** | actions validées, taux de confirmation/annulation/reprise mesurés depuis le ledger + runs |
| **Tests anti-fuite tenant** | test CI bloquant vérifiant l'isolation `tenant_id` sur chaque backend |

### NEXT — Approfondir la délégation
| Chantier | Definition of Done |
|---|---|
| **Autonomie faible risque** | mode `auto` sur read + tâches faible risque, sans hausse d'incidents ; kill-switch par tenant |
| **Inbox IA généralisée** | `ai_summary`/`ai_action_items` sur Pipedream ; liaison auto email→contact fiabilisée + correction manuelle |
| **Workflows événementiels** | orchestrateur webhook→run→steps complet ; builder utilisable |
| **UI config Bob** | écrans agents/skills/tools + gouvernance (admin + préférences) |
| **Rename `membrane_*`** | migration + backfill ; modèle email convergé |

## 5. Definition of Ready / Done (transverse)

**Ready** (avant de coder) : exigence référencée dans le [PRD](../02-product/prd-cahier-des-charges.md), critères d'acceptation clairs, impact sécurité/tenant évalué, ADR si structurant.

**Done** : code + tests (≥ 85 %) + import-linter vert + E2E si parcours critique + doc mise à jour (PRD/spec/ADR) + observabilité (logs/traces/metrics) + revue + déployé en dev.

## 6. Dette technique suivie
- Migration hors LangGraph (en cours) · rename `membrane_*` · relations N:N JSON (activités) · consolidation KB relationnel/vectoriel · cibles SLO à poser · design system à formaliser. Voir [Decision Log](../06-gouvernance/decision-log.md) et [Risk Register](../06-gouvernance/risk-register.md).

## 7. Capacité & organisation `[À VALIDER]`
Le nombre de services (22) est élevé pour l'équipe actuelle. Décision à prendre : jusqu'où automatiser l'ops (templates, scaffolding d'API) vs consolider certains services. À arbitrer avec le fondateur.
