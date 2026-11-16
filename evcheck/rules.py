"""The checking rules: evidence-check's script, the same file the Agent Skill runs.

A built package carries the script as evcheck/_rules.py (pyproject.toml copies it in); a source checkout
loads it from skills/evidence-check/scripts/, so there is one copy of the rules to change.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

try:
    from . import _rules as ce  # type: ignore[attr-defined]
except ImportError:  # running from a source checkout
    _path = Path(__file__).resolve().parents[1] / "skills" / "evidence-check" / "scripts" / "check_evidence.py"
    _spec = importlib.util.spec_from_file_location("evcheck._rules", _path)
    ce = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(ce)

__all__ = ["ce"]
