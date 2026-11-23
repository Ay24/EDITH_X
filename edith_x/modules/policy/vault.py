"""Ephemeral Pseudonymization Vault for Reversible PII Tokenization (Point 5)."""
from __future__ import annotations

import hashlib
import re
import secrets
import time
from dataclasses import dataclass, field
from collections import OrderedDict

from edith_x.modules.policy.firewall import PIIFirewall, _luhn_check, _verhoeff_validate, _nhs_modulus11_validate


@dataclass
class VaultTokenEntry:
    token: str
    original_value: str
    entity_type: str


@dataclass
class VaultSession:
    session_id: str
    created_at: float
    expires_at: float
    token_map: dict[str, VaultTokenEntry] = field(default_factory=dict)


def _mask_value(val: str, entity_type: str) -> str:
    """Generate PCI/privacy-compliant masked representations."""
    if entity_type == "credit_card":
        clean_digits = re.sub(r"\D", "", val)
        if len(clean_digits) >= 12:
            return f"{clean_digits[:4]} **** **** {clean_digits[-4:]}"
        return f"{val[:2]}****{val[-2:]}" if len(val) > 4 else "****"

    if entity_type == "email":
        parts = val.split("@")
        if len(parts) == 2:
            name, domain = parts
            masked_name = f"{name[0]}***{name[-1]}" if len(name) > 2 else f"{name[:1]}***"
            return f"{masked_name}@{domain}"
        return f"{val[:2]}***@{val.split('@')[-1]}"

    if entity_type == "ssn":
        clean = re.sub(r"\D", "", val)
        return f"***-**-{clean[-4:]}" if len(clean) >= 4 else "***-**-****"

    if entity_type == "aadhaar":
        clean = re.sub(r"\D", "", val)
        return f"**** **** {clean[-4:]}" if len(clean) >= 4 else "**** **** ****"

    if entity_type == "pan":
        return f"{val[:3]}****{val[-3:]}" if len(val) >= 6 else "*****"

    if len(val) > 4:
        return f"{val[:2]}****{val[-2:]}"
    return "****"


