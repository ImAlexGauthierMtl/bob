# API Contracts — Bob Conversion Slice

## Auth B4F

Exposed locally at `auth-b4f-api` and through the gateway as the auth surface.

- `POST /auth/login`
- `POST /auth/refresh`
- `GET /auth/me`
- `GET /api/auth/v1/session`
- `POST /api/auth/v1/refresh`
- `POST /api/auth/v1/logout`

Rules:

- Production session authority remains Bob Cloud for tenants, licences, IAM,
  RBAC and platform capabilities.
- Local/dev mode accepts a valid local JWT issued by `/auth/login` as a
  `Bearer` token for `GET /api/auth/v1/session`, returning an authenticated
  `local-dev` session without requiring Bob Cloud availability.
- Angular may call `/auth/login` only when its non-production environment has
  `localAuthEnabled=true`; staging and production login must use the Bob Cloud
  cookie/session path.
- Angular must still call only `auth-b4f-api`; it must not call
  `user-backend-api` or any internal backend directly.
- The local/dev JWT fallback is disabled outside local/dev unless explicitly
  enabled through `CDE_LOCAL_AUTH_ENABLED`.
- `/api/auth/v1/session` without a local JWT continues to delegate to Bob Cloud.

## Bob Chat B4F

Exposed through the gateway as `/api/bob-chat/v1`.

- `POST /api/bob-chat/v1/messages`
- `GET /api/bob-chat/v1/sessions`
- `GET /api/bob-chat/v1/sessions/{session_id}`
- `DELETE /api/bob-chat/v1/sessions/{session_id}`

Rules:

- Validate the current Bob Cloud session and `bob_chat.use` capability.
- The Kubernetes gateway rewrites `/api/bob-chat/v1/*` to `/*` before the
  request reaches `bob-chat-b4f-api`; the B4F keeps both the public
  `/api/bob-chat/v1/*` routes and rewritten internal `/*` routes covered by
  tests.
- Require `Idempotency-Key` on message creation.
- Accept optional `agent_id` on message creation. When provided, Bob Chat B4F
  forwards it inside the internal runtime metadata so the Agent Runtime can
  resolve the selected Bob agent and its associated skills/tools.
- Issue `X-Session-Context` for internal backend calls.
- Delegate conversation persistence to `conversation-backend-api`.
- Delegate memory context retrieval to `agent-memory-backend-api`.
- Delegate run creation to `agent-runtime-backend-api`.
- Never expose the signed internal context to the frontend.

## Agent Control B4F

Exposed through the gateway as `/api/agent-control/v1`.

The public namespace covers every current BCC route under
`/api/agent-control/v1/bcc/*`. The list below names the route families rather
than a restrictive allowlist.

