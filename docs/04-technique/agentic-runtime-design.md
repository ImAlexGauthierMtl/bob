# Design technique — Runtime agentique (Bob)

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Couche** : 04 · Technique · **Dernière MAJ** : 2026-07-01
> Design du sous-système le plus critique de CDE. Réfs code : `agent-runtime-backend-api`, `bob-chat-b4f-api`, `agent-memory-backend-api`, `agent-control-b4f-api` · plan `../project-x/08-agentic-runtime/` · [`tool-governance-implementation-plan.md`](../tool-governance-implementation-plan.md). Spec produit : [Bob copilote](../02-product/specs-domaines/bob-copilote.md).

## 1. Objectif & responsabilités

Transformer un message utilisateur en une **réponse + des actions exécutées et tracées**, sous contrôle humain. Le runtime doit être : **sûr** (gating), **traçable** (narration + ledger), **gouverné** (policies), **résilient** (fallback), **borné** (limites de boucle).

## 2. Chaîne de composants

```
Frontend ──► bob-chat-b4f (façade publique)
                │  session · idempotence · X-Session-Context signé
                ▼
        agent-runtime-backend (interne)
                │  provider LLM · sélection & exécution d'outils · confirmations · gouvernance
     ┌──────────┼───────────────────────────┐
     ▼          ▼                            ▼
conversation-backend   agent-memory-backend      MCP gateway / outils
(messages/sessions)    (RAG · Milvus · knowledge)  (slack, teams, mail, drive, factory…)

agent-control-b4f : BCC · training · client map · tool-governance (admin)
```

## 3. Cycle d'un run (détaillé)

1. **Réception** (bob-chat-b4f) : vérif idempotence (`Idempotency-Key`), gestion de session, ajout du message utilisateur (conversation-backend).
2. **Contexte mémoire** : `build_rag_context` — recherche privée/organisationnelle, revalidation des vecteurs, **filtrage par sensibilité** (`internal`/`private_user`/`public`), rejets tracés (`source_not_found`, `rag_sensitivity_forbidden`, `rag_limit_exceeded`).
3. **Résolution du catalogue** : agent demandé (ou défaut) → skills + tools ; application de la **gouvernance** (`apply_tool_governance_to_runtime_catalog`).
4. **Routage d'intent MCP déterministe** : si le prompt contient un mot-clé de famille (slack, teams, factory…), pré-routage vers `bob_mcp_gateway` **avant** l'appel LLM (utile si le provider ne gère pas `tool_choice`).
5. **Boucle provider** (`while tool_calls`) :
   - Appel LLM (Fireworks ou local).
   - Découpe : ≤ `MAX_TOOL_CALLS_PER_ITERATION = 3`.
   - Pour chaque tool_call : `tool_registry.execute()` → statut `success | requires_confirmation | error | degraded`.
   - Si `requires_confirmation` → crée `AgentConfirmation(pending)`, n'exécute pas.
   - Ajout des résultats aux messages, ré-invocation du LLM.
   - Bornes : `MAX_TOOL_ITERATIONS = 5`, `MAX_TOTAL_TOOL_CALLS = 12`.
6. **Persistance** : `AgentRun(status)` + metadata (provider, model, tool_calls, `tool_loop`, `routing`, `pending_confirmations`, `confirmed_executions`), `narration_steps`, `actions`, `artifacts`. Confirmations stockées séparément.
7. **Retour** : message assistant + narration + confirmations en attente.

### Résolution de confirmation
`POST /runs/{run_id}/confirmations/{id}/(confirm|cancel)` → bob-chat-b4f → runtime `confirm_confirmation()` → exécution `execute(..., confirmed=True)` → run mis à jour (`confirmed_executions`).

## 4. Providers LLM

| Provider | Modèle | Rôle | `supports_tool_choice` |
|---|---|---|---|
| **Fireworks** | `accounts/fireworks/models/kimi-k2p7-code` | production (OpenAI-compatible) | oui |
| **Local** | `bob-local-runtime` | fallback déterministe (dev / panne) | non → routage MCP déterministe |

