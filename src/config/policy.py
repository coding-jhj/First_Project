"""policy.json SSOT 로드·접근."""

from __future__ import annotations

import json
from pathlib import Path

_POLICY_PATH = Path(__file__).resolve().parent / "policy.json"
_policy: dict | None = None


def init_policy(path: Path | None = None) -> dict:
    """FastAPI lifespan 등에서 호출 — JSON을 메모리에 적재."""
    global _policy
    p = path or _POLICY_PATH
    with open(p, encoding="utf-8") as f:
        _policy = json.load(f)
    return _policy


def get_policy() -> dict:
    if _policy is None:
        init_policy()
    assert _policy is not None
    return _policy


def class_set(key: str) -> set[str]:
    return set(get_policy()["classes"][key])


def alert_thresholds() -> dict:
    return get_policy()["alert_mode"]


def distance_format() -> dict:
    return get_policy()["distance_format"]


def held_thresholds_m() -> dict:
    return get_policy()["held_sentence_m"]
