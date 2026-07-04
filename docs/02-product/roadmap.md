# Roadmap — CDE

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Couche** : 02 · Produit · **Dernière MAJ** : 2026-07-01
> Roadmap **orientée résultats** (outcomes), pas liste de features. Organisée en 3 horizons (façon *Now / Next / Later*). Les dates sont indicatives `[À VALIDER]`.

## Principe

On ne s'engage sur des dates fermes qu'au plus proche (Now). Plus loin, on s'engage sur des **thèmes** et des **résultats visés**. Chaque item se relie à un objectif du [PRD](prd-cahier-des-charges.md) et aux [OKR](okr.md).

## État de départ (juillet 2026)

CDE est **fonctionnel en local (Docker)**, conforme v1.4, avec les 5 domaines opérationnels à des degrés divers. Le socle CRM+Inbox est solide ; le différenciateur (Bob) est en cours de durcissement (migration hors LangGraph, mémoire RAG, UI de config).

---

## 🔴 NOW — Trimestre en cours (T3 2026) : « Fiabiliser et mettre en production »

**Résultat visé** : CDE tourne en production pour les premiers utilisateurs, avec un Bob fiable et traçable sur le cœur CRM+email.

| Thème | Livrables | Réf. |
|---|---|---|
| **Production-ready** | Durcir CI/CD (Harbor, K8s, Cosign), déploiement dev→staging→prod | [Launch Readiness](../05-delivery/launch-readiness.md) |
| **Runtime Bob v2** | Finir la migration hors LangGraph, retirer les stubs, tests provider réels | [ADR-0004](../04-technique/adr/adr-0004-runtime-agentique-maison-vs-langgraph.md) |
| **Mémoire RAG** | Activer Milvus en prod, fiabiliser recherche/sensibilité | [Runtime](../04-technique/agentic-runtime-design.md) |
| **Observabilité IA** | Traces OTel par appel provider, SLO run posés | [SLO](../04-technique/slo-observability.md) |
| **Confiance** | Instrumenter NSM + contre-métriques (confirmation, annulation, reprise) | [North Star](../00-vision/north-star-metric.md) |

## 🟠 NEXT — 2 trimestres (T4 2026 – T1 2027) : « Approfondir la délégation »

**Résultat visé** : l'utilisateur délègue davantage à Bob, avec plus d'autonomie sur les tâches à faible risque.

- **Autonomie encadrée** : mode `auto` par défaut sur les actions *read* et les tâches faible risque (labellisation, mise à jour, brouillons) ; l'humain ne valide que l'exception.
- **Inbox IA généralisée** : `ai_summary` + `ai_action_items` sur **tous** les providers (Pipedream inclus) ; fiabiliser la liaison auto email→contact/org.
- **Workflows événementiels** : orchestrateur complet (webhook → run → steps), builder d'automatisation utilisable par un admin.
- **Surfaces de configuration Bob** : UI de gestion agents/skills/tools + gouvernance (admin + préférences).
- **Analytics manager** : dashboard pipeline + usage/coût lisible.

## 🟢 LATER — Horizon 6-12 mois+ (T2 2027+) : « Vers le multi-agents »

**Résultat visé** : une équipe d'agents spécialisés se répartit les comptes, coordonnée par le BCC.

- **BCC / multi-agents** : agents administratifs, skills importables à grande échelle, client map opérationnelle.
- **Mode voix** (`voice_phone`) en production.
- **Marketplace de skills** (interne puis tierce).
- **Génération de contenu KB** assistée par LLM (si validé).
- **Expansion des intégrations MCP** (au-delà de Slack/Teams/Drive/calendrier).

---

## Vue synthétique

```
NOW (T3-26)         NEXT (T4-26 → T1-27)        LATER (T2-27+)
Fiabiliser  ───────► Approfondir la ───────────► Multi-agents
& prod              délégation
─ CI/CD prod        ─ auto faible risque         ─ BCC / fleet d'agents
─ Runtime v2        ─ inbox IA généralisée       ─ voix prod
─ RAG Milvus        ─ workflows événementiels    ─ marketplace skills
─ obs. IA           ─ UI config Bob              ─ génération KB
─ NSM instrumentée  ─ analytics manager          ─ + intégrations MCP
```

## Ce qu'on ne fait PAS maintenant (anti-roadmap)
- Mobile natif · multi-devise avancée · personnalisation UI poussée · connecteurs sur-mesure hors MCP. Ces choix protègent le focus sur le différenciateur (délégation sûre). Voir [Tenets](../00-vision/tenets.md) (tenet 6 : vertical d'abord).

> **Dépendances de risque** : la roadmap NEXT (autonomie `auto`) dépend de la maturité de l'observabilité et des contre-métriques du NOW. On n'ouvre pas l'autonomie tant que la qualité n'est pas mesurée. Voir [Risk Register](../06-gouvernance/risk-register.md).

> `[À VALIDER]` Séquencement et dates à confirmer selon capacité (équipe actuelle), retours des premiers utilisateurs, et priorités business du fondateur.
