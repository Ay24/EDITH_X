"""Tests for Global & Regional PII Checksums (Point 4)."""
import pytest
from edith_x.modules.policy.firewall import PIIFirewall


def test_indian_pan_card_redaction():
    firewall = PIIFirewall()
    text = "Customer PAN card is ABCDE1234F for tax verification."
    redacted, detected, types = firewall.redact(text)
    assert detected is True
    assert "pan" in types
    assert "ABCDE1234F" not in redacted
    assert "[REDACTED_PAN]" in redacted


def test_indian_aadhaar_verhoeff_redaction():
    firewall = PIIFirewall()
    # 2942 3658 9128 is a valid Verhoeff 12-digit number (starts with 2)
    # Let's verify valid Aadhaar is redacted
    # Note: 3675 9834 2162 is a valid Verhoeff number:
    # Let's check with firewall
    valid_aadhaar = "9999 4105 7036"
    text = f"User Aadhaar number: {valid_aadhaar}."
    redacted, detected, types = firewall.redact(text)
    assert detected is True
    assert "aadhaar" in types
    assert "[REDACTED_AADHAAR]" in redacted

    # Invalid 12 digits (fails Verhoeff) should NOT be flagged as Aadhaar
    invalid_digits = "2345 6789 0123"
    text_invalid = f"Order tracking batch: {invalid_digits}."
    redacted_inv, detected_inv, types_inv = firewall.redact(text_invalid)
    assert "aadhaar" not in types_inv
    assert invalid_digits in redacted_inv


def test_uk_nhs_number_redaction():
    firewall = PIIFirewall()
    # Valid NHS number 943 476 5919
    # Sum: 9*10 + 4*9 + 3*8 + 4*7 + 7*6 + 6*5 + 5*4 + 9*3 + 1*2 = 90+36+24+28+42+30+20+27+2 = 299.
    # 299 % 11 = 2. 11 - 2 = 9 (check digit is 9).
    text = "Patient NHS number is 943 476 5919."
    redacted, detected, types = firewall.redact(text)
    assert detected is True
    assert "nhs" in types
    assert "943 476 5919" not in redacted
    assert "[REDACTED_NHS]" in redacted


def test_date_of_birth_contextual_redaction():
    firewall = PIIFirewall()
    text = "Employee DOB: 14/05/1990 in record."
    redacted, detected, types = firewall.redact(text)
    assert detected is True
    assert "dob" in types
    assert "14/05/1990" not in redacted
    assert "[REDACTED_DOB]" in redacted

    # Regular date without birth context should NOT be redacted as DOB
    text_meeting = "Quarterly review scheduled on 14/05/1990."
    redacted_m, detected_m, types_m = firewall.redact(text_meeting)
    assert "dob" not in types_m
    assert "14/05/1990" in redacted_m


def test_developer_uuid_and_hashes_zero_false_positives():
    firewall = PIIFirewall()
    # UUID and Git SHA in normal development prompt
    text = "Commit 4cb79465dd6b89bdb1673d2bd416b9b1bf96f330 fixed bug in instance 550e8400-e29b-41d4-a716-446655440000"
    redacted, detected, types = firewall.redact(text)
    assert detected is False
    assert "api_key" not in types
    assert "4cb79465dd6b89bdb1673d2bd416b9b1bf96f330" in redacted
    assert "550e8400-e29b-41d4-a716-446655440000" in redacted
