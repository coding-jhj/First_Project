# PPT 슬라이드 삽입용 코드 & 차트 내용

> 실제 프로젝트 코드에서 직접 발췌한 내용입니다.
> 각 항목 하단에 PPT 배치 방법을 안내합니다.

---

## 슬라이드 10 — Android 파이프라인

### 코드 스니펫 (MvpPipeline.kt)

PPT에 코드 블록으로 넣을 수 있는 핵심 파이프라인 함수입니다.

```kotlin
// MvpPipeline.kt — 파이프라인 핵심 흐름
fun update(detections: List<Detection>): MvpFrame {

    // STEP 1: 기존 트랙 missed 카운트 증가
    tracks.forEach { it.missed += 1 }

    // STEP 2: IoU 기반 객체 매칭 (임계값 0.25)
    for (di in detections.indices) {
        for (ti in tracks.indices) {
            val score = iou(detections[di], tracks[ti])
            if (score >= IOU_MATCH_THRESHOLD)   // 0.25
                scoredPairs.add(Triple(score, di, ti))
        }
    }

    // STEP 3: EMA 평활화 (알파 0.55)
    track.cx = EMA_ALPHA * det.cx + (1f - EMA_ALPHA) * track.cx

    // STEP 4: 위험도 계산 → 진동 패턴 결정
    val maxRisk = output.maxOfOrNull { it.riskScore } ?: 0f
    return MvpFrame(
        detections = output.sortedByDescending { it.riskScore },
        vibrationPattern = patternFor(maxRisk, output.firstOrNull())
    )
}
```

### 파이프라인 노드별 파라미터 표

PPT에서 노드 다이어그램 옆에 배치하는 수치 표입니다.

| 노드 | 역할 | 핵심 파라미터 |
|---|---|---|
| CameraX | 실시간 프레임 입력 | — |
| TFLite YOLO | bbox / class / confidence 산출 | `yolo11n_320.tflite` |
| Vote + Dedup | 순간 오탐·중복 bbox 제거 | NMS IoU ≥ 0.45 |
| IoU Tracking | 연속 프레임 객체 연결 | 매칭 임계값 0.25 |
| EMA Smoothing | 위치·위험도 흔들림 완화 | α = 0.55 |
| Feedback | TTS·진동·UI·JSON 업로드 | MAX_MISSED = 12프레임 |

### PPT 배치 방법

- 왼쪽 70%: 6개 노드를 세로 흐름(화살표 연결)로 배치
- 오른쪽 30%: 위 파라미터 표 삽입
- 코드 블록은 발표자 노트 또는 부록 슬라이드에 넣거나, 슬라이드 하단에 작은 폰트로 배치

---

## 슬라이드 11 — 핵심 매칭 알고리즘

### 입력 → 출력 매핑 표

```
입력                        출력
─────────────────────────────────────────────────────
class_ko  direction  dist_m  risk   →  TTS 문장
─────────────────────────────────────────────────────
의자       12시 (정면)  1.5m    0.72  →  "정면 약 1.5m에 의자가 있어요."
자동차     12시 (정면)  2.0m    0.95  →  "위험! 정면 자동차. 조심! 멈추세요!"
고양이     10시 (왼쪽)  3.0m    0.55  →  "조심하세요. 왼쪽 약 3m에 고양이가 있어요."
의자+사람  각 방향      복수    복수  →  "오른쪽 약 1m에 의자가 있어요. 정면에 사람도 있어요."
```

### 실제 코드 스니펫 (SentenceBuilder.kt)

```kotlin
// SentenceBuilder.kt — 객체 클래스별 TTS 문장 분기
val base = when {
    det.classKo in VoicePolicy.vehicleKo() ->
        "위험! ${dir} ${det.classKo}. 조심! 멈추세요!"

    det.classKo in VoicePolicy.animalKo() ->
        "조심하세요. ${locStr}에 ${det.classKo}${ig} 있어요."

    det.classKo in VoicePolicy.everydayKo() ->
        "${locStr}에 ${det.classKo}${ig} 있어요."

    isCaution ->
        "${locStr}에 ${det.classKo}${ig} 있어요. $action."

    else ->
        "${locStr}에 ${det.classKo}${ig} 있어요."
}
```

### 객체 카테고리 분류 표

PPT에서 "입력값 카드" 영역에 넣을 수 있는 표입니다.

| 카테고리 | 예시 객체 | classWeight | 안내 형식 |
|---|---|---|---|
| vehicleKo (차량) | 자동차, 오토바이, 자전거 | 1.0 | "위험! 정면 자동차. 조심! 멈추세요!" |
| criticalKo (위험) | 계단, 에스컬레이터 | 0.9 | 위치 + 클래스 + 주의 |
| animalKo (동물) | 개, 고양이 | 0.85 | 조심 + 위치 + 클래스 |
| cautionKo (주의) | 자전거, 킥보드 | 0.65 | 위치 + 클래스 + 행동 |
| everydayKo (일반) | 의자, 문, 책상 | 0.45 | 위치 + 클래스 |

### PPT 배치 방법

- 좌측: "입력" 카드 (class / direction / distance / risk)
- 가운데: "Matching Engine" 박스 (화살표)
- 우측: "출력" 카드 (TTS 문장 / 진동 / UI / 서버 기록)
- 코드 스니펫은 슬라이드 하단 작은 박스 또는 발표자 노트

---

## 슬라이드 13 — 위험도 계산과 진동 패턴

### 수식 (실제 코드 그대로)

```
risk = (centerWeight × distanceWeight × classWeight) + sizeBoost
```

