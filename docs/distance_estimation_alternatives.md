# Depth 없이 거리 추정하는 기법 비교

> Depth Anything V2를 제거한 이후 대안 검토. 추가 모델 없이 경량으로 동작하는 방식 위주.

---

## 1. 박스 면적 보정 (현재 사용 중)

```
distance ≈ sqrt(calib_area / bbox_area)
```

- 이미 `bbox_calib_area`로 구현되어 있음 (`policy.json` → `on_device.bbox_calib_area`)
- 추가 연산 없음
- **단점**: 같은 클래스라도 물체 크기가 다양하면 오차 큼

---

## 2. 알려진 실물 크기 기반 삼각법

```
D = (실물_너비_m × 초점거리_px) / bbox_너비_px
```

### 원리

카메라 핀홀 모델에서 물체의 실제 크기(W), 화면에서의 픽셀 크기(w), 초점거리(f)가 있으면 거리(D)를 계산할 수 있음.

### 클래스별 평균 실물 크기 예시

| 클래스 | 기준 치수 | 평균값 |
|---|---|---|
| 사람 | 어깨 너비 | 0.45m |
| 자동차 | 차체 너비 | 1.8m |
| 버스 | 차체 너비 | 2.5m |
| 오토바이 | 차체 너비 | 0.8m |
| 의자 | 좌석 너비 | 0.5m |
| 문 | 문 높이 | 2.0m |

### 초점거리 구하는 법

```kotlin
// 카메라 API에서 직접 읽기
val focalLength = characteristics.get(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS)?.firstOrNull()
// 또는 EXIF에서 읽기 (사진 촬영 후)
val exif = ExifInterface(filePath)
val focalMm = exif.getAttribute(ExifInterface.TAG_FOCAL_LENGTH)
```

픽셀 단위 환산: `f_px = f_mm × image_width_px / sensor_width_mm`

### 구현 예시

```kotlin
fun estimateDistanceMeters(bboxWidthPx: Float, classKo: String, focalLengthPx: Float): Double? {
    val realWidthM = REAL_WIDTH_MAP[classKo] ?: return null
    return (realWidthM * focalLengthPx / bboxWidthPx).toDouble()
}

val REAL_WIDTH_MAP = mapOf(
    "사람" to 0.45f,
    "자동차" to 1.8f,
    "버스" to 2.5f,
    "의자" to 0.5f
)
```

- **추가 모델 없음**, 연산 사실상 0
- FPS 영향 없음
- **단점**: 어린이, 자전거처럼 개체 크기 편차가 큰 클래스는 오차 있음

---

## 3. bbox 하단 Y좌표 기반 (지면 소실점)

```
distance ≈ (camera_height_m × focal_length_px) / (bbox_bottom_y - horizon_y)
```

### 원리

카메라가 고정 높이에 있을 때, 지면에 닿은 물체의 발 위치(bbox 하단 y좌표)는 거리와 반비례함.

```
카메라
  │  ← camera_height (예: 1.2m)
  │
지면 ───────────────────────────────
      가까운 물체    먼 물체
      (bbox 하단 y 높음)  (bbox 하단 y 낮음)
```

- 시각장애인 앱 특성상 카메라 위치(목/가슴)가 어느 정도 일정 → 적합
- **추가 모델 없음**, 연산 거의 없음
- **단점**: 카메라가 위아래로 기울면 오차 큼, 날아다니는 물체(새 등) 부정확

---

## 4. MiDaS Small / Depth Anything V2 Small (경량화 depth, 참고용)

| 모델 | 입력 크기 | 폰 추론 속도 |
|---|---|---|
| MiDaS v2.1 small | 256×256 | ~30ms |
| DepthAnything V2 vits ONNX | 256×256 | ~50ms |

- 현재 사용하던 모델보다 훨씬 가볍지만 **여전히 10ms+ 소비**
- "depth는 제거" 방향이므로 현재 프로젝트에는 비권장

---

## 이 프로젝트에 맞는 선택

미팅 방향("거리는 질문했을 때만 안내")을 기준으로:

| 상황 | 방식 | 이유 |
|---|---|---|
| 실시간 장애물 안내 | 박스 면적 3단계 (현재) | 수치 필요 없음, 가깝다/멀다만 구분 |
| 질문 시 "앞에 뭐가 있어?" | 삼각법 (2번) | 정지 상태 + 클래스 크기 prior로 "약 1.5m 앞에 의자" |

**결론**: 추가 모델 없이 클래스별 실물 크기 테이블 + 카메라 초점거리만 추가하면 됨.
