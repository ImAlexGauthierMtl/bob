# ADR-0004 — Runtime agentique maison plutôt que LangGraph

- **Statut** : Accepted (migration en cours) · **Date** : 2026-07-01 · **Décideur** : Alexandre Gauthier
- **Réf.** : [Runtime agentique](../agentic-runtime-design.md) · `../project-x/08-agentic-runtime/`

## Contexte
Bob doit exécuter des outils de façon **sûre** (confirmation sur actions sensibles), **gouvernée** (policies par risque/scope), **traçable** (narration + coût) et **résiliente** (fallback si LLM indisponible). Le projet a d'abord utilisé **LangGraph/LangChain**, puis a entrepris de le retirer au profit d'un runtime maison.

## Décision
Construire un **runtime agentique interne** (`agent-runtime-backend-api`) :
- Boucle d'exécution d'outils bornée (5 itérations, 3 outils/itération, 12 total).
- **Gating de confirmation** natif (`AgentConfirmation`, statut `requires_confirmation`) + readback.
- **Routage d'intent MCP déterministe** avant l'appel LLM.
- **Gouvernance d'outils** à 2 niveaux (policies admin + préférences user) intégrée à la boucle.
- Abstraction **provider** (`RuntimeProviderPort`) : Fireworks + **fallback local déterministe**.

Retrait progressif de LangGraph/LangChain (stubs de contrat → tests provider réels → nettoyage des imports legacy).

## Alternatives envisagées
1. **Rester sur LangGraph/LangChain** — écosystème riche, démarrage rapide ; mais abstractions lourdes, contrôle limité sur le gating de confirmation, le routage déterministe et la gouvernance fine ; dépendance à un framework tiers qui évolue vite. Rejeté.
2. **Framework agent tiers alternatif** (autre orchestrateur) — même famille de compromis (boîte noire vs contrôle). Rejeté.
3. **Runtime maison** — plus de code à maintenir, mais **contrôle total** sur les invariants de sûreté qui sont notre différenciateur. **Retenu.**

## Conséquences
- ✅ Contrôle total des **invariants de sûreté** (tenets 1 & 2) — impossible à garantir aussi finement avec un framework générique.
- ✅ Fallback local → résilience (tenet 7).
- ✅ Pas de dépendance structurante à un framework tiers instable.
- ⚠️ **Charge de maintenance** : la boucle, les providers, le routage et la gouvernance sont à notre charge.
- ⚠️ **Migration inachevée** : stubs à remplacer, imports legacy à nettoyer, traces OTel provider à ajouter — risque tant que la transition n'est pas finie (voir [Roadmap NOW](../../02-product/roadmap.md)).
- ➡️ Exige une couverture de tests solide sur le runtime (invariants n°1 à 5 du [design](../agentic-runtime-design.md)).
