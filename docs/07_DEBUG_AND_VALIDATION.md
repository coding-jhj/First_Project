# Debug And Validation

## 주요 디버깅 주제

- 탐지 박스 불일치
- FPS 저하
- ONNX 추론 지연
- 서버/Android 문장 규칙 불일치
- 계단/낙차/바닥 위험 표현
- 경고 피로 방지

## 검증 기준

- 핵심 테스트는 `tests/test_sentence.py`, `tests/test_detect.py`를 우선 확인합니다.
- 발표 전에는 실제 카메라 환경에서 FPS와 안내 문장을 함께 확인합니다.
- 실패 사례 이미지와 실험 결과는 `legacy/results/`에 보관합니다.

## 상세 원본

- `legacy/md/DETECTION_DEBUG.md`
- `legacy/md/BOUNDING_BOX_FIX.md`
- `legacy/md/PERF_DEBUG.md`
- `legacy/md/CALIBRATION_TEST.md`
- `legacy/md/troubleshooting.md`
- `legacy/md/ALERT_FATIGUE_GUIDE.md`
- `legacy/md/phase4_vision_validation.md`
- `legacy/md/stairs_pseudo_label.md`
- `legacy/md/eval_log.md`

