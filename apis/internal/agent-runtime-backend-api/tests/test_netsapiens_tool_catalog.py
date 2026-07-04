import json
from collections import Counter

import pytest

from app.application.mcp_intent_router import infer_external_mcp_intent
from app.application.runtime_catalog_defaults import default_mcp_capabilities
from app.domain import InternalContext, RuntimeToolCall
from app.infrastructure.tools.local_registry import LocalRuntimeToolRegistry


EXPECTED_NETSAPIENS_DOC_TOOL_IDS = {
    "skyswitch.pbx-subscriber-overview",
    "skyswitch.pbx-subscriber-read",
    "skyswitch.pbx-subscriber-create",
    "skyswitch.pbx-subscriber-update",
    "skyswitch.pbx-subscriber-delete",
    "skyswitch.pbx-subscriber-count-domain",
    "skyswitch.pbx-subscriber-list-domain",
    "skyswitch.pbx-device-overview",
    "skyswitch.pbx-device-read",
    "skyswitch.pbx-device-create",
    "skyswitch.pbx-device-update",
    "skyswitch.pbx-device-delete",
    "skyswitch.pbx-device-count-domain-user",
    "skyswitch.pbx-device-list-supported-models",
    "skyswitch.pbx-phone-create",
    "skyswitch.pbx-phone-read",
    "skyswitch.pbx-phone-resync",
    "skyswitch.pbx-phone-update",
    "skyswitch.pbx-phone-count",
    "skyswitch.pbx-phone-delete",
    "skyswitch.pbx-domains-create",
    "skyswitch.pbx-domains-count",
    "skyswitch.pbx-domains-read",
    "skyswitch.pbx-domains-update",
    "skyswitch.pbx-domains-delete",
    "skyswitch.pbx-domains-read-billable-summary",
    "skyswitch.pbx-answering-rules-overview",
    "skyswitch.pbx-answering-rules-read",
    "skyswitch.pbx-answering-rules-create",
    "skyswitch.pbx-answering-rules-update",
    "skyswitch.pbx-answering-rules-delete",
    "skyswitch.pbx-answering-rules-reorder",
    "skyswitch.pbx-time-frames-create",
    "skyswitch.pbx-time-frames-create-time-range",
    "skyswitch.pbx-conference-bridges-overview",
    "skyswitch.pbx-conference-bridges-create",
    "skyswitch.pbx-conference-bridges-update",
    "skyswitch.pbx-conference-bridges-disconnect-participants",
    "skyswitch.pbx-conference-bridges-read",
    "skyswitch.pbx-call-create",
    "skyswitch.pbx-call-read-active",
    "skyswitch.pbx-call-count",
    "skyswitch.pbx-call-report-active",
    "skyswitch.pbx-call-answer-active",
    "skyswitch.pbx-call-disconnect-active",
    "skyswitch.pbx-call-hold",
    "skyswitch.pbx-call-unhold",
    "skyswitch.pbx-call-enable-recording",
    "skyswitch.pbx-call-disable-recording",
    "skyswitch.pbx-call-pause-recording",
    "skyswitch.pbx-call-resume-recording",
    "skyswitch.pbx-call-reject-incoming",
    "skyswitch.pbx-call-transfer-active",
    "skyswitch.pbx-subscriptions-overview",
    "skyswitch.pbx-subscriptions-read",
    "skyswitch.pbx-subscriptions-create-agent",
    "skyswitch.pbx-subscriptions-create-audit-log",
    "skyswitch.pbx-subscriptions-create-call",
    "skyswitch.pbx-subscriptions-create-presence",
    "skyswitch.pbx-subscriptions-create-call-recording",
    "skyswitch.pbx-subscriptions-create-cdr",
    "skyswitch.pbx-subscriptions-delete",
    "skyswitch.pbx-call-id-emergency-read-domain",
    "skyswitch.pbx-cdr-read",
    "skyswitch.pbx-voicemail-read",
    "skyswitch.pbx-voicemail-delete",
    "skyswitch.pbx-voicemail-upload-greeting",
    "skyswitch.pbx-phone-number-read",
    "skyswitch.pbx-phone-number-create",
    "skyswitch.pbx-phone-number-update",
    "skyswitch.pbx-recordings-read",
    "skyswitch.pbx-recordings-get-call-recording-setting",
    "skyswitch.pbx-recordings-enable-call-recording-setting",
    "skyswitch.pbx-recordings-disable-call-recording-setting",
    "skyswitch.pbx-agent-create",
    "skyswitch.pbx-agent-read-call-queue",
    "skyswitch.pbx-agent-count-call-queue",
    "skyswitch.pbx-agent-make-available",
    "skyswitch.pbx-agent-make-available-single-call",
    "skyswitch.pbx-agent-make-unavailable",
    "skyswitch.pbx-agent-delete-call-queue",
    "skyswitch.pbx-sip-trunks-create",
    "skyswitch.pbx-sip-trunks-count",
    "skyswitch.pbx-sip-trunks-read",
    "skyswitch.pbx-sip-trunks-update",
    "skyswitch.pbx-sip-trunks-delete",
}


