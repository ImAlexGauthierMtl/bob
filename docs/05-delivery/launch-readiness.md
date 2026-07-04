# Launch Readiness Review — CDE

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Couche** : 05 · Delivery · **Dernière MAJ** : 2026-07-01
> Revue de préparation au lancement (façon Google *Launch/Production Readiness Review*). Chaque ligne est un **go/no-go** à statuer honnêtement avant d'ouvrir le produit à de vrais clients en production.

## Légende
✅ Prêt · 🟡 Partiel / en cours · ⛔ Manquant · ❓ À vérifier

## 1. Fonctionnel (le produit fait ce qu'il promet)
| Item | Statut | Note |
|---|---|---|
| Cœur CRM (contacts/orgs/opp/devis/activités) | ✅ | fonctionnel en local |
| Inbox dual-provider + smart labels | ✅ | 🟡 liaison auto à fiabiliser |
| Bob : conversation + tool-loop + confirmation | ✅ | invariants de sûreté en place |
| Bob : mémoire RAG | 🟡 | dépend de Milvus en prod |
| Workflows événementiels | 🟡 | orchestrateur à finaliser |
| KB (articles/catégories/recherche/feedback) | ✅ | génération LLM non implémentée |
| Usage/facturation (ledger + rate cards) | ✅ | brancher aux plans |

## 2. Fiabilité & exploitation
| Item | Statut | Note |
|---|---|---|
| Probes (`liveness/readiness/startup/health/metrics`) | ✅ | sur chaque API |
| Logs structurés + traces OTel | ✅ | 🟡 traces provider LLM à ajouter |
| Dashboards (santé/runtime/usage/NSM) | ⛔ | [SLO §5](../04-technique/slo-observability.md) |
| Alertes P0-P2 | ⛔ | à instrumenter |
| SLO cibles chiffrées | ⛔ | à poser sur données réelles |
| Runbooks / on-call | ⛔ | à créer |
| Template postmortem | ⛔ | à créer |
| Dégradation propre (fallback LLM/Milvus) | ✅ | tenet 7 |

## 3. Sécurité & conformité
| Item | Statut | Note |
|---|---|---|
| HTTPS / TLS wildcard / backends non exposés | ✅ | via gateway |
| JWT + RBAC | ✅ | envisager rotation/révocation, RS256 |
| **Tests anti-fuite inter-tenant en CI** | ⛔ | **bloquant** — invariant n°1 |
| Chiffrement au repos (tokens OAuth, emails) | ❓ | à vérifier / ajouter |
| Défense prompt-injection | 🟡 | gating présent, sanitation à ajouter |
| Threat model traité | 🟡 | [Threat Model](../04-technique/threat-model.md) — durcissements ouverts |
| DPIA / RGPD (rétention, effacement) | 🟡 | [DPIA](../06-gouvernance/privacy-dpia.md) — à outiller |
| Pentest externe | ⛔ | recommandé avant scale |

## 4. Déploiement
| Item | Statut | Note |
|---|---|---|
| CI/CD parent/child | ✅ | template v1.0.70 |
| Build Kaniko + Harbor | 🟡 | attend provisioning Harbor + robot accounts |
| Verify (Trivy + Cosign) | 🟡 | dépend infra Harbor |
| Deploy Helm dev/staging/prod | 🟡 | staging/prod attend provisioning K8s |
| Migrations Lease K8s | ✅ | downgrade testé |
| Feature flags / kill-switch par tenant | 🟡 | `Tenant.settings` présent, à généraliser |

## 5. Qualité
| Item | Statut | Note |
|---|---|---|
| Couverture ≥ 85 % (back & front) | ✅ | seuil CI |
| Import-linter 0 violation | ✅ | 51 contrats |
| E2E Playwright | 🟡 | smoke ; à étendre aux parcours critiques |
| Tests des invariants de sûreté runtime | 🟡 | à compléter |

## 6. Business & support `[À VALIDER]`
| Item | Statut |
|---|---|
| Modèle de tarification défini | ⛔ |
| Conditions d'utilisation / DPA clients | ⛔ |
| Support / onboarding client | ⛔ |
| Facturation opérationnelle (plans → entitlements) | 🟡 |

## Verdict global
**NO-GO pour une prod client à grande échelle** en l'état. **GO possible pour un pilote fermé** (quelques tenants de confiance, en supervision rapprochée) **une fois traités les 4 bloquants** :

1. ⛔ **Tests anti-fuite inter-tenant en CI** (sécurité).
2. ⛔ **Dashboards + alertes + SLO** (exploitabilité).
3. 🟡→✅ **CI/CD prod** (Harbor/K8s provisionnés, pipeline vert bout en bout).
4. 🟡→✅ **Runtime Bob v2** (migration finie, invariants testés).

Puis, avant le **scale** : pentest externe, chiffrement au repos, défense prompt-injection, DPIA outillée, tarification & CGU.

> Cette revue est **vivante** : on la met à jour à chaque jalon et on rejoue le go/no-go. Priorités croisées avec le [Risk Register](../06-gouvernance/risk-register.md).
