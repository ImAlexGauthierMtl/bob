# Tool Governance Implementation Plan

## Objective

Give CDE a wired Settings surface where:

- end users manage their own Bob tool preferences and account connections;
- admins authorize the tools available to the company and teams;
- Bob Chat consumes only governed tools exposed by the runtime;
- backend persistence stays behind B4F APIs and internal backends.

## Frontend Settings

Create two explicit Settings zones:

- **My Settings**: personal profile, personal tool access/preferences, personal integrations.
- **Administration**: team, roles, platform access, and enterprise tool governance.

Required screens:

- `My Tool Access`: shows the user’s allowed tools, current personal preferences, and links to integrations.
- `Tool Governance`: admin view for enabling/disabling tools, setting team scope, risk, sync mode, and data mapping intent.

The Integrations catalog remains the place where users connect accounts and inspect Pipedream app tools.
Governance moves out of the bottom of Integrations so the catalog does not carry admin-only noise.

## B4F Contract

Angular calls only `agent-control-b4f-api` for Bob tool governance.

Public routes:

- `GET /api/agent-control/v1/tool-governance/policies`
- `PUT /api/agent-control/v1/tool-governance/policies/{policy_id}`
- `GET /api/agent-control/v1/tool-governance/me`
- `PUT /api/agent-control/v1/tool-governance/me/preferences`

B4F responsibilities:

- validate the user session and `agent_control.manage` / `agent_control.use`;
- sign `X-Session-Context` for the internal runtime backend;
- compose frontend-friendly responses;
- never access DB or provider secrets.

## Backend And DB

`agent-runtime-backend-api` owns runtime tool policy persistence through
`agent_runtime.runtime_catalog_items`.

Collections:

- `tool_policies`: tenant-level admin governance entries.
- `user_tool_preferences`: user-level Bob tool preferences.

Internal routes:

- `GET /internal/agent-runtime/v1/settings/tool-governance`
- `PUT /internal/agent-runtime/v1/settings/tool-governance/{policy_id}`
- `GET /internal/agent-runtime/v1/settings/tool-governance/me`
- `PUT /internal/agent-runtime/v1/settings/tool-preferences/me`

Policy fields:

- `id`, `display_name`, `provider`, `integration_key`, `tool_key`;
- `family`, `capability`, `risk`, `enabled`;
- `team_scope`, `sync_enabled`, `sync_mode`, `data_mapping`, `notes`.

This is the first persisted governance layer. Future Bob Cloud wiring should
replace local tenant/team authority, but the UI and contracts remain stable.

## Test Plan

Backend:

- internal routes require signed session context;
- default runtime capabilities produce governance policies;
- admin policy upsert persists and overrides tenant policy;
- user preferences are scoped to tenant and user.

B4F:

- public routes require auth and permission;
- B4F signs internal session context instead of forwarding tenant/user from the frontend;
- frontend routes are mounted in the Agent Control namespace.

Frontend:

- Settings nav separates My Settings from Administration;
- My Tool Access renders allowed tools and saves user preferences;
- Tool Governance renders policies and saves admin changes;
- Integrations catalog no longer duplicates admin scope configuration.

Browser certification:

- run local Docker stack;
- open Chrome with the extension profile;
- verify login/session, Settings navigation, My Tool Access, Tool Governance, and Conversation tool usage;
- save screenshots in `captures/`.