Sélection : si `FIREWORKS_API_KEY` && `AGENT_RUNTIME_PROVIDER ∈ {auto, fireworks}` → Fireworks, sinon Local. Port `RuntimeProviderPort.complete(messages, tools, trace_id) → RuntimeModelResult`. Params : `FIREWORKS_TEMPERATURE=0.1`, `TOP_P=0.8`, `TIMEOUT=60s`. Embeddings : `qwen3-embedding-8b` (4096d).

## 5. Gouvernance d'outils (2 niveaux)

- **Policies admin** (`tool_policies`) : `provider`, `integration_key`, `tool_key`, `family`, `capability`, **`risk` (read/write/destructive)**, `enabled`, `team_scope`, `sync_*`, `notes`. Ex. `slack.draft-send` → risk `write`.
- **Préférences utilisateur** (`user_tool_preferences`) : `preferred_email/calendar_provider` (auto/…/ask), `require_write_confirmation`, `show_tool_trace`, `allow_personal_connectors`.
- **Filtrage** : à chaque run, l'ensemble d'outils est réduit (policies + préférences) avant présentation au LLM. Routes publiques : `/api/agent-control/v1/tool-governance/*`.

## 6. Mémoire & RAG

- **MemoryEntry** : scope (`PRIVATE_USER`/`ORGANIZATION`/`SHARED_CLEAN`), type (insight/note/procedure/fact), **sensitivity**, `expires_at`, `idempotency_key`.
- **Vecteurs Milvus** : collections `bob_private_memory_chunks_v1`, `bob_organization_knowledge_chunks_v1`, `support_procedure_chunks_v1`, `zoho_ticket_chunks_v1`. Rebuild jobs avec dual-write (original + shadow) et revalidation.
- **Ingestion Zoho** (via Pipedream) : ticket → procédure candidate (Fireworks) → chunks → embeddings → upsert Milvus → PostgreSQL (source de vérité).
- **Résilience** : Milvus optionnel en local (`MILVUS_ENABLED=false`) → repli full-text / embeddings déterministes.

## 7. Outils & MCP

- Outils internes par défaut : `bob_runtime_status` (read), `bob_memory_context_summary` (read), `bob_mcp_gateway` (read, `internal_gateway`).
- Familles MCP (croo-agentic) via gateway : slack, teams, mail-calendar, workspace-files, factory, gitlab-code, browser, web-research, bob-control-center, support-memory.
- Exécution : `RuntimeToolRegistryPort.execute()` → statut `success | requires_confirmation | error | degraded`.

## 8. Migration hors LangGraph (état & plan)

- **Déjà porté** : providers Fireworks + local, routeur d'intent MCP, orchestrateur de boucle, gating/readback, gouvernance, mémoire RAG.
- **À finir** (ordre recommandé) : remplacer les stubs de contrat par des tests provider réels/fakes → mettre à jour la doc → ajouter traces OTel par appel provider → nettoyer les imports legacy langchain/langgraph.
- Décision structurante : [ADR-0004](adr/adr-0004-runtime-agentique-maison-vs-langgraph.md).

## 9. Invariants de sûreté (à ne jamais casser)

1. Aucune action `write`/`destructive` exécutée sans `AgentConfirmation(confirmed)`.
2. La sensibilité RAG est toujours filtrée avant d'entrer dans le contexte.
3. Les bornes de boucle (5/3/12) sont des garde-fous durs (coût & runaway).
4. Le frontend ne transmet jamais d'identité brute au runtime : contexte de session **signé** (`X-Session-Context`).
5. Chaque écriture sensible est **idempotente**.

## 10. Observabilité du runtime
Chaque run doit émettre : trace OTel (par appel provider — à finaliser), narration steps, et une/des `UsageTransaction` (COGS via `CostRateCard`, `correlation_id` = run/conversation). SLO : [SLO & Observabilité](slo-observability.md).

## 11. Risques spécifiques
Coût/latence du tool-loop à l'échelle, dépendance Fireworks (rate-limit/rupture), qualité du routage déterministe (faux positifs de mots-clés), dérive de la mémoire (entrées obsolètes). Voir [Risk Register](../06-gouvernance/risk-register.md).
