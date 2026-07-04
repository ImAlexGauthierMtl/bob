# North Star Metric & arbre de métriques — CDE

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Couche** : 00 · Vision · **Dernière MAJ** : 2026-07-01

Une *North Star Metric* (NSM) est la **mesure unique** qui capture le mieux la valeur que le produit délivre au client. Chez les grandes entreprises tech, elle sert d'arbitre : toute initiative doit expliquer comment elle la fait bouger.

## North Star Metric

> ## 🌟 Actions à valeur exécutées par Bob et validées par un humain, par semaine active
> *(« Human-approved Bob actions per week »)*

**Pourquoi celle-ci ?**

- Elle capture le **cœur de la proposition de valeur** : Bob ne *suggère* pas, il *exécute*. Une action = un email envoyé, un contact créé/mis à jour, un devis préparé, une opportunité avancée, une activité complétée.
- Le filtre **« validée par un humain »** garde le produit honnête : une action non voulue, annulée au *gate* de confirmation, ne compte pas. On mesure la valeur *acceptée*, pas le volume brut.
- Elle est **instrumentable dès aujourd'hui** : le `usage-backend-api` enregistre déjà chaque exécution dans un ledger append-only (`UsageTransaction`) avec `trigger_source`, `correlation_id`, et le runtime trace `confirmed_executions` par run.

**Ce qu'elle n'est pas** : ni le nombre d'utilisateurs (vanity), ni le nombre de messages envoyés à Bob (activité ≠ valeur), ni le MRR (résultat, pas cause).

## Arbre de métriques (input metrics)

La NSM se décompose en leviers actionnables. C'est sur ces *input metrics* que les équipes travaillent.

```
       NSM : Actions Bob validées / semaine active
        = Utilisateurs actifs  ×  Actions validées par utilisateur actif
                 │                          │
     ┌───────────┴───────────┐    ┌─────────┴──────────────┐
   Acquisition            Rétention   Taux de              Taux de
   (nouveaux              (WAU/MAU)   sollicitation        confirmation
    tenants actifs)                   (actions proposées   (proposées → validées)
                                       / utilisateur)
```

### Niveau 1 — Adoption
| Métrique | Définition | Source |
|---|---|---|
| **Tenants actifs** | Tenants avec ≥1 utilisateur actif dans la semaine | `Tenant` + auth |
| **WAU / MAU** | Ratio d'engagement (viscosité) | sessions auth |
| **Time-to-first-value** | Délai entre création du tenant et 1ʳᵉ action Bob validée | ledger usage |

### Niveau 2 — Profondeur d'usage
| Métrique | Définition | Source |
|---|---|---|
| **Actions proposées / utilisateur actif** | Volume que Bob met sur la table | `AgentRun.actions` |
| **Taux de confirmation** | `confirmed / (confirmed + cancelled)` au *gate* | `AgentConfirmation.status` |
| **Mix d'actions** | Répartition par famille d'outils (email, CRM, KB…) | `metadata.routing` |
| **Couverture domaines** | Nb de domaines (CRM/inbox/KB/platform) touchés par tenant | usage |

### Niveau 3 — Confiance & qualité (contre-métriques)
| Métrique | Pourquoi on la surveille | Cible |
|---|---|---|
| **Taux d'annulation au gate** | Trop haut = Bob propose des actions non pertinentes | ↓ |
| **Taux d'action reprise/corrigée** | L'humain doit refaire après Bob = valeur négative | ↓ |
| **Runs en échec / dégradés** | Fiabilité du runtime (`status = failed \| degraded`) | < 2 % |
| **Latence P95 d'un run** | Un agent lent n'est pas utilisé | voir [SLO](../04-technique/slo-observability.md) |
| **COGS par action** | Coût d'inférence par action validée (marge) | suivi via `CostRateCard` |

## Garde-fous (guardrail metrics)

Une NSM qu'on optimise sans garde-fou dérape. On ne « gonfle » **jamais** la NSM en :
- réduisant le nombre de confirmations demandées sur des actions sensibles (sécurité > volume) ;
- comptant des actions techniques internes (`bob_runtime_status`) comme des actions à valeur ;
- dégradant la qualité des données CRM (une mise à jour fausse compte négativement une fois corrigée).

## Cadence de revue

- **Hebdomadaire** (façon Amazon WBR) : NSM + arbre d'input metrics + contre-métriques.
- **Trimestrielle** : recalibrage des cibles OKR — voir [OKR](../02-product/okr.md).

> `[À VALIDER]` Les cibles chiffrées (WAU/MAU, seuils) ne sont pas encore posées faute de données de production. Ce document définit *quoi* mesurer ; les *seuils* seront fixés après les premières semaines de trafic réel.
