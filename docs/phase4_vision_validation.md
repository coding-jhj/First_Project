## Phase 4 — Vision/ML 검증 결과 요약

### 범위 (이번 제출 기준)

- **포함**: 탐지(Detection) + 방향 판단 + 문장 생성 안정성 + (가능 시) Depth 동작 여부
- **제외**: **버스(OCR)**, **계단(바닥 위험/계단 탐지)**  
  - 이유: 팀 내 합의로 MVP/평가 범위에서 제외
  - 코드 반영: `tools/benchmark.py`의 `EXCLUDED_CLASSES_KO = {"버스", "계단"}`

---

### 재현 방법

테스트 이미지 자동 수집(의자/사람):

```bash
python tools/build_test_images.py
```

벤치마크 실행:

```bash
python tools/benchmark.py
```

결과 파일:

- `results/eval_log.md` — 실행할 때마다 최신 결과가 아래에 추가됨
- `results/failure_cases/<타임스탬프>/` — 오류가 있을 때만 생성; 최대 5장 샘플 + `manifest.json`, 공통 패턴 요약

Depth 미터 보정(모델 파일 `depth_anything_v2_vits.pth` 필요):

```bash
python tools/calibrate_depth.py --image path/to.jpg --known-meters 2.0
```

버스 OCR 파이프라인(수집 → 시드 라벨 → 검수 → 평가):

```bash
python tools/build_bus_ocr_dataset.py
python tools/seed_bus_ocr_labels.py
python tools/eval_bus_ocr.py
```

조건별 탐지(야간/주간 등):

```bash
python tools/build_condition_test_images.py
python tools/benchmark_conditions.py
```

미터 오차 답변용(실측 CSV + 이미지 폴더):

```bash
python tools/validate_depth_meters.py --truth-csv data/depth_truth/truth.csv --image-dir data/depth_truth
```

---

### 가이드 체크리스트 대응

| 항목 | 상태 |
|------|------|
| Precision / Recall / F1 / FPR + 클래스별 FP 요약 | `tools/benchmark.py` (`bench_precision_recall`), 로그에 **FPR 상위 클래스** 포함 |
| 실패 이미지 ~5장 + 패턴 | 벤치 실행 시 `results/failure_cases/` 에 자동 복사 |
| 계단 pseudo-label 고정 bbox | 코드·리스크 설명: `docs/stairs_pseudo_label.md`, `USE_FIXED_STAIRS_BBOX` 환경 변수 |
| Depth 스케일 | `tools/calibrate_depth.py`, `validate_depth_meters.py`, `src/depth/depth.py` 의 `DEPTH_SCALE` |
| 버스 OCR 현실 데이터 | `build_bus_ocr_dataset.py`, `seed_bus_ocr_labels.py`, `eval_bus_ocr.py` → `results/bus_ocr_eval.md` |
| 환경별 강약 숫자 | `build_condition_test_images.py` + `benchmark_conditions.py` → `results/condition_eval.md` |

---

### “잘 되는 환경 / 약한 환경” (발표용 프레임)

다음은 **동일 파이프라인**에서 일반적으로 나타나기 쉬운 구분입니다. 팀 테스트셋으로 숫자를 바꿔 적으면 완료 기준에 맞습니다.

| 구분 | 잘 되기 쉬운 조건 | 약해지기 쉬운 조건 |
|------|-------------------|---------------------|
| 탐지 | 밝은 실내·야외, 물체가 화면에서 충분히 큼 | 극단적 소물체, 강한 역광, 심한 모션 블러 |
| 방향 | `detect.py` 9구역 규칙과 맞는 중심 배치 | 경계선 근처(cx), 가려진 bbox |
| 거리(Depth) | 모델 로드됨 + 보정 후 | 모델 없음(bbox fallback), 미보정 미터 표현 |
| OCR | 선명한 전면 번호판, 정면 각도 | 야간, 반사, 저해상도, 기울어진 측면 |

계단 전용 수치(mAP 등)는 **고정 pseudo-bbox 학습 한계**가 있으면 과장하지 않습니다. 상세는 `docs/stairs_pseudo_label.md`.

---

### 스냅샷: 최신 결과 (2026-04-30 17:34, 버스/계단 제외)

- **응답 시간(평균)**: 540.9ms (목표 3초 이내 → 통과)
- **방향 판단 정확도**: 100.0% (9/9)
- **문장 생성 테스트**: 100% (27/27)
- **PRF/FPR(평균)**: Recall 95.0% / Precision 95.0% / F1 95.0% / FPR 5.0%

클래스별(테스트셋 기반):

- 사람: R 90.0% / P 90.0% / F1 90.0% / FPR 10.0%
- 의자: R 100.0% / P 100.0% / F1 100.0% / FPR 0.0%

---

### 해석 (발표에서 말할 수 있는 수준)

- 테스트 이미지 기준으로 **사람/의자**는 누락이 거의 없고(Recall 높음), 오탐은 제한적(FPR 낮음)입니다.
- Depth는 모델 파일이 없으면 **bbox 기반 fallback**으로 동작합니다. “정확한 미터”보다 **구간(매우 가까이~멀리)** 표현이 안전합니다.
- 최신 벤치 실행 후 `eval_log.md` 하단의 **FPR 상위 클래스·실패 샘플 폴더**를 함께 캡처하면 제출·발표 자료로 충분합니다.
