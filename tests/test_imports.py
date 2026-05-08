"""라이브러리 import 체크 — 서버 없이 실행 가능 (CI용)."""
import importlib
import pytest

# MVP 서버 런타임은 Android가 만든 탐지 JSON만 처리한다.
# torch/ultralytics는 학습·내보내기 도구용이라 서버 CI import 필수값에서 제외한다.
CORE_LIBS = ["cv2", "numpy", "fastapi"]


@pytest.mark.parametrize("lib", CORE_LIBS)
def test_core_import(lib):
    """핵심 서버 라이브러리 import 확인 — CI에서 항상 실행"""
    mod = importlib.import_module(lib)
    assert mod is not None
