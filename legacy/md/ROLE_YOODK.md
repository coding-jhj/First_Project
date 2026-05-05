# 신유득 역할 가이드

> 현재 역할: Vision, ML  
> 과거 서버/GCP 담당 문서는 더 이상 기준 문서가 아닙니다. 서버와 GCP는 정환주가 담당하고, 신유득은 탐지/Depth/OCR/평가를 맡습니다.

## 책임 범위

| 영역 | 할 일 |
|---|---|
| YOLO | `src/vision/detect.py` 탐지 흐름과 class별 threshold 설명 |
| Depth | `src/depth/depth.py`의 Depth V2/fallback 동작 확인 |
| Hazard | `src/depth/hazard.py` 계단/낙차 후보 감지 한계 정리 |
| OCR | `src/ocr/bus_ocr.py`는 실험 기능으로 분리 설명 |
| 평가 | `tools/benchmark.py`, `results/`에 성공/실패 케이스 기록 |

## 먼저 읽을 파일

1. `src/vision/detect.py`
2. `src/depth/depth.py`
3. `src/depth/hazard.py`
4. `src/ocr/bus_ocr.py`
5. `docs/01_study/FUNCTION_LOGIC_STUDY.md`

## 발표 때 말할 핵심

```text
저는 Vision과 ML을 담당했습니다.
YOLO 탐지 결과가 방향, 거리 추정, 위험도 계산으로 이어지는 과정을 검증했습니다.
Depth V2가 있으면 상대 깊이 기반으로 보조 추정하고, 없거나 실패하면 bbox 기반 fallback으로 동작합니다.
OCR과 신호등/계단 감지는 실험 기능으로 분리해 과장하지 않겠습니다.
```

## 오늘 할 일

- [ ] `detect_objects()` 처리 순서를 직접 설명해 보기
- [ ] `detect_and_depth()`에서 `depth_source`가 `v2`인지 `bbox`인지 확인
- [ ] 오탐 이미지 5개와 실패 이유 기록
- [ ] README의 Vision/ML 설명이 실제 코드와 맞는지 검수
- [ ] "정확한 거리"가 아니라 "대략적 거리 추정"이라고 표현했는지 확인