def _netsapiens_doc_capabilities():
    return [
        capability
        for capability in default_mcp_capabilities()
        if capability.get("family") == "skyswitch"
        and capability.get("api_surface") == "netsapiens-pbx"
    ]


def test_netsapiens_doc_catalog_exposes_all_documented_tools():
    capabilities = _netsapiens_doc_capabilities()
    by_id = {capability["qualified_id"]: capability for capability in capabilities}

    assert set(by_id) == EXPECTED_NETSAPIENS_DOC_TOOL_IDS
    assert len(by_id) == 86
    assert Counter(capability["risk"] for capability in capabilities) == {
        "read": 32,
        "write-requested": 42,
        "destructive-confirmed": 12,
    }

    read_subscriber = by_id["skyswitch.pbx-subscriber-read"]
    assert read_subscriber["endpoint"] == "/ns-api/"
    assert read_subscriber["http_method"] == "POST"
    assert read_subscriber["api_object"] == "subscriber"
    assert read_subscriber["api_action"] == "read"
    assert read_subscriber["api_base_hint"] == "https://manager.croo.io/ns-api/"
    assert read_subscriber["portal_url"] == "https://manager.croo.io/dashboard"

    domain_delete = by_id["skyswitch.pbx-domains-delete"]
    assert domain_delete["risk"] == "destructive-confirmed"
    assert domain_delete["guardrail"] == "domain_delete_blocked_assign_ticket_to_gustavo"


def test_netsapiens_router_prefers_specific_pbx_objects_over_context_words():
    assert infer_external_mcp_intent("Read Answering Rule NetSapiens for subscriber 600").capability == (
        "skyswitch.pbx-answering-rules-read"
    )
    assert infer_external_mcp_intent("Read Time Frame NetSapiens for domain bigbob01").capability == (
        "skyswitch.pbx-time-frames-create"
    )
    assert infer_external_mcp_intent("Create Time Range NetSapiens for domain bigbob01").capability == (
        "skyswitch.pbx-time-frames-create-time-range"
    )


@pytest.mark.asyncio
async def test_netsapiens_doc_catalog_is_read_only_safe_until_adapter_is_bound():
    registry = LocalRuntimeToolRegistry()
    context = InternalContext(
        tenant_id="tenant-croo-local",
        user_id="user-alex-local",
        trace_id="netsapiens-readonly-contract",
        permissions=("mcp:read", "mcp:write"),
        roles=("admin",),
    )

    failures = []
    for index, capability in enumerate(_netsapiens_doc_capabilities(), start=1):
        result = await registry.execute(
            call=RuntimeToolCall(
                id=f"netsapiens-readonly-{index}",
                name="bob_mcp_gateway",
                arguments={
                    "operation": "execute_capability",
                    "family": "skyswitch",
                    "capability": capability["qualified_id"],
                    "risk": capability["risk"],
                    "confirmed": False,
                    "query": f"read-only test for {capability['qualified_id']}",
                },
            ),
            context=context,
            metadata={"test_mode": "read_only"},
        )
        payload = json.loads(result.content)
        if capability["risk"] == "read":
            ok = (
                result.status == "completed"
                and payload.get("status") == "connector_binding_required"
                and payload.get("external_connector_bound") is False
            )
        else:
            ok = result.status == "requires_confirmation" and payload.get("status") == "confirmation_required"
        if not ok:
            failures.append((capability["qualified_id"], capability["risk"], result.status, payload.get("status")))

    assert failures == []
