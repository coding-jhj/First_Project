# 신유득 TODO

> 과거에는 GCP 배포를 신유득 담당으로 적었지만, 현재 기준에서는 정환주가 서버/GCP/프론트엔드를 담당합니다.  
> 이 문서는 신유득의 현재 역할인 Vision/ML TODO로 재정리합니다.

## Vision/ML 체크리스트

- [ ] `src/vision/detect.py`의 `detect_objects()` 처리 순서 설명
- [ ] class별 `CLASS_MIN_CONF`가 왜 다른지 정리
- [ ] `CLASS_RISK_MULTIPLIER`에서 차량/동물/일반 물체의 차이 설명
- [ ] `src/depth/depth.py`에서 Depth V2 모델 로드 실패 시 fallback 확인
- [ ] `depth_source`가 `v2`인지 `bbox`인지 서버 응답에서 확인
- [ ] 계단/낙차 감지는 실험 기능으로 문서에 분리
- [ ] OCR은 발표 시 "실험 기능"으로만 설명
- [ ] 오탐/미탐 케이스를 `results/` 문서에 기록

## 정환주에게 전달할 것

- 모델 파일명과 실제 사용 여부
- Depth V2가 GCP에서 로드되는지 여부
- benchmark 또는 수동 테스트 결과
- README에서 과장된 Vision/ML 표현이 있으면 수정 요청
