import json
from collections import Counter

import pytest

from app.application.mcp_intent_router import infer_external_mcp_intent
from app.application.runtime_catalog_defaults import (
    SKYSWITCH_TELCO_DOC_TOOL_ENTRIES,
    default_mcp_capabilities,
)
from app.domain import InternalContext, RuntimeToolCall
from app.infrastructure.tools.local_registry import LocalRuntimeToolRegistry


def _skyswitch_telco_doc_capabilities():
    return [
        capability
        for capability in default_mcp_capabilities()
        if capability.get("family") == "skyswitch"
        and capability.get("api_surface") == "skyswitch-telco"
    ]


def test_skyswitch_telco_catalog_exposes_official_documented_tools():
    capabilities = _skyswitch_telco_doc_capabilities()
    by_id = {capability["qualified_id"]: capability for capability in capabilities}

    assert len(SKYSWITCH_TELCO_DOC_TOOL_ENTRIES) == 213
    assert len(by_id) == 213
    assert Counter(capability["risk"] for capability in capabilities) == {
        "read": 112,
        "write-requested": 68,
        "destructive-confirmed": 33,
    }
    assert Counter(capability["doc_section"] for capability in capabilities).most_common(5) == [
        ("10DLC", 33),
        ("Toll Free A2P", 15),
        ("Message Forwarding", 12),
        ("Catalog, Reservations & Purchase", 11),
        ("LNP Management", 11),
    ]

    get_e911 = by_id["skyswitch.telco-e911-get-e911"]
    assert get_e911["risk"] == "read"
    assert get_e911["http_method"] == "GET"
    assert get_e911["endpoint"] == "/accounts/{account_id}/phone-numbers/{phone_number}/e911"
    assert get_e911["api_scope"] == "e911"
    assert get_e911["api_base_hint"] == "https://api.skyswitch.com"
    assert get_e911["doc_url"] == "https://developers.skyswitch.com/reference/get_accounts-account-id-phone-numbers-phone-number-e911"

    provision_e911 = by_id["skyswitch.telco-e911-provision-e911"]
    assert provision_e911["risk"] == "write-requested"
    assert provision_e911["http_method"] == "PUT"
    assert provision_e911["guardrail"] == "write_action_requires_explicit_confirmation_and_readback"

    send_message = by_id["skyswitch.telco-message-sending-send-message"]
    assert send_message["risk"] == "write-requested"
    assert send_message["http_method"] == "POST"
    assert send_message["endpoint"] == "/accounts/{account_id}/messaging/send"
    assert send_message["api_scope"] == "messaging"

    delivery_status = by_id["skyswitch.telco-sms-reports-get-delivery-status"]
    assert delivery_status["risk"] == "read"
    assert delivery_status["http_method"] == "POST"
    assert delivery_status["endpoint"] == "/accounts/{account_id}/messaging/delivery"
    assert delivery_status["api_scope"] == "messaging"

    assert all("," not in capability["qualified_id"] for capability in capabilities)
    assert all("---" not in capability["qualified_id"] for capability in capabilities)


def test_skyswitch_telco_intent_router_selects_documented_tools():
    examples = [
        ("Get e911 SkySwitch for number 15145550100", "skyswitch.telco-e911-get-e911", "read"),
        ("Provision e911 SkySwitch for 15145550100", "skyswitch.telco-e911-provision-e911", "write-requested"),
        ("Get inbound CNAM SkySwitch", "skyswitch.telco-cnam-deliveries-inbound-get-cnam-delivery", "read"),
        ("Set outbound CNAM SkySwitch", "skyswitch.telco-cnam-storage-outbound-set-outbound-cnam", "write-requested"),
        ("Get delivery status SMS SkySwitch", "skyswitch.telco-sms-reports-get-delivery-status", "read"),
        ("List MDR reports SkySwitch", "skyswitch.telco-sms-reports-list-mdrs", "read"),
        (
            "Reserve a DID SkySwitch",
            "skyswitch.telco-catalog-reservations-and-purchase-reserve-phone-number",
            "write-requested",
        ),
        ("Route phone number SkySwitch", "skyswitch.telco-voice-route-route-phone-number", "write-requested"),
        (
            "List available toll free SkySwitch",
            "skyswitch.telco-catalog-reservations-and-purchase-list-toll-free-numbers-catalog",
            "read",
        ),
    ]
    for prompt, capability, risk in examples:
        intent = infer_external_mcp_intent(prompt)

        assert intent is not None
        assert intent.family == "skyswitch"
        assert intent.capability == capability
        assert intent.risk == risk


@pytest.mark.asyncio
async def test_skyswitch_telco_catalog_is_read_only_safe_until_adapter_is_bound():
    registry = LocalRuntimeToolRegistry()
    context = InternalContext(
        tenant_id="tenant-croo-local",
        user_id="user-alex-local",
        trace_id="skyswitch-telco-readonly-contract",
        permissions=("mcp:read", "mcp:write"),
        roles=("admin",),
    )

    failures = []
    for index, capability in enumerate(_skyswitch_telco_doc_capabilities(), start=1):
        result = await registry.execute(
            call=RuntimeToolCall(
                id=f"skyswitch-telco-readonly-{index}",
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
