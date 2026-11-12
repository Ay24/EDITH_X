import pytest
from edith_x.core.config import Settings
from edith_x.core.interfaces import AuthContext, IntentResult
from edith_x.modules.policy.firewall import PIIFirewall
from edith_x.modules.policy.service import PolicyService

def test_detect_and_mask_credit_card():
    firewall = PIIFirewall()
    text = "My corporate card is 4532-1234-5678-9012 for billing"
    cleaned, detected, items = firewall.redact(text)
    assert detected is True
    assert "4532-1234-5678-9012" not in cleaned
    assert "[REDACTED_CREDIT_CARD]" in cleaned
    assert "credit_card" in items

def test_detect_and_mask_ssn():
    firewall = PIIFirewall()
    text = "Employee SSN is 000-12-3456"
    cleaned, detected, items = firewall.redact(text)
    assert detected is True
    assert "000-12-3456" not in cleaned
    assert "[REDACTED_SSN]" in cleaned
    assert "ssn" in items

def test_detect_and_mask_email():
    firewall = PIIFirewall()
    text = "Please reach out to john.doe@enterprise-corp.com directly"
    cleaned, detected, items = firewall.redact(text)
    assert detected is True
    assert "john.doe@enterprise-corp.com" not in cleaned
    assert "[REDACTED_EMAIL]" in cleaned
    assert "email" in items

def test_detect_api_keys():
    firewall = PIIFirewall()
    text = "Use key sk-ant-api03-abcdefghijklmnopqrstuvwxyz1234567890"
    cleaned, detected, items = firewall.redact(text)
    assert detected is True
    assert "[REDACTED_SECRET]" in cleaned
    assert "api_key" in items

def test_clean_text_no_pii():
    firewall = PIIFirewall()
    text = "Can you write a python script to calculate fibonacci numbers?"
    cleaned, detected, items = firewall.redact(text)
    assert detected is False
    assert cleaned == text
    assert len(items) == 0

@pytest.mark.asyncio
async def test_policy_service_forces_local_on_pii():
    settings = Settings(local_model_list=["llama3.2:3b"], cloud_model_list=["gpt-4o"])
    service = PolicyService(settings)
    intent = IntentResult(
        type="coding",
        complexity=0.8,
        risk=0.2,
        confidence=0.9,
    )
    auth = AuthContext(user_id="user-1", org_id="org-1", email="user@corp.com", role="member", api_key_id="key-1")

    # With PII query
    decision = await service.evaluate(intent, auth, query="My SSN is 123-45-6789, process this tax form")
    assert decision.pii_detected is True
    assert decision.requires_local is True
    assert decision.allowed_models == settings.local_model_list
    assert "gpt-4o" not in decision.allowed_models


def test_detect_high_entropy_raw_secret():
    firewall = PIIFirewall()
    text = "Database connection token is 8f9b2c3d4e5a6f7b8c9d0e1f2a3b4c5d6e7f8a9b"
    cleaned, detected, items = firewall.redact(text)
    assert detected is True
    assert "8f9b2c3d4e5a6f7b8c9d0e1f2a3b4c5d6e7f8a9b" not in cleaned
    assert "[REDACTED_SECRET]" in cleaned
