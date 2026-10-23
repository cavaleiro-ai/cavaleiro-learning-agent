"""WhatsApp Cloud allowlists compare business-scoped user ids (BSUIDs) exactly.

Regression for #138192. Since the WhatsApp usernames rollout, ``messages[].from`` can carry a
BSUID (``CC.<alphanumeric>``, e.g. ``DE.1A2B3C4D5E``) instead of a phone number. The allowlist
normalizer stripped every non-digit from every entry and sender, so two different BSUIDs with
the same digits (``DE.1A2B3C4D5E`` and ``DE.12345ABCDE`` both became ``12345``) admitted each
other, and a BSUID could also collide with a phone number. Only phone-shaped ids are reduced to
digits now; anything else must match byte for byte.
"""

from __future__ import annotations

from unittest.mock import MagicMock


def _build_adapter(monkeypatch, allowed: str):
    from plugins.platforms.whatsapp_cloud.adapter import WhatsAppCloudAdapter

    for var in (
        "WHATSAPP_CLOUD_ALLOW_FROM",
        "WHATSAPP_CLOUD_ALLOWED_USERS",
        "WHATSAPP_CLOUD_ALLOW_ALL_USERS",
        "WHATSAPP_CLOUD_DM_POLICY",
        "WHATSAPP_DM_POLICY",
        "GATEWAY_ALLOW_ALL_USERS",
        "WHATSAPP_ALLOW_ALL_USERS",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("WHATSAPP_CLOUD_ALLOWED_USERS", allowed)
    config = MagicMock()
    config.extra = {"phone_number_id": "1234567890", "access_token": "test-token"}
    return WhatsAppCloudAdapter(config)


def test_bsuids_sharing_digits_do_not_admit_each_other(monkeypatch):
    adapter = _build_adapter(monkeypatch, "DE.1A2B3C4D5E")
    assert adapter._is_dm_allowed("DE.1A2B3C4D5E") is True
    assert adapter._is_dm_allowed("DE.12345ABCDE") is False


def test_bsuid_never_matches_a_phone_entry_with_the_same_digits(monkeypatch):
    adapter = _build_adapter(monkeypatch, "12345")
    assert adapter._is_dm_allowed("DE.1A2B3C4D5E") is False
    assert adapter._is_dm_allowed("12345") is True


def test_bsuid_comparison_is_case_sensitive(monkeypatch):
    adapter = _build_adapter(monkeypatch, "DE.1A2B3C4D5E")
    assert adapter._is_dm_allowed("DE.1a2b3c4d5e") is False


def test_phone_entries_keep_their_formatting_tolerance(monkeypatch):
    adapter = _build_adapter(monkeypatch, "+1 (555) 123-4567,15550001111@s.whatsapp.net")
    assert adapter._is_dm_allowed("15551234567") is True
    assert adapter._is_dm_allowed("15550001111") is True
    assert adapter._is_dm_allowed("15559999999") is False
