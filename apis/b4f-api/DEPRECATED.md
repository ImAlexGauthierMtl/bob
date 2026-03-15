# DEPRECATED — B4F Gateway

This service was the single-entry-point gateway proxy that routed frontend requests
to the appropriate backend microservice. It has been replaced by the 3-tier architecture
where the frontend talks directly to domain-specific B4F APIs:

- `auth~b4f-api` (port 8001) — Authentication, users, tenants, RBAC
- `crm~b4f-api` (port 8002) — CRM: contacts, organizations, opportunities, etc.
- `ai-agent~b4f-api` (port 8003) — AI Agent: Bob, BCC, client maps, training
- `communication~b4f-api` (port 8004) — Communication: MS365, emails, smart labels
- `platform~b4f-api` (port 8005) — Platform: workflows, usage
- `kb~b4f-api` (port 8006) — Knowledge base

This directory can be safely removed once all frontend traffic is confirmed to be
routing through the domain B4F APIs.
