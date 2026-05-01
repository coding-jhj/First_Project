# 신유득 Vision/ML TODO

현재 기준에서 신유득 담당은 GCP가 아니라 Vision/ML입니다.

## 목표

오탐을 줄이고, 모델/threshold/fallback 상태를 팀원이 설명할 수 있게 만듭니다.

## 해야 할 일

| 우선순위 | 작업 | 결과물 |
|---|---|---|
| P0 | 오탐 클래스 5개 이상 정리 | 이미지/상황/현재 confidence/조치 표 |
| P0 | `src/vision/detect.py` class별 threshold 확인 | 변경 전후 비교표 |
| P1 | Depth V2 loaded/fallback 상태 확인 | `/health` 캡처 또는 로그 |
| P1 | bbox 거리 추정 한계 정리 | 발표용 한계 문장 |
| P1 | OCR/신호등/계단 기능을 실험 기능으로 분리 | README/발표 표현 확인 |
| P2 | `tools/benchmark.py`로 성능 측정 | 평균 처리 시간 |

## 보면 되는 코드

| 파일 | 함수 |
|---|---|
| `src/vision/detect.py` | `detect_objects`, `_compute_scene_analysis` |
| `src/depth/depth.py` | `detect_and_depth`, `_infer_depth_map`, `_bbox_dist_m` |
| `src/depth/hazard.py` | `detect_floor_hazards` |
| `src/ocr/bus_ocr.py` | `recognize_bus_number` |
| `tools/benchmark.py` | 벤치마크 실행 흐름 |

## 조사 기준

1. "정확도 높음"처럼 말하지 말고, 실패 사례를 같이 적습니다.
2. 오탐은 class 이름, 상황, 조명, 거리, bbox 크기를 같이 기록합니다.
3. Android FPS 개선과 충돌할 수 있으므로 김재현과 모델 크기/threshold를 같이 봅니다.
4. 발표에서는 "대략 거리 추정", "후보 감지", "실험 기능" 같은 표현을 씁니다.
