"""M4 — PII & Enterprise Secret Redaction Firewall."""
from __future__ import annotations

import re


def _luhn_check(number_str: str) -> bool:
    """Validate credit card number using Luhn algorithm."""
    digits = [int(c) for c in number_str if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = d * 2
            checksum += (doubled - 9) if doubled > 9 else doubled
        else:
            checksum += d
    return checksum % 10 == 0


class PIIFirewall:
    """Detects and redacts Personally Identifiable Information and credentials."""

    CC_PATTERN = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
    SSN_PATTERN = re.compile(r"\b\d{3}[-\s]\d{2}[-\s]\d{4}\b")
    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
    PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
    KEY_PATTERN = re.compile(
        r"\b(?:sk-[a-zA-Z0-9_\-]{20,}|AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}|Bearer\s+[a-zA-Z0-9_\-\.]{20,})\b"
    )

    def redact(self, text: str) -> tuple[str, bool, list[str]]:
        """
        Scan and redact PII/secrets.
        Returns:
            (redacted_text, detected_boolean, list_of_detected_types)
        """
        detected_types: list[str] = []
        result = text

        # 1. API Keys & Cloud Secrets
        def replace_key(match):
            detected_types.append("api_key")
            return "[REDACTED_SECRET]"

        result = self.KEY_PATTERN.sub(replace_key, result)

        # 2. SSN
        def replace_ssn(match):
            detected_types.append("ssn")
            return "[REDACTED_SSN]"

        result = self.SSN_PATTERN.sub(replace_ssn, result)

        # 3. Credit Cards
        matches = list(self.CC_PATTERN.finditer(result))
        for m in reversed(matches):
            raw = m.group(0)
            clean_digits = re.sub(r"\D", "", raw)
            if 13 <= len(clean_digits) <= 19:
                detected_types.append("credit_card")
                start, end = m.span()
                result = result[:start] + "[REDACTED_CREDIT_CARD]" + result[end:]

        # 4. Email
        def replace_email(match):
            detected_types.append("email")
            return "[REDACTED_EMAIL]"

        result = self.EMAIL_PATTERN.sub(replace_email, result)

        # 5. Phone
        def replace_phone(match):
            detected_types.append("phone")
            return "[REDACTED_PHONE]"

        result = self.PHONE_PATTERN.sub(replace_phone, result)

        has_pii = len(detected_types) > 0
        return result, has_pii, list(set(detected_types))
