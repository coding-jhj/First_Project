## vision_ML

이 저장소는 VoiceGuide 프로젝트의 **Vision/ML 검증(Phase 4)**을 빠르게 재현하기 위한 최소 도구를 포함합니다.

### 빠른 실행 (Phase 4)

테스트 이미지 자동 수집(의자·사람):

```bash
python tools/build_test_images.py
```

벤치마크 실행 (결과는 `results/eval_log.md`에 누적 기록):

```bash
python tools/benchmark.py
```

조건별(야간/주간 등) 탐지 지표 — 먼저 이미지 수집 후:

```bash
python tools/build_condition_test_images.py
python tools/benchmark_conditions.py
```

Depth 보정 — 알려진 거리(m)의 물체가 찍힌 한 장으로 `DEPTH_SCALE` 추정 (`depth_anything_v2_vits.pth` 필요):

```bash
python tools/calibrate_depth.py --image path/to.jpg --known-meters 2.0
```

보정 후 미터 오차(MAE/RMSE) — 실측이 적힌 CSV + 같은 폴더의 이미지:

```bash
# data/depth_truth/truth.csv.example 참고해 truth.csv 작성
python tools/validate_depth_meters.py --truth-csv data/depth_truth/truth.csv --image-dir data/depth_truth
```

### 결과 확인

- `results/eval_log.md`: 실행 시간, 파이프라인 검증, 방향 정확도, 문장 생성 테스트, **Precision/Recall/F1/FPR**, **FPR 상위 클래스**, 실패 시 경로 안내
- `results/failure_cases/<시간>/`: 오탐·누락 샘플 이미지 최대 5장 + `manifest.json`
- `results/condition_eval.md`: 야간·주간 등 조건별 지표
- `results/depth_meter_error.md`: 실측 대비 거리 오차(보정 검증)

의존성 참고: `requirements-phase4.txt`

상세 요약: `docs/phase4_vision_validation.md`