class EphemeralVault:
    """In-memory ephemeral vault providing reversible pseudonymization with automatic TTL pruning."""

    def __init__(self, default_ttl_seconds: float = 60.0, max_sessions: int = 10000) -> None:
        self.default_ttl = default_ttl_seconds
        self.max_sessions = max_sessions
        self._sessions: OrderedDict[str, VaultSession] = OrderedDict()
        self._firewall = PIIFirewall()

    def _generate_token_name(self, entity_type: str, raw_val: str) -> str:
        tag_map = {
            "credit_card": "CARD_REF",
            "email": "EMAIL_REF",
            "ssn": "SSN_REF",
            "aadhaar": "AADHAAR_REF",
            "pan": "PAN_REF",
            "nhs": "NHS_REF",
            "phone": "PHONE_REF",
            "api_key": "SECRET_REF",
            "dob": "DOB_REF",
        }
        prefix = tag_map.get(entity_type, "ENTITY_REF")
        h = hashlib.sha256(raw_val.encode()).hexdigest()[:4].upper()
        return f"{{{{{prefix}_{h}}}}}"

    def tokenize(self, text: str, session_id: str | None = None) -> tuple[str, str]:
        """
        Scan text for PII/secrets, replace each with a typed surrogate token,
        and store the mapping in an ephemeral session.
        """
        self.prune_expired()
        sid = session_id or secrets.token_hex(16)
        now = time.time()

        if sid in self._sessions:
            session = self._sessions[sid]
        else:
            if len(self._sessions) >= self.max_sessions:
                self._sessions.popitem(last=False)
            session = VaultSession(session_id=sid, created_at=now, expires_at=now + self.default_ttl)
            self._sessions[sid] = session

        result = text
        token_map = session.token_map

        # Scan and tokenize entities in order of specificity

        # 1. API Keys
        matches_keys = list(self._firewall.KEY_PATTERN.finditer(result))
        for m in sorted(matches_keys, key=lambda x: x.start(), reverse=True):
            raw = m.group(0)
            tok = self._generate_token_name("api_key", raw)
            token_map[tok] = VaultTokenEntry(token=tok, original_value=raw, entity_type="api_key")
            start, end = m.span()
            result = result[:start] + tok + result[end:]

        # 2. PAN
        matches_pan = list(self._firewall.PAN_PATTERN.finditer(result))
        for m in sorted(matches_pan, key=lambda x: x.start(), reverse=True):
            raw = m.group(0)
            tok = self._generate_token_name("pan", raw)
            token_map[tok] = VaultTokenEntry(token=tok, original_value=raw, entity_type="pan")
            start, end = m.span()
            result = result[:start] + tok + result[end:]

        # 3. NHS
        matches_nhs = list(self._firewall.NHS_PATTERN.finditer(result))
        for m in sorted(matches_nhs, key=lambda x: x.start(), reverse=True):
            raw = m.group(0)
            if _nhs_modulus11_validate(raw):
                tok = self._generate_token_name("nhs", raw)
                token_map[tok] = VaultTokenEntry(token=tok, original_value=raw, entity_type="nhs")
                start, end = m.span()
                result = result[:start] + tok + result[end:]

        # 4. Aadhaar
        matches_aadhaar = list(self._firewall.AADHAAR_PATTERN.finditer(result))
        for m in sorted(matches_aadhaar, key=lambda x: x.start(), reverse=True):
            raw = m.group(0)
            if _verhoeff_validate(raw):
                tok = self._generate_token_name("aadhaar", raw)
                token_map[tok] = VaultTokenEntry(token=tok, original_value=raw, entity_type="aadhaar")
                start, end = m.span()
                result = result[:start] + tok + result[end:]

        # 5. Credit Cards
        matches_cc = list(self._firewall.CC_PATTERN.finditer(result)) + list(self._firewall.SPACED_CC_PATTERN.finditer(result))
        for m in sorted(matches_cc, key=lambda x: x.start(), reverse=True):
            raw = m.group(0)
            clean_digits = re.sub(r"\D", "", raw)
            start, end = m.span()
            if 13 <= len(clean_digits) <= 19 and (_luhn_check(clean_digits) or self._firewall._has_context(result, (start, end), "credit_card")):
                tok = self._generate_token_name("credit_card", raw)
                token_map[tok] = VaultTokenEntry(token=tok, original_value=raw, entity_type="credit_card")
                result = result[:start] + tok + result[end:]

        # 6. Emails
        matches_email = list(self._firewall.EMAIL_PATTERN.finditer(result))
        for m in sorted(matches_email, key=lambda x: x.start(), reverse=True):
            raw = m.group(0)
            tok = self._generate_token_name("email", raw)
            token_map[tok] = VaultTokenEntry(token=tok, original_value=raw, entity_type="email")
            start, end = m.span()
            result = result[:start] + tok + result[end:]

        # 7. SSN
        matches_ssn = list(self._firewall.SSN_PATTERN.finditer(result)) + list(self._firewall.SPACED_SSN_PATTERN.finditer(result))
        for m in sorted(matches_ssn, key=lambda x: x.start(), reverse=True):
            raw = m.group(0)
            tok = self._generate_token_name("ssn", raw)
            token_map[tok] = VaultTokenEntry(token=tok, original_value=raw, entity_type="ssn")
            start, end = m.span()
            result = result[:start] + tok + result[end:]

        return result, sid

    def detokenize(self, text: str, session_id: str, mask_mode: str = "full") -> str:
        """
        Replace surrogate tokens in text with original values (mask_mode='full')
        or privacy-masked values (mask_mode='masked').
        """
        now = time.time()
        session = self._sessions.get(session_id)
        if not session or session.expires_at <= now:
            return text

        result = text
        for tok, entry in session.token_map.items():
            if tok in result:
                replacement = entry.original_value if mask_mode == "full" else _mask_value(entry.original_value, entry.entity_type)
                result = result.replace(tok, replacement)

        return result

    def prune_expired(self) -> int:
        """Remove sessions past their expiration timestamp."""
        now = time.time()
        expired_keys = [sid for sid, s in self._sessions.items() if s.expires_at <= now]
        for sid in expired_keys:
            self._sessions.pop(sid, None)
        return len(expired_keys)