```kotlin
// MvpPipeline.kt computeRisk() — 위험도 계산
val centerWeight   = 1f - min(0.6f, abs(det.cx - 0.5f) * 1.2f)
val distanceWeight = when {
    distanceM <= 0.8f -> 1.00f   // 0.8m 이하: 최고 위험
    distanceM <= 1.5f -> 0.85f
    distanceM <= 2.5f -> 0.65f
    distanceM <= 4.0f -> 0.35f
    else              -> 0.15f   // 4m 초과: 낮음
}
val classWeight = when {
    det.classKo in vehicleKo()  -> 1.00f   // 차량
    det.classKo in criticalKo() -> 0.90f   // 위험물
    det.classKo in animalKo()   -> 0.85f   // 동물
    det.classKo in cautionKo()  -> 0.65f   // 주의
    else                        -> 0.45f   // 일반
}
val sizeBoost = min(0.25f, area * 1.8f)
```

### 거리별 위험도 변화 차트 데이터

PPT 막대 차트 또는 선 그래프로 사용할 수 있는 데이터입니다.

| 거리 | distanceWeight | 차량(×1.0) | 일반물체(×0.45) |
|---|---|---|---|
| 0.8m 이하 | 1.00 | 1.00 | 0.45 |
| ~1.5m | 0.85 | 0.85 | 0.38 |
| ~2.5m | 0.65 | 0.65 | 0.29 |
| ~4.0m | 0.35 | 0.35 | 0.16 |
| 4m 초과 | 0.15 | 0.15 | 0.07 |

> ※ centerWeight=1.0(정면), sizeBoost 제외 기준

### 진동 패턴 임계값 표

| 패턴 | Risk 범위 | 진동 설명 | 특이사항 |
|---|---|---|---|
| NONE | < 0.35 | 없음 | — |
| SHORT | 0.35 ~ 0.54 | 짧게 1회 | — |
| DOUBLE | 0.55 ~ 0.74 | 짧게 2회 | — |
| URGENT | ≥ 0.75 | 긴급 진동 | 차량이면 risk ≥ 0.55부터 URGENT |

### 3단계 위험도 게이지 — PPT용 색상 제안

```
[  SAFE  ][  CAUTION  ][  URGENT  ]
 < 0.35     0.35~0.74    ≥ 0.75
  초록        노랑         빨강
  NONE       SHORT/DOUBLE  URGENT
```

### PPT 배치 방법

- 상단: 수식 박스 (큰 폰트, 밝은 배경)
- 중간: 거리별 위험도 변화 선 그래프 (가로축: 거리, 세로축: risk)
- 하단: 진동 패턴 임계값 표 또는 3단계 게이지

---

## 슬라이드 15 — 수행 경과 / 검증

### 확보된 수치 (실제 측정값)

| 항목 | 수치 | 비고 |
|---|---|---|
| 자동 테스트 | **23 passed**, 9 deselected | `pytest tests/ -m "not integration"` |
| 서버 요청 처리 | 평균 **26.37ms** | FastAPI `/detect` 엔드포인트 |
| NLG 문장 생성 | 평균 **0.015ms** | `build_sentence()` 실행 시간 |

### 테스트 항목별 분류 표

| 테스트 파일 | 테스트 내용 | 통과 |
|---|---|---|
| `test_api.py` | `/api/policy`, `/detect` 응답 스키마, API key 보호 | ✓ |
| `test_sentence.py` | 한국어 NLG 조사, 방향별 문장, 최대 2개 안내 | ✓ |
| `test_server.py` | 서버 런타임 import, `/spaces/snapshot` | ✓ |
| `test_simulation.py` | 탐지 시뮬레이션, `recent_detections` 회귀 | ✓ |

### 서버 성능 차트 데이터

PPT 막대 차트로 사용할 수 있는 데이터입니다.

| 처리 단계 | 소요 시간 |
|---|---|
| NLG 문장 생성 | 0.015ms |
| DB 저장 (SQLite) | ~2ms |
| 전체 `/detect` 처리 | 26.37ms |

> ※ 클라이언트(Android) 모델 추론은 별도 측정 필요

### 추가 측정 필요 항목 (미확보 수치)

| 항목 | 이유 |
|---|---|
| Android 실기 FPS | 실제 기기·조명 환경에 따라 달라짐 |
| 모델별 mAP50 | 정량 비교 데이터 없음 |
| TTS-UI latency | 사용자 체감 지연 미측정 |
| 저조도 성능 | 실제 보행 환경 검증 필요 |

### PPT 배치 방법

- 상단: "확보된 수치" 3개를 큰 숫자로 강조 (23 / 26.37ms / 0.015ms)
- 중간: 테스트 항목별 분류 표 (파일명 + 내용 + 통과 체크)
- 하단: "추가 측정 필요" 항목을 점선 박스로 구분

---

## 공통 — 시스템 아키텍처 흐름 (9장 참고)

PPT 9장 아키텍처 다이어그램 설명용 텍스트입니다.

```
[ Android ]                          [ Server ]

CameraX ──▶ TFLite YOLO              POST /detect ──▶ FastAPI
              │                       POST /gps   ──▶ SQLite
              ▼                                          │
         Vote + Dedup                                    ▼
              │                                     SSE 이벤트
              ▼                                          │
         IoU Tracking                                    ▼
              │                                    Dashboard
              ▼                                  (Leaflet 지도)
         EMA Smoothing
              │
              ▼
         Risk 판단
        /          \
  TTS·진동          JSON 업로드 ──────────────────▶ [ Server ]
```

> 핵심: 서버는 영상을 받지 않고 Android가 만든 JSON만 받습니다.
