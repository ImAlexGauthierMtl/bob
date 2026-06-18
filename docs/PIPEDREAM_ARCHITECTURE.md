# Pipedream Integration Architecture

Date: 2026-06-18
Status: active provider target

## Decision

CDE uses Pipedream Connect for new third-party integrations. The previous
integration provider is not the active provider target.

The existing `membrane_*` database tables remain as local historical storage for
synced email/event records until a dedicated data migration can rename them
without risking production data. They must not be treated as a provider
contract.

## Runtime Shape

- Frontend calls only `communication-b4f-api`.
- `communication-b4f-api` exposes `/pipedream/*` as a thin B4F proxy.
- `email-backend-api` owns provider operations under
  `/api/v1/provider/pipedream/*`.
- Pipedream credentials are read only by backend services.
- Pipedream Connect tokens are created server-side and returned to the
  frontend as short-lived tokens or Connect Link URLs.

## Environment

```env
PIPEDREAM_CLIENT_ID=
PIPEDREAM_CLIENT_SECRET=
PIPEDREAM_PROJECT_ID=
PIPEDREAM_ENVIRONMENT=development
PIPEDREAM_API_URL=https://api.pipedream.com/v1
PIPEDREAM_WEBHOOK_SECRET=
PIPEDREAM_SEND_EMAIL_ACTION_ID=
PIPEDREAM_REPLY_EMAIL_ACTION_ID=
PIPEDREAM_FORWARD_EMAIL_ACTION_ID=
PIPEDREAM_SYNC_EMAILS_ACTION_ID=
```

## Main Endpoints

- `POST /pipedream/token`
- `GET /pipedream/connect-url?integration_key=...`
- `GET /pipedream/integrations`
- `GET /pipedream/connections`
- `DELETE /pipedream/connections/{connection_id}`
- `POST /pipedream/actions/{action_key}/run`
- `POST /pipedream/webhook`

## Validation

- No legacy integration-provider public endpoint should be mounted by
  `communication-b4f-api`.
- No legacy provider runtime variable should be required in `.env.example` or
  Docker local.
- Any remaining `membrane_*` references must be local storage compatibility,
  migrations, tests, or legacy file names awaiting the future data migration.
