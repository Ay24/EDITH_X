"""Unit tests for tamper-evident hash-chained audit ledger."""
import pytest
from edith_x.modules.identity.audit_ledger import AuditLedger


def test_audit_ledger_records_and_verifies_integrity():
    ledger = AuditLedger()

    # Record series of events
    e1 = ledger.record_event("login_success", "usr_001", "org_01", {"ip": "127.0.0.1"})
    e2 = ledger.record_event("policy_blocked", "usr_002", "org_02", {"reason": "cardholder_data"})
    e3 = ledger.record_event("model_invoked", "usr_001", "org_01", {"model": "llama-3.2-3b"})

    assert e1["prev_hash"] == "GENESIS_BLOCK_00000000000000000000000000000000000000000000000000000000"
    assert e2["prev_hash"] == e1["entry_hash"]
    assert e3["prev_hash"] == e2["entry_hash"]

    # Verify intact chain
    is_valid, count = ledger.verify_integrity()
    assert is_valid is True
    assert count == 3


def test_audit_ledger_detects_tampering():
    ledger = AuditLedger()

    ledger.record_event("action_1", "usr_01", "org_01")
    ledger.record_event("action_2", "usr_02", "org_01")
    ledger.record_event("action_3", "usr_03", "org_01")

    # Adversary tampers with the second record in the chain
    ledger._chain[1]["action"] = "action_2_tampered"

    # Verification must fail
    is_valid, bad_idx = ledger.verify_integrity()
    assert is_valid is False
    assert bad_idx == 1
