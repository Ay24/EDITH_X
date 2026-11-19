"""EDITH-X Package Init"""
from __future__ import annotations

import os

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
os.environ.setdefault("LITELLM_TELEMETRY", "False")

from edith_x.core.config import Settings, get_settings

__version__ = "0.1.0"
__all__ = ["Settings", "get_settings"]
