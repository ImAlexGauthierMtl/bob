# SLO & Observabilité — CDE

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Couche** : 04 · Technique · **Dernière MAJ** : 2026-07-01
> Objectifs de niveau de service (SLO) et dispositif d'observabilité. Les cibles chiffrées sont **proposées** et à calibrer sur données réelles `[À VALIDER]`.

## 1. Dispositif d'observabilité (existant)

| Pilier | Implémentation |
|---|---|
| **Health/probes** | `/liveness`, `/readiness`, `/startup`, `/health` (avec dépendances + latences), `/metrics` (Prometheus) sur **chaque** API |
| **Logs** | JSON structuré (`structlog` + `JSONRenderer`), contextvars `trace_id`/`request_id`/`tenant_id`/`user_id`, stdout |
| **Traces** | OpenTelemetry → **Alloy** (Grafana) via OTLP gRPC `:4317` ; propagation `traceparent` (W3C) sur HTTP + `trace_id` dans events Redis |
| **Smoke-test** | post-deploy : endpoints répondent, `/health` ≠ unhealthy, dépendances présentes, jamais de 5xx |

> Chantier ouvert : **traces OTel par appel provider LLM** dans le runtime (voir [Runtime](agentic-runtime-design.md) §10).

## 2. SLI → SLO (proposés)

### Disponibilité
| Service | SLI | SLO cible `[À VALIDER]` |
|---|---|---|
| Gateway / Frontend | % requêtes non-5xx | 99.9 % / mois |
| B4F (par service) | % requêtes non-5xx | 99.9 % |
| Backends | readiness up | 99.9 % |

### Latence
| Parcours | SLI | SLO cible `[À VALIDER]` |
|---|---|---|
| API B4F CRUD | P95 temps réponse | < 300 ms |
| Dashboard CRM (composition) | P95 | < 800 ms (5 backends en parallèle) |
| **Run Bob (bout en bout)** | P95 | **< X s** (à poser ; dominé par le LLM + tool-loop) |
| Sync email (webhook→visible) | P95 | < quelques secondes |

### Fiabilité IA (spécifique CDE)
| SLI | SLO cible `[À VALIDER]` |
|---|---|
| Runs en échec (`status=failed`) | < 1 % |
| Runs dégradés (`status=degraded`) | < 2 % |
| Taux de fallback provider (Fireworks→local) | surveillé, alerte si pic |
| Respect du gating (write sans confirmation) | **0** (invariant dur) |

### Qualité produit (relié à la [NSM](../00-vision/north-star-metric.md))
Taux de confirmation, taux d'annulation au gate, taux d'action reprise — suivis en continu (contre-métriques).

## 3. Error budget

- SLO disponibilité 99.9 %/mois ⇒ **~43 min** d'indisponibilité budgétée/mois.
- **Politique** : si l'error budget est épuisé, on gèle les déploiements de features et on priorise la fiabilité jusqu'à reconstitution. (Principe SRE.)

## 4. Alerting (à instrumenter)

| Condition | Sévérité | Action |
|---|---|---|
| `/health` dégradé sur un service | P2 | investiguer la dépendance en cause |
| Pic de 5xx / latence P95 hors SLO | P1 | rollback possible (helm) |
| Taux de runs échoués > seuil | P1 | vérifier Fireworks / tool registry |
| Pic de fallback provider | P2 | vérifier disponibilité/quota Fireworks |
| COGS/action anormal | P2 | vérifier boucle/outils, `CostRateCard` |
| Tentative d'accès cross-tenant détectée | **P0** | incident sécurité immédiat |

## 5. Dashboards recommandés
1. **Santé plateforme** : disponibilité/latence par service, dépendances `/health`.
2. **Runtime Bob** : runs (succès/échec/dégradé), latence, fallback, confirmations (pending/confirmed/cancelled).
3. **Usage & coût** : `UsageTransaction` par service/tenant/intent, COGS, marge.
4. **Produit / NSM** : actions validées, taux de confirmation, annulations.

## 6. Postmortems

Tout incident P0/P1 déclenche un **postmortem sans blâme** (façon Google/SRE) : timeline, impact, cause racine, ce qui a marché/pas marché, actions correctives datées. Le template vit dans les [runbooks de gouvernance](../06-gouvernance/) `[À CRÉER]`. Objectif : apprendre, pas punir.

## 7. Prochaines étapes
- Poser les **cibles chiffrées** après 2-4 semaines de trafic réel.
- Finaliser les **traces provider** dans le runtime.
- Brancher Alloy → backend de métriques/logs de prod (Grafana Cloud / Loki / Prometheus).
- Créer les **dashboards** et **alertes** ci-dessus.
