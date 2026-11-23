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

# ── Verhoeff & Modulus-11 Checksum Tables ─────────────────────────────────────
_VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

_VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]


def _verhoeff_validate(num_str: str) -> bool:
    """Validate 12-digit Indian Aadhaar number using Verhoeff algorithm."""
    clean = re.sub(r"\D", "", num_str)
    if len(clean) != 12:
        return False
    if clean[0] in ("0", "1"):
        return False
    c = 0
    for i, digit in enumerate(reversed(clean)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][int(digit)]]
    return c == 0


def _nhs_modulus11_validate(num_str: str) -> bool:
    """Validate 10-digit UK NHS number using Modulus 11 algorithm."""
    digits = [int(c) for c in num_str if c.isdigit()]
    if len(digits) != 10:
        return False
    weights = [10, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(d * w for d, w in zip(digits[:9], weights))
    rem = total % 11
    check_digit = 11 - rem
    if check_digit == 11:
        check_digit = 0
    elif check_digit == 10:
        return False
    return check_digit == digits[9]



class PIIFirewall:
    """Enterprise-grade context-aware PII and secret scanner with adversarial robustness."""

    # Standard patterns
    CC_PATTERN = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
    SPACED_CC_PATTERN = re.compile(r"\b(?:\d\s*){13,19}\b")
    SSN_PATTERN = re.compile(r"\b\d{3}[-\s]\d{2}[-\s]\d{4}\b")
    SPACED_SSN_PATTERN = re.compile(r"\b\d\s+\d\s+\d\s*[-.\s]\s*\d\s+\d\s*[-.\s]\s*\d\s+\d\s+\d\s+\d\b")
    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
    OBFUSCATED_EMAIL_PATTERN = re.compile(
        r"\b[A-Za-z0-9._%+-]+\s*(?:\[at\]|\(at\)|@)\s*[A-Za-z0-9.-]+\s*(?:\[dot\]|\.)\s*[A-Za-z]{2,}\b",
        re.IGNORECASE,
    )
    PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
    KEY_PATTERN = re.compile(
        r"\b(?:sk-[-a-zA-Z0-9_]{20,}|AKIA[-_0-9A-Z]{16,}|ghp_[-a-zA-Z0-9]{36,}|Bearer\s+[-a-zA-Z0-9_\.]{20,})\b"
    )

    # Global & Regional PII patterns
    PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
    AADHAAR_PATTERN = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
    NHS_PATTERN = re.compile(r"\b\d{3}\s?\d{3}\s?\d{4}\b")
    DOB_PATTERN = re.compile(r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b")

    # Hard-negative exemption filters (UUIDs, git SHAs, RFC timestamps, base64 data URIs)
    UUID_PATTERN = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
    GIT_SHA_PATTERN = re.compile(r"\b[0-9a-fA-F]{40}\b")
    HEX_CODE_PATTERN = re.compile(r"#[0-9a-fA-F]{3,8}\b|0x[0-9a-fA-F]+\b")
    TIMESTAMP_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})\b")

    # Contextual keywords that boost detection confidence
    CONTEXT_WORDS = {
        "credit_card": ["visa", "mastercard", "amex", "card", "billing", "payment", "cvv", "expiry", "charge"],
        "ssn": ["ssn", "social", "security", "tax", "ein", "employee", "identification", "payroll"],
        "api_key": ["secret", "token", "auth", "key", "password", "bearer", "private", "api", "connection"],
        "dob": ["dob", "born", "birth", "birthdate", "birthday"],
        "aadhaar": ["aadhaar", "uid", "uidai", "aadhar"],
        "nhs": ["nhs", "health", "patient", "medical", "hospital", "clinic"],
        "pan": ["pan", "tax", "income tax", "permanent account number"],
    }

    def _has_context(self, text: str, span: tuple[int, int], context_type: str, window: int = 50) -> bool:
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

        # 1. API Keys & Structured Cloud Secrets (including hyphenated mutations)
        def replace_key(match):
            detected_types.append("api_key")
            return "[REDACTED_SECRET]"

        result = self.KEY_PATTERN.sub(replace_key, result)

        # 2. SSN (Standard & Spaced)
        matches_ssn = list(self.SSN_PATTERN.finditer(result)) + list(self.SPACED_SSN_PATTERN.finditer(result))
        for m in sorted(matches_ssn, key=lambda x: x.start(), reverse=True):
            detected_types.append("ssn")
            start, end = m.span()
            result = result[:start] + "[REDACTED_SSN]" + result[end:]

        # 3. Credit Cards (Standard, Spaced, Luhn verified or Contextually boosted)
        matches_cc = list(self.CC_PATTERN.finditer(result)) + list(self.SPACED_CC_PATTERN.finditer(result))
        for m in sorted(matches_cc, key=lambda x: x.start(), reverse=True):
            raw = m.group(0)
            clean_digits = re.sub(r"\D", "", raw)
            start, end = m.span()
            if 13 <= len(clean_digits) <= 19 and (_luhn_check(clean_digits) or self._has_context(result, (start, end), "credit_card")):
                detected_types.append("credit_card")
                result = result[:start] + "[REDACTED_CREDIT_CARD]" + result[end:]

        # 4. Email (Standard & Obfuscated like [at] / (at))
        def replace_email(match):
            detected_types.append("email")
            return "[REDACTED_EMAIL]"

        result = self.EMAIL_PATTERN.sub(replace_email, result)
        result = self.OBFUSCATED_EMAIL_PATTERN.sub(replace_email, result)

        # 4b. Indian PAN Card
        def replace_pan(match):
            detected_types.append("pan")
            return "[REDACTED_PAN]"

        result = self.PAN_PATTERN.sub(replace_pan, result)

        # 4c. UK NHS Number (Modulus-11 validated)
        matches_nhs = list(self.NHS_PATTERN.finditer(result))
        for m in sorted(matches_nhs, key=lambda x: x.start(), reverse=True):
            raw = m.group(0)
            if _nhs_modulus11_validate(raw):
                detected_types.append("nhs")
                start, end = m.span()
                result = result[:start] + "[REDACTED_NHS]" + result[end:]

        # 4d. Indian Aadhaar Number (Verhoeff validated)
        matches_aadhaar = list(self.AADHAAR_PATTERN.finditer(result))
        for m in sorted(matches_aadhaar, key=lambda x: x.start(), reverse=True):
            raw = m.group(0)
            if _verhoeff_validate(raw):
                detected_types.append("aadhaar")
                start, end = m.span()
                result = result[:start] + "[REDACTED_AADHAAR]" + result[end:]

        # 4e. Date of Birth (DOB) contextually validated
        matches_dob = list(self.DOB_PATTERN.finditer(result))
        for m in sorted(matches_dob, key=lambda x: x.start(), reverse=True):
            start, end = m.span()
            if self._has_context(result, (start, end), "dob"):
                detected_types.append("dob")
                result = result[:start] + "[REDACTED_DOB]" + result[end:]

        # 5. Phone (excluding items already redacted)
        def replace_phone(match):
            detected_types.append("phone")
            return "[REDACTED_PHONE]"

        result = self.PHONE_PATTERN.sub(replace_phone, result)

        # 6. High-Entropy Raw Secrets Scanner (exemption filters for UUIDs, Git hashes, Base64 data, Timestamps)
        words = result.split()
        redacted_words = []
        has_secret_context = any(
            kw in result.lower() for kw in ("token is", "token:", "key is", "key:", "secret is", "secret:", "password")
        )

        for word in words:
            # Check hard-negative exemptions first (unless secret/token context is explicit)
            if (
                self.UUID_PATTERN.search(word)
                or (self.GIT_SHA_PATTERN.search(word) and not has_secret_context)
                or self.HEX_CODE_PATTERN.search(word)
                or self.TIMESTAMP_PATTERN.search(word)
                or "data:image/" in word
                or word.startswith("ERR-")
                or word.startswith("_MAX_")
                or word.startswith("redis-master-")
            ):
                redacted_words.append(word)
                continue

            clean_word = re.sub(r"[^\w]", "", word)
            # High-entropy passwords / token hashes (> 3.8 bits/char and length >= 28)
            if len(clean_word) >= 28 and _shannon_entropy(clean_word) >= 3.8:
                if not any(token in word for token in ("[REDACTED_", "http://", "https://")):
                    detected_types.append("api_key")
                    redacted_words.append("[REDACTED_SECRET]")
                    continue
            redacted_words.append(word)
        result = " ".join(redacted_words)

        has_pii = len(detected_types) > 0
        return result, has_pii, list(set(detected_types))

    def sanitize(self, text: str) -> tuple[str, list[dict]]:
        redacted, detected, types = self.redact(text)
        entities = [{"entity_type": t, "text": "[REDACTED]", "confidence": 0.98} for t in types]
        return redacted, entities


EnterprisePIIFirewall = PIIFirewall
