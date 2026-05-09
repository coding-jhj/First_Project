# VoiceGuide 시스템 분석

> 작성일: 2026-05-08  
> 기준: 실제 코드(Android Kotlin + Python FastAPI) 직접 확인

---

## 목차

1. [시스템 전체 구조](#1-시스템-전체-구조)
2. [카메라 프레임 처리 흐름](#2-카메라-프레임-처리-흐름)
3. [Android 핵심 컴포넌트](#3-android-핵심-컴포넌트)
4. [서버 핵심 컴포넌트](#4-서버-핵심-컴포넌트)
5. [핵심 알고리즘](#5-핵심-알고리즘)
6. [Android ↔ 서버 데이터](#6-android--서버-데이터)
7. [음성 명령 모드](#7-음성-명령-모드)
8. [설계 결정 이유](#8-설계-결정-이유)

---

## 1. 시스템 전체 구조

VoiceGuide는 시각장애인 보행 보조 앱입니다.  
카메라로 앞의 장애물을 인식하고 **"오른쪽 1.5미터에 의자가 있어요. 오른쪽으로 피하세요."** 처럼 음성으로 안내합니다.

### 왜 스마트폰과 서버로 나뉘어 있나

| 목표 | 해결 방법 |
|------|----------|
| **빠르게** — 장애물 경고는 1초 이내 | 스마트폰에서 AI 추론 직접 실행 |
| **자연스럽게** — 단순 "의자 있음"이 아닌 한국어 문장 | 서버에서 NLG 문장 생성 |

```
[Android]
  카메라 → YOLO 추론 → 로컬 문장 생성 → TTS 즉시 발화
  (서버 없이도 동작)
         ↓ 백그라운드 전송
[서버 (GCP Cloud Run)]
  탐지 결과 JSON 수신 → DB 저장 → 대시보드 표시
```

**TTS 음성은 Android 로컬에서 생성합니다. 서버 응답을 기다리지 않습니다.**  
서버가 꺼져있어도 진동 + 로컬 TTS는 계속 동작합니다.

### 정책 파일 (policy.json)

"차량이 몇 미터 이내면 위험", "사람은 몇 % 크기 이상이면 가까운 것" 같은 기준값을  
`src/config/policy.json` 하나에서 관리합니다.

앱 시작 시 서버에서 이 파일을 받아 저장해두고, 이후에는 저장된 값을 사용합니다.  
→ 기준값을 바꾸고 싶으면 앱 재배포 없이 서버 파일만 수정하면 됩니다.

---

## 2. 카메라 프레임 처리 흐름

```
CameraX (스트리밍)
  └─ 1초 이상 간격으로만 처리 (배터리 절약)
      └─ [1] TfliteYoloDetector.detect()
              └─ YUV 이미지 → letterbox → TFLite 추론
                  └─ Detection 목록 (classKo, cx, cy, w, h, confidence)

          [2] removeDuplicates()
              └─ 같은 클래스 bbox가 IoU 30% 이상 겹치면 하나만 남김
                  (YOLO가 같은 물체를 두 개로 잡는 현상 제거)

          [3] voteOnly()
              └─ 최근 3프레임 중 2번 이상 등장한 물체만 통과
                  (1~2프레임짜리 오탐 제거)

          [4] MvpPipeline.update()
              └─ 이전 프레임과 IoU 매칭 → track_id 부여
              └─ EMA로 위치·거리 안정화
              └─ riskScore 계산 → 진동 패턴 결정 → 즉시 진동

          [5] SentenceBuilder.build()
              └─ 위험도 높은 것 최대 2개 골라 한국어 문장 생성
              └─ handleSuccess(sentence) → TTS 즉시 발화

          [6] (백그라운드) POST /detect → 서버 DB 저장 + tracker 업데이트
          [7] (fire-and-forget) POST /detect_json → 서버 tracker/recent_detections 업데이트
```

**핵심**: 5번에서 TTS가 나갑니다. 6·7번은 백그라운드라 사용자는 기다리지 않습니다.

---

## 3. Android 핵심 컴포넌트

### TfliteYoloDetector.kt — 추론 엔진

카메라 프레임을 받아 YOLO 모델을 실행하고 Detection 목록을 반환합니다.

**letterboxing (이미지 전처리)**  
카메라는 직사각형 이미지를 주지만, YOLO는 정사각형(320×320) 입력을 요구합니다.  
이미지 비율을 유지하면서 빈 공간을 검정으로 채워 정사각형으로 만듭니다.

```
원본 (640×480) → 비율 유지 리사이즈 (320×240) → 검정 패딩 추가 → 320×320
```

**왜 Bitmap 변환 없이 직접 처리하나**  
Android 카메라는 YUV_420_888 포맷으로 프레임을 줍니다.  
Bitmap으로 변환하면 중간 객체 생성 + GC 부담이 생겨 느려집니다.  
ByteBuffer에 직접 RGB 변환값을 채워 넣어서 메모리 할당을 줄입니다.

**SamplingPlan 캐시**  
같은 화면 해상도/회전이면 좌표 매핑 테이블을 매 프레임 재계산하지 않고 재사용합니다.

**두 가지 모델 출력 형식**  
- `yolo11n_320.tflite`: 출력 shape `[1, 84, N]` → cx/cy/w/h + 80개 클래스 점수
- `yolo26n_float32.tflite`: 출력 shape `[1, N, 6]` → x1/y1/x2/y2/score/classId

`outputRows == 84`면 raw 포맷, 아니면 end-to-end NMS 포맷으로 자동 판별합니다.

---

### MvpPipeline.kt — 온디바이스 트래커

연속 프레임에서 같은 물체를 연결해 track_id를 부여하고, EMA로 위치·거리를 안정화합니다.

**IoU 매칭 (ByteTrack-lite)**

```kotlin
// 같은 클래스끼리만 매칭 (의자↔의자, 사람↔사람)
// IoU > 0.25인 쌍을 후보로 수집
// IoU 높은 순서로 탐욕적 할당
for ((_, di, ti) in scoredPairs.sortedByDescending { it.first }) {
    if (di in assignedDetectionIds) continue
    if (track.id in assignedTrackIds) continue
    // 매칭 확정
}
```

왜 0.25인가: 너무 낮으면 다른 물체끼리 연결, 너무 높으면 물체가 조금만 움직여도 새 track_id가 생깁니다.

**riskScore 계산**

```kotlin
val centerWeight  = 1f - min(0.6f, abs(det.cx - 0.5f) * 1.2f)  // 화면 중앙일수록 위험
val distanceWeight = when { distanceM <= 0.8f -> 1.0f; distanceM <= 1.5f -> 0.85f; ... }
val classWeight   = when { vehicleKo -> 1.0f; criticalKo -> 0.9f; ... }
val sizeBoost     = min(0.25f, area * 1.8f)
riskScore = (centerWeight * distanceWeight * classWeight + sizeBoost).coerceIn(0f, 1f)
```

riskScore에 따라 진동 패턴이 결정됩니다: `NONE / SHORT / DOUBLE / URGENT`

---

### VoicePolicy.kt — 정책 관리자

`policy.json`을 파싱해서 분류 기준과 임계값을 앱 전체에 제공합니다.

**초기화 순서**

```kotlin
fun init(appContext: Context) {
    synchronized(this) {
        val cached = prefs.getString(PREF_POLICY_JSON, null)
        val json = if (!cached.isNullOrBlank()) cached  // 서버에서 받아둔 것 우선
                   else assets.open("policy_default.json")...  // 없으면 번들 기본값
        snap = parsePolicy(json)
    }
}
```

**거리 추정**

```kotlin
fun calcDistBboxM(classKo: String, w: Float, h: Float): Double {
    val area  = w * h
    val calib = bboxCalibAreaByClass[classKo] ?: bboxCalibArea  // 클래스별 다른 기준값
    return sqrt(calib / area)
    // 원리: 물체가 클수록 가깝고 작을수록 멀다
    // calib = 1미터 거리에서 이 물체가 차지하는 기준 bbox 면적
}
```

사람(calib ≈ 0.08)과 버스(calib ≈ 0.35)는 같은 bbox 크기라도 실제 거리가 다릅니다.

---

### SentenceBuilder.kt — 온디바이스 NLG

Detection 목록을 받아 한국어 TTS 문장을 만듭니다.

**방향 안정화 (getStableClock)**

```kotlin
private fun getStableClock(classKo: String, cx: Float, index: Int): String {
    val uniqueKey = "${classKo}_$index"
    val prev = stableClock[uniqueKey]
    if (prev == null || clockDistance(prev, newClock) >= 2) {
        stableClock[uniqueKey] = newClock  // 2칸 이상 이동해야 방향 변경
    }
    return stableClock[uniqueKey]!!
}
```

EMA 후에도 cx가 약간 흔들립니다. "11시→12시→11시"처럼 방향이 왔다갔다하면  
TTS가 "왼쪽 오른쪽 왼쪽"을 반복합니다. 시계 2칸 이상 이동할 때만 방향이 바뀐 것으로 처리합니다.

**한국어 조사 처리**

```kotlin
fun josaIGa(word: String): String {
    val last = word.last()
    return if ((last.code - 0xAC00) % 28 != 0) "이" else "가"
    // 한글 유니코드: (코드 - 0xAC00) % 28 == 0이면 받침 없음
    // 의자(자=받침없음) → "의자가", 책(받침있음) → "책이"
}
```

---

### MainActivity.kt — 전체 조율

**동시 실행 제어**

```kotlin
private val inFlightCount = AtomicInteger(0)
private val MAX_ON_DEVICE_IN_FLIGHT = 1

// 이미 처리 중이면 새 프레임 skip
if (inFlightCount.get() >= MAX_ON_DEVICE_IN_FLIGHT) return
```

TfliteYoloDetector가 `@Synchronized`라 동시 추론이 불가능하고,  
이전 결과가 처리되기 전에 새 프레임이 들어오면 혼선이 생깁니다.

**TTS 잠금**

```kotlin
private val ttsBusy = AtomicBoolean(false)

if (!ttsBusy.compareAndSet(false, true)) return  // 말하는 중이면 skip
// TTS onDone 콜백에서
ttsBusy.set(false)
```

`compareAndSet`은 원자적 연산이라 check-then-act 사이 경쟁 조건이 없습니다.

---

## 4. 서버 핵심 컴포넌트

### 세션 관리 (routes.py)

```python
def _normalize_session_id(wifi_ssid: str = "", device_id: str = "") -> str:
    preferred = device_id or wifi_ssid  # device_id 우선
    if not value or value.lower() in {"<unknown ssid>", "unknown ssid", "0x"}:
        return f"anonymous_{uuid.uuid4().hex[:8]}"  # WiFi 없는 기기마다 고유 ID
    return value
```

WiFi 없는 여러 기기가 모두 `"anonymous"`를 쓰면 대시보드에서 섞입니다.  
UUID를 붙여 기기마다 격리합니다.

---

### SessionTracker (tracker.py) — 서버 EMA

Android EMA와 서버 EMA의 역할이 다릅니다.

| | Android MvpPipeline | 서버 SessionTracker |
|-|---------------------|---------------------|
| 무엇을 안정화? | cx/cy/w/h 좌표 | distanceM 거리 |
| 목적 | 방향 흔들림 방지 | 접근 감지 ("가까워지고 있어요") |
| 지속 시간 | 앱 세션 동안만 | 서버 재시작 전까지 |

**물체 키 설계**

```python
def _object_key(obj: dict) -> str:
    tid = obj.get("track_id")
    if tid not in (None, "", 0, "0"):
        return f"track:{tid}"   # Android ByteTrack이 준 ID 사용
    return f"class:{cls}"       # track_id 없으면 클래스명으로 대체
```

---

### sentence.py — 서버 NLG

서버 NLG는 **대시보드 표시**에 사용됩니다. Android TTS에는 사용되지 않습니다.

Android와 서버 NLG의 차이:

| | Android SentenceBuilder | 서버 sentence.py |
|-|------------------------|-----------------|
| 언어 | Kotlin | Python |
| TTS 사용 | ✅ (로컬에서 즉시) | ❌ (대시보드 표시용) |
| 호출 시점 | YOLO 추론 직후 | HTTP 응답 생성 시 |

**경고 단계 분류**

```python
def get_alert_mode(obj: dict) -> str:
    if is_vehicle and dist_m < v_m: return "critical"  # 즉각 경고
    if dist_m < g_m:               return "critical"
    if dist_m < b_m:               return "beep"        # 비프음만
    return "silent"                                      # 무음
```

silent인 물체는 "지금 뭐 있어?" 질문에는 포함해서 대답합니다.

---

### db.py — 저장 구조

```
detection_events    ← /detect로 저장되는 탐지 이벤트 이력 (세션당 최근 200개)
recent_detections   ← /detect_json으로 저장되는 최근 상태 (질문 응답 복원용, 500개)
snapshots           ← 공간 스냅샷 (이전 프레임과 비교해 "의자가 생겼어요" 감지)
gps_history         ← GPS 이동 경로 (대시보드 지도)
gps_routes          ← 저장된 완성 경로
```

**백그라운드 Writer**

```python
def enqueue_detection_event(**kwargs):
    _event_queue.put_nowait(kwargs)  # 큐에 넣고 즉시 반환

def _event_writer_loop():
    # 별도 daemon 스레드에서 최대 24개씩 배치 저장
```

DB 쓰기가 느려도 `/detect` 응답 속도에 영향이 없습니다.

---

### events.py — 대시보드 실시간 업데이트 (SSE)

```python
_subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)

async def publish(session_id: str, event: dict) -> None:
    for queue in list(_subscribers.get(session_id, ())):
        if queue.full():
            queue.get_nowait()  # 꽉 찼으면 가장 오래된 메시지 버림
        queue.put_nowait(payload)
```

- Queue 크기 16: 브라우저가 잠깐 느려져도 최대 16개까지 버퍼링
- `list(...)` 복사본으로 순회: 순회 중 구독자 추가/제거 시 RuntimeError 방지
- 15초마다 keepalive 신호: 프록시(Cloud Run 등)가 연결을 자동으로 끊는 것 방지

---

## 5. 핵심 알고리즘

### EMA (지수이동평균)

YOLO는 매 프레임마다 같은 물체의 위치·거리를 조금씩 다르게 측정합니다.  
그대로 쓰면 "1.0m → 1.3m → 0.9m"처럼 흔들려서 TTS가 매번 다른 말을 합니다.

```
smooth = α × 현재값 + (1-α) × 이전값   (α = 0.55)

예: 1.0 → 1.17 → 1.02 → 1.07  ← 훨씬 안정적
```

α = 0.55: 현재 55% + 이전 45%. 0.5 미만이면 반응이 너무 느리고, 0.7 이상이면 흔들림이 많습니다.

### bbox 기반 거리 추정

```
dist = √(calib / area)

예: 사람(calib=0.08)이 화면의 2%를 차지하면
    dist = √(0.08 / 0.02) = 2.0m
```

카메라로 정확한 거리 측정은 불가능하므로, "물체가 클수록 가깝다"는 원리를 이용합니다.  
클래스마다 calib 값이 다릅니다 (사람과 버스는 실제 크기가 다르기 때문).

### IoU (Intersection over Union)

두 bbox가 얼마나 겹치는지 0~1로 나타냅니다.

```
IoU = 교집합 넓이 / 합집합 넓이

0.0 = 전혀 겹치지 않음
1.0 = 완전히 같은 위치
```

VoiceGuide에서 두 가지로 사용:
- `IoU > 0.25` → 이전 track과 같은 물체로 연결 (MvpPipeline)
- `IoU > 0.3` → 중복 bbox로 판단해 confidence 낮은 것 제거 (removeDuplicates)

### 한국어 받침 판별

```kotlin
(last.code - 0xAC00) % 28 == 0  → 받침 없음 → "의자가", "사람이" 중 "가"
(last.code - 0xAC00) % 28 != 0  → 받침 있음 → "책이", "컵이" 중 "이"

한글 유니코드: 0xAC00(가)부터 28개씩 받침 조합
  가(0xAC00): % 28 = 0 → 받침 없음
  각(0xAC01): % 28 = 1 → 받침 있음
```

---

## 6. Android ↔ 서버 데이터

### Android → 서버 (POST /detect)

```json
{
  "device_id": "pixel7_abc123",
  "wifi_ssid": "HomeWifi",
  "mode": "장애물",
  "objects": [
    {
      "class_ko": "의자",
      "confidence": 0.91,
      "bbox_norm_xywh": [0.4, 0.45, 0.2, 0.25],
      "direction": "12시",
      "distance_m": 1.5
    }
  ]
}
```

### Android → 서버 (POST /detect_json, fire-and-forget)

```json
{
  "device_id": "pixel7_abc123",
  "detections": [
    {
      "class_ko": "의자",
      "cx": 0.5, "cy": 0.55, "w": 0.2, "h": 0.25,
      "zone": "12시",
      "dist_m": 1.5,
      "track_id": 3,
      "risk_score": 0.72,
      "vibration_pattern": "DOUBLE"
    }
  ]
}
```

`/detect_json`은 `.execute().close()` — 응답을 읽지 않고 닫습니다.  
서버 tracker와 recent_detections 업데이트 용도입니다.

---

## 7. 음성 명령 모드

STT로 인식된 키워드에 따라 모드가 바뀝니다 (`VoiceGuideConstants.kt STT_KEYWORDS`).

| 모드 | 트리거 키워드 예시 | 동작 |
|------|-----------------|------|
| **장애물** | "뭐 있어", "주변 알려줘", "앞에" | 위험도 상위 물체 안내 (기본 모드) |
| **찾기** | "찾아줘", "어디있어", "이건 뭐야" | 특정 물체 위치 안내 |
| **질문** | "지금 뭐가 있어", "현재 상황 알려줘" | 현재 + tracker 누적 상태 포괄 응답 |
| **들고있는것** | "손에 든 게 뭐야", "바로 앞에 뭐 있어" | 바로 가까이 있는 물체 안내 |
| **신호등** | "신호등", "건너도 돼" | 신호등 색 감지 |
| **중지** | "잠깐", "멈춰", "그만해" | 분석 일시정지 |
| **재시작** | "다시 시작", "계속해줘" | 분석 재개 |

모든 모드에서 로컬 `SentenceBuilder`가 문장을 생성합니다.  
찾기 → `buildFind()`, 들고있는것 → `buildHeld()`, 나머지 → `build()`

---

## 8. 설계 결정 이유

| 결정 | 이유 |
|------|------|
| Android에서 AI 직접 실행 | 서버 없이도 진동+TTS 동작. 지연 없음 |
| TTS는 로컬 문장 사용 | 서버 응답 기다리면 1~2초 지연 발생 |
| 서버 NLG는 대시보드용 | 품질 개선 시 앱 재배포 없이 서버만 수정 |
| policy.json SSOT | Android·서버가 같은 기준값 공유. 앱 재배포 없이 수정 가능 |
| EMA가 Android·서버 양쪽 존재 | 역할 다름: Android = 좌표 안정화, 서버 = 접근 감지 |
| 백그라운드 DB Writer | /detect 응답 지연 없이 DB 쓰기 처리 |
| anonymous_UUID | WiFi 없는 기기들이 같은 세션 공유로 대시보드 오염 방지 |
| MAX_ON_DEVICE_IN_FLIGHT = 1 | TFLite @Synchronized + GPU delegate는 동시 추론 불가 |
| SSE keepalive 15초 | Cloud Run 기본 타임아웃 대비 연결 유지 |