- `GET /api/agent-control/v1/bcc/organizations`
- `POST /api/agent-control/v1/bcc/organizations`
- `GET /api/agent-control/v1/bcc/organizations/{org_id}`
- `PUT /api/agent-control/v1/bcc/organizations/{org_id}`
- `DELETE /api/agent-control/v1/bcc/organizations/{org_id}`
- `GET /api/agent-control/v1/bcc/roles`
- `POST /api/agent-control/v1/bcc/roles`
- `GET /api/agent-control/v1/bcc/roles/{role_id}`
- `PUT /api/agent-control/v1/bcc/roles/{role_id}`
- `DELETE /api/agent-control/v1/bcc/roles/{role_id}`
- `GET /api/agent-control/v1/bcc/cognitive-map`
- `GET|POST|PUT|DELETE /api/agent-control/v1/bcc/industries...`
- `GET|POST|DELETE /api/agent-control/v1/bcc/careers...`
- `GET|POST|DELETE /api/agent-control/v1/bcc/skill-templates...`
- `GET|POST|DELETE /api/agent-control/v1/bcc/task-templates...`
- `GET|POST|DELETE /api/agent-control/v1/bcc/domains...`
- `GET|POST|DELETE /api/agent-control/v1/bcc/intents...`
- `GET|POST|DELETE /api/agent-control/v1/bcc/regulations...`
- `GET|POST|PUT|DELETE /api/agent-control/v1/bcc/skills...`
- `GET|POST|PUT|DELETE /api/agent-control/v1/bcc/tasks...`
- `POST /api/agent-control/v1/bcc/tasks/{task_id}/steps`
- `POST /api/agent-control/v1/bcc/skills/{skill_id}/resources`
- `POST /api/agent-control/v1/bcc/roles/{role_id}/milestones`
- `GET /api/agent-control/v1/bcc/profiles/{entity_type}/{entity_id}`
- `GET /api/agent-control/v1/bcc/profiles/{entity_type}/{entity_id}/{section}`
- `GET /api/agent-control/v1/bcc/profiles/{entity_type}/{entity_id}/history`
- `POST /api/agent-control/v1/bcc/profiles/{entity_type}/{entity_id}/entries`
- `POST /api/agent-control/v1/training/sessions`
- `PATCH /api/agent-control/v1/training/sessions/{session_id}/slide`
- `GET /api/agent-control/v1/training/sessions/{session_id}/notes`
- `POST /api/agent-control/v1/training/sessions/{session_id}/notes`
- `DELETE /api/agent-control/v1/training/notes/{note_id}`
- `GET /api/agent-control/v1/training/sessions/{session_id}/missing`
- `POST /api/agent-control/v1/training/sessions/{session_id}/missing`
- `DELETE /api/agent-control/v1/training/missing/{item_id}`
- `GET /api/agent-control/v1/contacts/{contact_id}/client-map`
- `PUT /api/agent-control/v1/contacts/{contact_id}/client-map`
- `POST /api/agent-control/v1/contacts/{contact_id}/client-map/golden-notes`
- `PUT /api/agent-control/v1/contacts/{contact_id}/client-map/golden-notes/{note_id}`
- `DELETE /api/agent-control/v1/contacts/{contact_id}/client-map/golden-notes/{note_id}`
- `GET /api/agent-control/v1/contacts/{contact_id}/client-map/meddpicc-score`
- `POST /api/agent-control/v1/contacts/{contact_id}/client-map/analyze-behavior`
- `GET /api/agent-control/v1/agent-control/contract`

Rules:

- Angular uses `agentControlApiUrl` for BCC, training and client-map surfaces.
- The public gateway alias is `agent-control`; it routes to the dedicated
  `agent-control-b4f-api` service. The service owns its extracted application
  code and mounts only the Agent Control, BCC, training and client-map
  namespaces.
- Validate session and permissions before all domain operations.
- Require `agent_control.manage`, `agent_control.use` or `admin` before all
  domain operations. Production permissions must come from signed session
  claims; the local CDE capability context is accepted only in development.
- Never accept `tenant_id` or `user_id` from the frontend body or query string.
- Keep behavioral analysis and other agent-side logic in the B4F, not Angular.
- The authenticated runtime contract is served locally at
  `/agent-control/contract` by the transitional B4F and must describe the public
  base path, namespaces, identity source and backing service status.
- Provider-backed operations such as behavioral analysis are delegated to the
  internal Agent Backend; the Agent Control B4F must not receive provider keys
  or instantiate LLM clients.

## Bob Settings B4F

Exposed through the gateway as `/api/bob-settings/v1` and implemented by
`platform-b4f-api`.

