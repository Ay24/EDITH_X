"""M4 — Context-Boosted PII & High-Entropy Secret Redaction Firewall (Reverse-Engineered from Presidio)."""
from __future__ import annotations

import math
import re
from collections import Counter


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


def _shannon_entropy(data: str) -> float:
    """Calculate Shannon entropy (bits per character) to detect high-entropy keys/passwords."""
    if not data:
        return 0.0
    entropy = 0.0
    length = len(data)
    for count in Counter(data).values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy


class PIIFirewall:
    """Enterprise-grade context-aware PII and secret scanner."""

    CC_PATTERN = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
    SSN_PATTERN = re.compile(r"\b\d{3}[-\s]\d{2}[-\s]\d{4}\b")
    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
    PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
    KEY_PATTERN = re.compile(
        r"\b(?:sk-[a-zA-Z0-9_\-]{20,}|AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}|Bearer\s+[a-zA-Z0-9_\-\.]{20,})\b"
    )

    # Contextual keywords that boost detection confidence
    CONTEXT_WORDS = {
        "credit_card": ["visa", "mastercard", "amex", "card", "billing", "payment", "cvv", "expiry"],
        "ssn": ["ssn", "social", "security", "tax", "ein", "employee", "identification"],
        "api_key": ["secret", "token", "auth", "key", "password", "bearer", "private"],
    }

    def _has_context(self, text: str, span: tuple[int, int], context_type: str, window: int = 40) -> bool:
        start, end = span
        context_window = (
            text[max(0, start - window):start] + " " + text[end:min(len(text), end + window)]
        ).lower()
        keywords = self.CONTEXT_WORDS.get(context_type, [])
        return any(kw in context_window for kw in keywords)

    def redact(self, text: str) -> tuple[str, bool, list[str]]:
        """
        Scan and redact PII and enterprise secrets.
        Returns:
            (redacted_text, detected_boolean, list_of_detected_types)
        """
        detected_types: list[str] = []
        result = text

        # 1. API Keys & Structured Cloud Secrets
        def replace_key(match):
            detected_types.append("api_key")
            return "[REDACTED_SECRET]"

        result = self.KEY_PATTERN.sub(replace_key, result)

        # 2. SSN
        matches_ssn = list(self.SSN_PATTERN.finditer(result))
        for m in reversed(matches_ssn):
            detected_types.append("ssn")
            start, end = m.span()
            result = result[:start] + "[REDACTED_SSN]" + result[end:]

        # 3. Credit Cards (Validation + Context Check)
        matches_cc = list(self.CC_PATTERN.finditer(result))
        for m in reversed(matches_cc):
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

        # 6. High-Entropy Raw Secrets Scanner (Passwords / Token Hashes > 3.8 bits/char with length > 24)
        words = result.split()
        redacted_words = []
        for word in words:
            clean_word = re.sub(r"[^\w]", "", word)
            if len(clean_word) >= 28 and _shannon_entropy(clean_word) >= 3.8:
                if not any(token in word for token in ("[REDACTED_", "http://", "https://")):
                    detected_types.append("api_key")
                    redacted_words.append("[REDACTED_SECRET]")
                    continue
            redacted_words.append(word)
        result = " ".join(redacted_words)

        has_pii = len(detected_types) > 0
        return result, has_pii, list(set(detected_types))
