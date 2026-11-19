"""Tamper-Evident SHA-256 Hash-Chained Audit Ledger for Enterprise Compliance (SOC2 / HIPAA)."""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any


class AuditLedger:
    """Cryptographically chained append-only audit ledger ensuring non-repudiation."""

    def __init__(self, ledger_file: Path | str | None = None) -> None:
        self._ledger_path = Path(ledger_file) if ledger_file else None
        self._chain: list[dict[str, Any]] = []
        self._last_hash = "GENESIS_BLOCK_00000000000000000000000000000000000000000000000000000000"

        if self._ledger_path and self._ledger_path.exists():
            self._load_ledger()

    def _compute_hash(self, entry_dict: dict[str, Any]) -> str:
        # Canonical serialization without the entry_hash itself
        payload = {k: v for k, v in entry_dict.items() if k != "entry_hash"}
        canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    def _load_ledger(self) -> None:
        if not self._ledger_path:
            return
        with open(self._ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    self._chain.append(entry)
                    self._last_hash = entry.get("entry_hash", self._last_hash)

    def record_event(
        self,
        action: str,
        user_id: str,
        org_id: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record a structured event into the cryptographic chain."""
        now = time.time()
        event_id = str(uuid.uuid4())
        entry = {
            "event_id": event_id,
            "timestamp": now,
            "action": action,
            "user_id": user_id,
            "org_id": org_id,
            "details": details or {},
            "prev_hash": self._last_hash,
        }
        entry_hash = self._compute_hash(entry)
        entry["entry_hash"] = entry_hash

        self._chain.append(entry)
        self._last_hash = entry_hash

        if self._ledger_path:
            self._ledger_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._ledger_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")

        return entry

    def verify_integrity(self) -> tuple[bool, int]:
        """Verify the cryptographic hash chain of all recorded events."""
        current_prev = "GENESIS_BLOCK_00000000000000000000000000000000000000000000000000000000"
        for idx, entry in enumerate(self._chain):
            if entry.get("prev_hash") != current_prev:
                return False, idx
            expected_hash = self._compute_hash(entry)
            if entry.get("entry_hash") != expected_hash:
                return False, idx
            current_prev = entry.get("entry_hash", "")
        return True, len(self._chain)

    def get_entries(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._chain[-limit:]