- `GET /api/bob-settings/v1/conversation`
- `PUT /api/bob-settings/v1/conversation`
- `GET /api/bob-settings/v1/voice`
- `PUT /api/bob-settings/v1/voice`
- `GET /api/bob-settings/v1/runtime`
- `GET /api/bob-settings/v1/memory`
- `POST /api/bob-settings/v1/runtime/agents`
- `POST /api/bob-settings/v1/runtime/skills`
- `POST /api/bob-settings/v1/runtime/tools`
- `GET /api/bob-settings/v1/security/tenants`
- `PATCH /api/bob-settings/v1/security/tenants/{tenant_id}`
- `GET /api/bob-settings/v1/security/licenses`
- `PATCH /api/bob-settings/v1/security/licenses/{capability}`
- `GET /api/bob-settings/v1/security/users`
- `POST /api/bob-settings/v1/security/invitations`
- `GET /api/bob-settings/v1/security/roles`
- `GET /api/bob-settings/v1/security/memberships`
- `PATCH /api/bob-settings/v1/security/memberships/{membership_id}`

Rules:

- Angular uses `bobSettingsApiUrl` intentionally for Bob preferences, runtime
  catalog, tenants, licences, users and RBAC management.
- The Kubernetes gateway rewrites `/api/bob-settings/v1/*` to `/*` before the
  request reaches `platform-b4f-api`; the B4F keeps both the public
  `/api/bob-settings/v1/*` routes and rewritten internal `/*` or `/security/*`
  routes covered by tests.
- Conversation and voice preferences are CDE-local until a dedicated
  preference backend is selected.
- Runtime catalog reads and mutations are delegated to
  `agent-runtime-backend-api` with a signed internal session context. The B4F
  does not own or persist provider, agent, skill or tool runtime catalog data.
- Memory settings are delegated to `agent-memory-backend-api` with a signed
  internal session context. The B4F returns memory counts, isolation status,
  redacted Milvus/embedding configuration and vector health only; it does not
  expose URIs, tokens, provider secrets or raw memory content.
- Memory settings may return a `vector_index.degraded[]` list when vector
  configuration or health is unavailable. This must not block conversation,
  voice or runtime catalog settings from loading.
- Runtime catalog settings expose safe provider, agent, skill, tool, memory,
  RAG and vector controls. They never expose provider keys, raw tool secrets or
  internal signed session contexts.
- Tenant, licence, user and RBAC attribution is delegated to Bob Cloud when
  configured, with a local/stub mode for CDE development and demonstration.
- Mutations require `Idempotency-Key`.
- Bob Settings is a B4F contract, not a direct Angular-to-Backend dependency.

## Conversation Backend

Internal only. Not routed by the gateway.

- `POST /internal/conversation/v1/sessions`
- `GET /internal/conversation/v1/sessions`
- `GET /internal/conversation/v1/sessions/{session_id}`
- `DELETE /internal/conversation/v1/sessions/{session_id}`
- `POST /internal/conversation/v1/sessions/{session_id}/messages`
- `GET /internal/conversation/v1/sessions/{session_id}/messages`

Rules:

- Require `X-Session-Context` on every domain route.
- Scope every session and message by the signed `tenant_id` and `user_id`.
- Own the `conversation` PostgreSQL schema through Alembic migrations.
- Avoid application startup DDL.

## Agent Runtime Backend

Internal only. Not routed by the gateway.

- `POST /internal/agent-runtime/v1/runs`
- `GET /internal/agent-runtime/v1/runs/{run_id}`
- `POST /internal/agent-runtime/v1/runs/{run_id}/cancel`
- `POST /internal/agent-runtime/v1/runs/{run_id}/confirmations/{confirmation_id}/confirm`
- `POST /internal/agent-runtime/v1/runs/{run_id}/confirmations/{confirmation_id}/cancel`

Rules:

- Require `X-Session-Context` on every domain route.
- Scope every run and confirmation by the signed `tenant_id` and `user_id`.
- Require `Idempotency-Key` on run creation.
- Own the `agent_runtime` PostgreSQL schema through Alembic migrations.
- Avoid application startup DDL.
- Own runtime catalog persistence through `agent_runtime.runtime_catalog_items`.
  This catalog stores admin-created agents, skills and tools inside the tenant.
  Reads are tenant-wide so an agent created in Bob Settings is available to Bob
  Chat runtime execution for the same tenant. Idempotent creation keys remain
  attached to the creator/request context. The catalog is combined with backend
  defaults at read time.
