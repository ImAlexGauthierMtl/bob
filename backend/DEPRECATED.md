# DEPRECATED — Croo Legacy Monolith API

This is the original monolithic backend (port 4500). All its functionality has been
extracted into the 3-tier microservice architecture:

## Backend Layer (CRUD + Events)
- `user~backend-api` (9001) — Users, tenants, roles
- `contact~backend-api` (9002) — Contacts
- `org~backend-api` (9003) — Organizations, departments
- `opportunity~backend-api` (9004) — Opportunities, quotes
- `activity~backend-api` (9005) — Activities
- `product~backend-api` (9006) — Products
- `email~backend-api` (9007) — Emails, MS365 connections, smart labels
- `agent~backend-api` (9008) — Bob settings, BCC, client maps, training
- `workflow~backend-api` (9009) — Workflows
- `kb~backend-api` (9010) — Knowledge base
- `usage~backend-api` (9011) — Usage tracking

## B4F Layer (Business Logic)
- `auth~b4f-api` (8001) — Authentication, JWT, authorization
- `crm~b4f-api` (8002) — CRM aggregation
- `ai-agent~b4f-api` (8003) — AI orchestration
- `communication~b4f-api` (8004) — MS365 sync, webhooks
- `platform~b4f-api` (8005) — Workflow execution, usage analytics
- `kb~b4f-api` (8006) — Knowledge base access control

This monolith is kept running during the transition period as `legacy-api` in
docker-compose.yml. It can be removed once all routes have been verified against
the new architecture.
