"""
더미 장면 추론 모듈.

YOLO11n TFLite 모델로 미리 준비된 테스트 이미지를 추론해
서버 /detect 포맷의 탐지 결과를 반환합니다.

TFLite/tensorflow 미설치 환경에서는 자동으로 PT 모델로 fallback하고,
PT 모델도 없으면 장면별 사전 정의된 더미 데이터를 반환합니다.

사용법:
    import dummy_scenes
    dummy_scenes.load_model()
    objects = dummy_scenes.run_scene(dummy_scenes.SCENE_BUS)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import ultralytics as _ul

# ── COCO 클래스 인덱스 → 한국어 이름 (VoiceGuide policy.json 기준) ─────────────
COCO_KO: dict[int, str] = {
    0:  "사람",       1:  "자전거",     2:  "자동차",     3:  "오토바이",
    5:  "버스",       6:  "기차",       7:  "트럭",       9:  "신호등",
    13: "벤치",       16: "개",         17: "말",         24: "배낭",
    25: "우산",       26: "핸드백",     28: "여행가방",
    56: "의자",       57: "소파",       58: "화분",       60: "테이블",
    63: "노트북",     67: "휴대폰",     73: "책",         74: "시계",
}

# ── ultralytics 패키지 내장 테스트 이미지 ─────────────────────────────────────
_ASSETS   = Path(_ul.__file__).parent / "assets"
SCENE_BUS    = str(_ASSETS / "bus.jpg")
SCENE_PERSON = str(_ASSETS / "zidane.jpg")
SCENE_CAUTION = "__caution__"   # 합성 키 — 실제 이미지 없이 주의·안전 물체만 반환

# ── 설정 ──────────────────────────────────────────────────────────────────────
MODEL_PATH  = "android/app/src/main/assets/yolo11n_320.tflite"
CONF_THRESH = 0.30

# ── 장면별 사전 정의 더미 결과 (TFLite/PT 모델 모두 없을 때 사용) ─────────────
# bbox_norm_xywh: [x_center_approx, y_top, width, height] (정규화된 좌표)
_DUMMY_RESULTS: dict[str, list[dict]] = {
    SCENE_BUS: [
        {"class_ko": "버스",    "confidence": 0.91, "bbox_norm_xywh": [0.05, 0.30, 0.60, 0.55]},  # critical_ko
        {"class_ko": "자전거",  "confidence": 0.78, "bbox_norm_xywh": [0.65, 0.50, 0.12, 0.35]},  # critical_ko
        {"class_ko": "사람",    "confidence": 0.85, "bbox_norm_xywh": [0.70, 0.40, 0.15, 0.50]},  # 거리 기반
        {"class_ko": "배낭",    "confidence": 0.66, "bbox_norm_xywh": [0.72, 0.60, 0.08, 0.25]},  # caution_ko
        {"class_ko": "벤치",    "confidence": 0.55, "bbox_norm_xywh": [0.10, 0.65, 0.25, 0.20]},  # everyday_ko
    ],
    SCENE_PERSON: [
        {"class_ko": "사람",      "confidence": 0.94, "bbox_norm_xywh": [0.20, 0.10, 0.35, 0.70]},  # 거리 기반
        {"class_ko": "핸드백",    "confidence": 0.73, "bbox_norm_xywh": [0.35, 0.55, 0.10, 0.20]},  # caution_ko
        {"class_ko": "여행가방",  "confidence": 0.68, "bbox_norm_xywh": [0.60, 0.60, 0.15, 0.30]},  # caution_ko
        {"class_ko": "우산",      "confidence": 0.59, "bbox_norm_xywh": [0.55, 0.15, 0.08, 0.50]},  # everyday_ko
    ],
    SCENE_CAUTION: [
        {"class_ko": "배낭",  "confidence": 0.80, "bbox_norm_xywh": [0.30, 0.25, 0.18, 0.35]},  # caution_ko
        {"class_ko": "화분",  "confidence": 0.62, "bbox_norm_xywh": [0.70, 0.55, 0.12, 0.30]},  # everyday_ko
        {"class_ko": "의자",  "confidence": 0.55, "bbox_norm_xywh": [0.15, 0.50, 0.20, 0.35]},  # everyday_ko
    ],
}

_model = None        # YOLO 모델 인스턴스 (None이면 더미 모드)
_dummy_mode = False  # True이면 사전 정의 더미 데이터 반환


def load_model(path: str = MODEL_PATH) -> None:
    """
    TFLite → PT 순서로 모델 로드를 시도한다.
    모두 실패하면 더미 모드로 전환 (데모 시 모델 미설치 환경 대응).
    """
    global _model, _dummy_mode
    if _model is not None or _dummy_mode:
        return

    try:
        from ultralytics import YOLO
    except (ImportError, Exception) as e:
        print(f"  [dummy_scenes] ultralytics.YOLO 임포트 실패: {e}")
        _dummy_mode = True
        print("  [dummy_scenes] 더미 모드 전환 — 사전 정의 탐지 결과 사용")
        return

    # 1차 시도: TFLite 모델
    if os.path.exists(path):
        try:
            candidate = YOLO(path, task="detect")
            # 실제 추론이 가능한지 확인 (객체 생성만으로는 backend 로드 안 됨)
            test_img = SCENE_BUS if os.path.exists(SCENE_BUS) else None
            if test_img:
                candidate(test_img, conf=CONF_THRESH, verbose=False)
            _model = candidate
            print(f"  [dummy_scenes] TFLite 모델 로드 완료: {path}")
            return
        except Exception as e:
            print(f"  [dummy_scenes] TFLite 로드 실패: {e}")

    # 2차 시도: ultralytics 기본 PT 모델 (자동 다운로드)
    try:
        candidate = YOLO("yolo11n.pt")
        _model = candidate
        print("  [dummy_scenes] PT 모델(yolo11n.pt) fallback 로드 완료")
        return
    except Exception as e:
        print(f"  [dummy_scenes] PT 모델 로드 실패: {e}")

    # 모두 실패 → 더미 모드
    _dummy_mode = True
    print("  [dummy_scenes] 더미 모드 전환 — 사전 정의 탐지 결과 사용")


def run_scene(image_path: str) -> list[dict]:
    """
    이미지를 YOLO로 추론하고 서버 /detect 포맷의 탐지 결과 목록을 반환한다.

    모델 미설치 시 사전 정의 더미 데이터를 반환하므로 항상 성공한다.

    반환 예시:
        [
          {"class_ko": "버스",  "confidence": 0.91,
           "bbox_norm_xywh": [0.12, 0.08, 0.55, 0.70]},
          {"class_ko": "사람", "confidence": 0.85,
           "bbox_norm_xywh": [0.60, 0.15, 0.18, 0.60]},
        ]
    """
    if _dummy_mode:
        # 합성 키(__caution__ 등) 직접 일치 우선
        if image_path in _DUMMY_RESULTS:
            return [dict(r) for r in _DUMMY_RESULTS[image_path]]
        # 실제 이미지 경로는 파일명으로 매칭
        basename = os.path.basename(image_path)
        for key, results in _DUMMY_RESULTS.items():
            if os.path.basename(key) == basename:
                return [dict(r) for r in results]
        # 매핑 없으면 사람 1명
        return [{"class_ko": "사람", "confidence": 0.80,
                 "bbox_norm_xywh": [0.35, 0.20, 0.30, 0.60]}]

    if _model is None:
        raise RuntimeError("load_model()을 먼저 호출하세요.")

    results = _model(image_path, conf=CONF_THRESH, verbose=False)[0]
    objects: list[dict] = []

    for box in results.boxes:
        cls_idx = int(box.cls.item())
        conf    = round(float(box.conf.item()), 4)

        x1, y1, x2, y2 = box.xyxyn.tolist()[0]
        w = round(x2 - x1, 4)
        h = round(y2 - y1, 4)

        objects.append({
            "class_ko":       COCO_KO.get(cls_idx, f"물체{cls_idx}"),
            "confidence":     conf,
            "bbox_norm_xywh": [round(x1, 4), round(y1, 4), w, h],
        })

    return objects
