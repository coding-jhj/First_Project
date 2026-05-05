"""policy.json SSOT 로더·문장 거리 표현 회귀."""

from src.config.policy import get_policy, init_policy, class_set
from src.nlg.sentence import _format_dist


def test_policy_loads():
    init_policy()
    p = get_policy()
    assert p["version"] >= 1
    assert "버스" in class_set("vehicle_ko")
    assert "의자" in class_set("everyday_ko")


def test_format_dist_uses_policy_thresholds():
    assert _format_dist(0.3) == "코앞"
    assert "약" in _format_dist(1.2) and "미터" in _format_dist(1.2)
    assert _format_dist(5.0).startswith("약 5")
