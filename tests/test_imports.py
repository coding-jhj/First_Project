"""라이브러리 import 체크 — 서버 없이 실행 가능 (CI용)."""
import importlib
import pytest

# 서버와 Android ONNX 모델 준비 도구에 필요한 핵심 라이브러리
CORE_LIBS = ["cv2", "ultralytics", "torch", "numpy", "fastapi"]


@pytest.mark.parametrize("lib", CORE_LIBS)
def test_core_import(lib):
    """핵심 서버 라이브러리 import 확인 — CI에서 항상 실행"""
    mod = importlib.import_module(lib)
    assert mod is not None