- `GET /internal/agent-runtime/v1/settings`
- `POST /internal/agent-runtime/v1/settings/agents`
- `POST /internal/agent-runtime/v1/settings/skills`
- `POST /internal/agent-runtime/v1/settings/tools`
- Runtime settings expose the Bob agent skill catalog imported from
  `croo-agentic` as safe metadata (`id`, `name`, `description`, `scope`,
  `source`, `status`). These entries are selectable when admins compose a Bob
  agent in Settings and are injected into run metadata when that agent is used.
- Runtime settings include the imported Croo agentic MCP catalog as safe
  metadata: family, skill path, capability index, server names and per-capability
  entries with `qualified_id`, risk level, capability file and expected MCP
  tools. These capability entries are also surfaced as runtime tools in settings.
  Read execution is gated through the internal `bob_mcp_gateway` runtime tool,
  which can list or describe loaded families and persists the result as an
  audited run action. External connector execution and writes remain blocked
  until the matching MCP adapter is bound and an explicit confirmation is
  resolved.
- The first bound MCP adapter is Factory Supabase read access. It is enabled
  only inside `agent-runtime-backend-api` through `FACTORY_SUPABASE_DB_URL`
  (fallback `SUPABASE_DB_URL`) and supports read capabilities such as
  `requests-queues.list_queue_by_project`, `requests-queues.list_requests`,
  `requests-queues.get_request`, and `dev-validation.list_queue`. These calls
  return `degraded` when the local secret is absent rather than leaking or
  fabricating data.
- Runtime provider selection is controlled by environment. `auto` uses
  Fireworks when `FIREWORKS_API_KEY` is present, otherwise the deterministic
  local runtime is used for dev/CI.
- Fireworks uses the OpenAI-compatible chat completions API with model
  `accounts/fireworks/models/kimi-k2p7-code` unless overridden by
  `FIREWORKS_MODEL`.
- Run creation resolves `metadata.agent_id` or `metadata.client_context.agent_id`
  against runtime settings. The resolved `runtime_catalog` is stored in run
  metadata with the public agent, skills, tools and selection status. If no
  agent is requested, the active default Bob agent is used.
- Tool calls are selected from the controlled runtime registry and persisted as
  audited run actions. Unknown tools and unloaded MCP families are rejected by
  the registry.
- Keep provider, memory and tool execution details behind the runtime
  contract; frontend receives only safe run status, narration, actions and
  artifacts.

## Agent Memory Backend

Internal only. Not routed by the gateway.

- `GET /internal/agent-memory/v1/status`
- `POST /internal/agent-memory/v1/search`
- `POST /internal/agent-memory/v1/organization/search`
- `POST /internal/agent-memory/v1/entries`
- `POST /internal/agent-memory/v1/organization/entries`
- `GET /internal/agent-memory/v1/entries/{entry_id}`
- `POST /internal/agent-memory/v1/entries/{entry_id}/readback`
- `POST /internal/agent-memory/v1/journal`
- `POST /internal/agent-memory/v1/rag/context`
- `POST /internal/agent-memory/v1/rag/milvus-context`
- `GET /internal/agent-memory/v1/vector-index/config`
- `GET /internal/agent-memory/v1/vector-index/health`
- `POST /internal/agent-memory/v1/vector-index/revalidate`
- `POST /internal/agent-memory/v1/vector-index/rebuild`
- `GET /internal/agent-memory/v1/vector-index/jobs/{job_id}`
- `POST /internal/agent-memory/v1/vector-index/jobs/{job_id}/prepare`
- `POST /internal/agent-memory/v1/vector-index/jobs/{job_id}/upsert-plan`
- `POST /internal/agent-memory/v1/vector-index/jobs/{job_id}/rollback`

Rules:

