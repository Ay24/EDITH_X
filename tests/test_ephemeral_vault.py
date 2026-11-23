"""Tests for Reversible Ephemeral Pseudonymization Vault (Point 5)."""
import time
import pytest
from edith_x.modules.policy.vault import EphemeralVault


def test_vault_tokenize_and_detokenize_roundtrip():
    vault = EphemeralVault(default_ttl_seconds=30.0)
    original_text = "Please process card 4532 0150 1234 5678 and notify john.doe@example.com immediately."

    tokenized_text, session_id = vault.tokenize(original_text)

    # Verify PII is completely removed from tokenized text
    assert "4532 0150 1234 5678" not in tokenized_text
    assert "john.doe@example.com" not in tokenized_text
    assert "{{CARD_REF_" in tokenized_text
    assert "{{EMAIL_REF_" in tokenized_text
    assert session_id is not None

    # Model generates answer using the token
    model_response = f"I have authorized {tokenized_text.split()[3]} and sent confirmation receipt to {tokenized_text.split()[-2]}."

    # Full detokenization
    restored_full = vault.detokenize(model_response, session_id, mask_mode="full")
    assert "4532 0150 1234 5678" in restored_full
    assert "john.doe@example.com" in restored_full

    # Partial masked detokenization (PCI-compliant display)
    restored_masked = vault.detokenize(model_response, session_id, mask_mode="masked")
    assert "4532 **** **** 5678" in restored_masked
    assert "j***e@example.com" in restored_masked


def test_vault_ttl_expiration_and_cleanup():
    vault = EphemeralVault(default_ttl_seconds=0.1)
    original_text = "Verify card 4532 0150 1234 5678"
    tokenized_text, session_id = vault.tokenize(original_text)

    time.sleep(0.15)
    # After TTL, vault should return token unchanged or empty mapping
    restored = vault.detokenize(tokenized_text, session_id)
    assert "{{CARD_REF_" in restored  # expired session cannot detokenize
