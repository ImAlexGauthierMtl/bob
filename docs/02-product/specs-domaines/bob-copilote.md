# Spec produit — Bob, le copilote agentique

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Couche** : 02 · Produit · **Dernière MAJ** : 2026-07-01
> Parent : [PRD §4.3](../prd-cahier-des-charges.md#43-bob--copilote-agentique--spec-détaillée) · Design technique : [Runtime agentique](../../04-technique/agentic-runtime-design.md) · Réf. : [`tool-governance-implementation-plan.md`](../../tool-governance-implementation-plan.md)

## 1. Objet

Bob est **le différenciateur** de CDE : un copilote qui **exécute** le travail commercial (pas seulement suggère), sous contrôle humain. Couvre [JTBD-4](../../01-discovery/jobs-to-be-done.md) (déléguer en sécurité). C'est ici que se concentre la valeur **et** le risque produit.

## 2. Capacités produit

| Capacité | Description |
|---|---|
| **Conversation** | Chat en session (workspace, voix à venir, mode training) avec historique et idempotence client. |
| **Exécution d'outils** | Bob appelle des outils (CRM, email, MCP : Slack, Teams, Drive, calendrier…) dans un *tool-call loop* borné. |
| **Confirmation & readback** | Toute action sensible (write/destructive) est présentée puis exécutée **après clic** de l'utilisateur. |
| **Mémoire** | RAG privé/organisationnel : Bob se souvient (insights, notes, procédures, faits) selon un scope et une sensibilité. |
| **Gouvernance d'outils** | 2 niveaux : politiques admin (`tool_policies`) + préférences utilisateur (provider email/agenda, confirmation, trace). |
| **Narration** | Chaque étape est visible (`demande_reçue → provider → outil_* → action_confirmée → réponse`). |
| **Overlay d'affichage** | Widget temps réel : étapes, confirmations en attente, artifacts (graphiques, tableaux). |
| **BCC / training** | Bob Control Center : agents administratifs, skills importables, playbooks, client map. |

## 3. Boucle d'exécution (vue produit)

1. L'utilisateur envoie un message → session + idempotence.
2. Construction du **contexte mémoire** (RAG).
3. **Routage d'intent MCP déterministe** : si le message contient un mot-clé de famille (slack, teams, factory…), pré-routage vers l'outil avant même l'appel LLM.
4. Sélection des outils **gouvernés** (policies + préférences).
5. Boucle provider (≤ 5 itérations) : LLM → tool_calls → [gate de confirmation si sensible] → exécution → ré-invocation. Limites : 3 outils/itération, 12 au total.
6. Stockage du run (provider, modèle, tool_calls, narration, confirmations, coût) + message assistant.
7. Retour au frontend : message + narration + confirmations en attente.

Détails techniques (entités `AgentRun`, `AgentConfirmation`, providers, limites) : [Runtime agentique](../../04-technique/agentic-runtime-design.md).

## 4. Gouvernance d'outils (règle produit centrale)

- **Politique** (`tool_policies`) par outil : `risk` (read/write/destructive), `team_scope`, `enabled`, provider, capability, notes. Gérée par l'admin.
- **Préférences utilisateur** : provider email/agenda préféré, `require_write_confirmation`, `show_tool_trace`, connecteurs personnels autorisés.
- **Filtrage** : à chaque run, l'ensemble d'outils proposé au LLM est réduit selon policies + préférences. Un outil désactivé n'est jamais proposé.

## 5. Sûreté (non négociable — tenets 1 & 2)

- Aucune action irréversible sans **confirmation explicite** + *readback*.
- **Tout tracé** : narration steps + ledger d'usage (`correlation_id`).
- **Signature de contexte de session** : Bob Chat signe `X-Session-Context` vers le runtime ; pas d'identité brute du frontend au backend.
- **Sensibilité RAG respectée** : seules les entrées autorisées (`internal`, `private_user`, `public`) entrent dans le contexte.

## 6. Surfaces UI

Page Chat (`pages/chat`), overlay (`bob-display-overlay`), settings Bob (personnalité/voix), Bob capabilities, BCC control center, training templates. Stores NGRX : `bob-chat`, `bob-session`, `bob-assistant-settings`, `bob-platform-settings`, `bcc-interview-chat`, `ai-agent`.

## 7. Réglages Bob
- **Personnalité** : ton (professional/friendly/direct/playful), formalité, longueur de réponse, langue, créativité, emojis.
- **Voix** : voix (autumn/cedar/marie), vitesse, écoute auto.

## 8. Exigences & priorités
Voir [PRD §4.3](../prd-cahier-des-charges.md#43-bob--copilote-agentique--spec-détaillée). Must : EF-BOB-1,2,3,4,6,8. À finaliser : mémoire RAG (5, 🟡 — dépend de Milvus), BCC (10), réglages (11) ; migration hors LangGraph ([ADR-0004](../../04-technique/adr/adr-0004-runtime-agentique-maison-vs-langgraph.md)).

## 9. Métriques (les plus importantes du produit)
Taux de confirmation (proposé→validé), taux d'annulation au gate, taux d'action reprise/corrigée, runs échoués/dégradés, latence P95, COGS/action. Voir [North Star](../../00-vision/north-star-metric.md).