- Require `X-Session-Context` on every domain route.
- Private memory is always scoped by signed `tenant_id + user_id`.
- Organization memory is scoped by signed `tenant_id`, source ACL and explicit capability/RBAC.
- Never fall back from private memory to organization or shared memory implicitly.
- Refuse secrets and require source metadata for writes.
- Own the `agent_memory` PostgreSQL schema through Alembic migrations.
- Keep Milvus as a reconstructible index; Postgres remains the source of truth.
- Require `Idempotency-Key` on vector rebuild, prepare and rollback mutations.
- Vector rebuild endpoints create auditable Postgres jobs first; Milvus workers
  are a separate implementation gate.
- Vector prepare creates deterministic Postgres records with opaque `scope_key`
  before any Milvus upsert.
- Vector upsert-plan checks prepared records and readiness for Milvus/embedding
  without making a network call.
- `VectorStoreConfigResponse` returns `enabled`, `configured`,
  `uri_configured`, `token_configured`, `database`, `secure`,
  `timeout_seconds`, `default_dimension`, `embedding_provider`,
  `embedding_configured`, `embedding_model_configured` and
  `embedding_dimension`.
- Milvus configuration status is redacted: no URI, token or provider secret is
  returned by the API.
- Runtime embedding settings are controlled by `EMBEDDINGS_PROVIDER`,
  `EMBEDDINGS_MODEL` and `EMBEDDINGS_DIMENSION`; Milvus settings remain limited
  to vector-store connectivity and defaults.
- Vector health checks are permissioned, redacted and do not contact Milvus when
  Milvus is disabled.
- Vector revalidation accepts Milvus vector IDs but returns only Postgres
  revalidated source IDs, scope/status metadata and controlled rejection codes;
  no memory content is returned.
- Vector revalidation is read-only even though it uses POST for payload size;
  it does not require `Idempotency-Key`.
- Private vector results require the signed `tenant_id + user_id`; organization
  vector results require organization search permission or admin.
- RAG context assembly is read-only and accepts future Milvus candidate vector
  IDs, but every returned memory item must first pass Postgres revalidation.
- RAG context may return accepted memory content to internal runtimes only; no
  rejected or cross-scope memory content is returned.
- RAG context returns `trace_id` and an opaque `audit_ref`; it returns content
  only for allowlisted sensitivities.
- Adding a sensitivity to the RAG allowlist requires an explicit security
  review and a regression test.
- Candidate vector order is preserved and included in the `audit_ref` hash
  because upstream vector order represents retrieval ranking.
- Milvus-backed context assembly uses Milvus only to obtain ranked vector IDs;
  content still comes exclusively from Postgres after revalidation.
- Milvus-backed context rejects wrong query vector dimensions before remote
  search and never exposes Milvus entities or metadata as model context.
- Milvus-backed context accepts only the primary Milvus hit ID as a candidate;
  IDs hidden in returned entity metadata are ignored.
- Milvus-backed `audit_ref` includes a hash of the query vector so the same
  ranked candidates from different vectors produce different audit references.
- Embedding configuration is separate from Milvus configuration and is exposed
  only as provider/model/dimension readiness.
- Milvus is disabled by default and appears in health dependencies only when
  explicitly enabled or configured.
- Avoid application startup DDL.

## Bob Cloud Stub

Local/CI only. Not routed by the gateway and forbidden in production.

- `GET /api/auth/v1/session`
- `POST /api/auth/v1/refresh`
- `POST /api/auth/v1/logout`
- `GET /api/platform/v1/entitlements/me`
- `POST /api/platform/v1/entitlements/check`
- `GET /api/platform/v1/tenants/current`
- `GET /api/iam/v1/users`
- `POST /api/iam/v1/invitations`
- `GET /api/iam/v1/roles`
- `GET /api/iam/v1/memberships`
- `PATCH /api/iam/v1/memberships/{membership_id}`

Rules:

- `BOB_CLOUD_MODE=stub` is allowed only outside production.
- IAM mutations are disabled in the stub.
- Real environments must use Bob Cloud through `BOB_CLOUD_API_URL`.
