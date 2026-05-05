## Phase 4 — Vision/ML 검증 결과 요약

### 범위

- **포함**: 탐지(Detection) + 방향 판단 + 문장 생성 안정성 + (가능 시) Depth 동작 여부

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

조건별 탐지(야간/주간 등):

```bash
python tools/build_condition_test_images.py
python tools/benchmark_conditions.py
```

미터 오차(실측 CSV + 이미지 폴더):

```bash
python tools/validate_depth_meters.py --truth-csv data/depth_truth/truth.csv --image-dir data/depth_truth
```

---

### 도구 체크리스트

| 항목 | 상태 |
|------|------|
| Precision / Recall / F1 / FPR + FPR 상위 클래스 | `tools/benchmark.py` |
| 실패 이미지 샘플 | `results/failure_cases/` |
| Depth 스케일 | `tools/calibrate_depth.py`, `validate_depth_meters.py`, `src/depth/depth.py` 의 `DEPTH_SCALE` |
| 환경별 강약 숫자 | `build_condition_test_images.py` + `benchmark_conditions.py` → `results/condition_eval.md` |

---

### “잘 되는 환경 / 약한 환경” (발표용 프레임)

| 구분 | 잘 되기 쉬운 조건 | 약해지기 쉬운 조건 |
|------|-------------------|---------------------|
| 탐지 | 밝은 실내·야외, 물체가 화면에서 충분히 큼 | 극단적 소물체, 강한 역광, 심한 모션 블러 |
| 방향 | `detect.py` 9구역 규칙과 맞는 중심 배치 | 경계선 근처(cx), 가려진 bbox |
| 거리(Depth) | 모델 로드됨 + 보정 후 | 모델 없음(bbox fallback), 미보정 미터 표현 |

---

### 스냅샷: 참고 결과 (2026-04-30)

- **응답 시간(평균)**: 540.9ms (목표 3초 이내 → 통과)
- **방향 판단 정확도**: 100.0% (9/9)
- **문장 생성 테스트**: 100% (27/27)
- **PRF/FPR(평균)**: Recall 95.0% / Precision 95.0% / F1 95.0% / FPR 5.0%

클래스별(테스트셋 기준 예시):

- 사람: R 90.0% / P 90.0% / F1 90.0% / FPR 10.0%
- 의자: R 100.0% / P 100.0% / F1 100.0% / FPR 0.0%

---

### 해석 (발표에서 말할 수 있는 수준)

- 테스트 이미지 기준으로 **사람/의자**는 누락이 거의 없고(Recall 높음), 오탐은 제한적(FPR 낮음)입니다.
- Depth는 모델 파일이 없으면 **bbox 기반 fallback**으로 동작합니다. “정확한 미터”보다 **구간(매우 가까이~멀리)** 표현이 안전합니다.
- 최신 벤치 실행 후 `eval_log.md` 하단의 **FPR 상위 클래스·실패 샘플 폴더**를 함께 캡처하면 제출·발표 자료로 활용할 수 있습니다.
