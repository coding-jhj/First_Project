# VoiceGuide 시스템 전체 분석

> 작성일: 2026-05-08  
> 분석 관점: 로직 이해 / 설계 이해 / 데이터 흐름 이해

---

## 목차

1. [시스템 설계 철학](#1-시스템-설계-철학)
2. [전체 데이터 흐름](#2-전체-데이터-흐름)
3. [Android 레이어 분석](#3-android-레이어-분석)
4. [서버 레이어 분석](#4-서버-레이어-분석)
5. [핵심 알고리즘 이해](#5-핵심-알고리즘-이해)
6. [Android ↔ 서버 인터페이스](#6-android--서버-인터페이스)
7. [설계 결정 이유 정리](#7-설계-결정-이유-정리)

---

## 1. 시스템 설계 철학

### 왜 "온디바이스 추론 + 서버 NLG" 구조인가

VoiceGuide는 두 가지 상충하는 목표를 동시에 만족해야 한다.

- **실시간성**: 시각장애인이 장애물을 피하려면 음성 안내가 1초 이내에 나와야 한다.
- **지능적 안내**: 단순히 "의자 있음"이 아니라 "오른쪽 1.5미터에 의자가 있어요. 오른쪽으로 피하세요." 수준의 자연스러운 한국어 문장이 필요하다.

이 두 목표 때문에 역할이 분리됐다.

```
[Android — 속도 우선]
  YOLO 추론 → 즉시 로컬 TTS 가능 (서버 없이도 동작)
  MvpPipeline → 온디바이스 트래킹/위험도 계산

[서버 — 품질 우선]
  NLG 문장 품질 개선, 정책 업데이트 용이
  대시보드, 다중 기기 세션 관리, GPS 이력
  서버 연결 안 되면 → Android가 자체 SentenceBuilder로 fallback
```

### SSOT (Single Source of Truth) 원칙

탐지 분류 기준(vehicle, animal, critical 등), 거리 임계값, 경고 문턱값은 `policy.json` 하나에서 관리한다. Android는 앱 시작 시 서버에서 이 파일을 받아 `SharedPreferences`에 캐시하고, 서버도 같은 파일을 읽는다.

```
서버 src/config/policy.json
  ↑ (GET /api/policy, ETag 캐싱)
Android VoicePolicy.init() → SharedPreferences 캐시
  → 이후 VoicePolicy.calcDistBboxM(), requireSnap() 등이 이 값 사용
```

**왜 ETag를 쓰는가**: policy.json은 자주 바뀌지 않는다. 매 요청마다 전체 JSON을 내려받으면 네트워크 낭비다. ETag(MD5 해시)로 변경 여부를 먼저 확인하고 같으면 304 반환 → 트래픽 절약.

---

## 2. 전체 데이터 흐름

### 2.1 일반 탐지 흐름 (장애물 모드)

```
[1] CameraX ImageAnalysis
    └─ analyzeStreamFrame() → cameraExecutor 스레드
    └─ 1초 이상 간격 강제 (lastStreamFrameTime 비교)

[2] TfliteYoloDetector.detect(imageProxy)
    └─ YUV → letterbox → NHWC Float32 변환
    └─ TFLite 추론 (GPU or XNNPACK)
    └─ 후처리: NMS → Detection(classKo, cx, cy, w, h, confidence) 목록

[3] removeDuplicates()
    └─ 같은 클래스에서 IoU > 0.3 겹치면 confidence 낮은 것 제거
    └─ 이유: YOLO가 동일 물체를 인접 위치에서 2개로 탐지하는 현상 방지

[4] voteOnly()
    └─ 최근 3프레임 detectionHistory에 추가
    └─ VOTE_MIN_COUNT(2)회 이상 등장한 물체만 통과
    └─ 이유: 1~2프레임 오탐(인형, 노트북 등) 필터링

[5] MvpPipeline.update()
    └─ IoU 매칭으로 이전 track과 연결 → track_id 부여
    └─ EMA로 cx/cy/w/h/distanceM 평활화
    └─ computeRisk() → riskScore 계산
    └─ patternFor() → NONE/SHORT/DOUBLE/URGENT 진동 패턴

[6] classify()
    └─ bbox 면적 > BEEP_AREA_THRESH(8%) → voice 목록
    └─ 나머지 → beep only
    └─ 이유: 멀리 있는 물체는 음성 대신 비프음만 → 경고 피로 방지

[7] Android SentenceBuilder.build()
    └─ 온디바이스 문장 생성 (서버 없이 즉시 TTS 가능)
    └─ risk 기준 정렬 → 최대 2개 물체만 안내

[8] (서버 URL 있으면) sendDetectionJsonToServer()
    └─ POST /detect_json
    └─ 서버 응답의 sentence로 TTS 안내 업그레이드

[9] TTS.speak() + 진동
    └─ ttsBusy AtomicBoolean으로 동시 재생 방지
    └─ alert_mode에 따라 critical/beep/silent 처리
```

### 2.2 질문 응답 흐름 ("지금 뭐 있어?")

```
[1] STT가 "지금 뭐 있어" 인식
    └─ handleVoiceCommand() → mode = "질문"

[2] POST /question 또는 POST /detect_json (mode="질문")
    └─ 서버: tracker.get_current_state(max_age_s=3.0)
       └─ 최근 3초 동안 detect_json으로 쌓인 EMA 추적 결과 반환
       └─ tracker가 비어 있으면: db.get_recent_detections() 로 DB에서 복원

[3] build_question_sentence()
    └─ 현재 프레임 탐지 + tracker 누적 상태 + scene 정보 합산
    └─ "최근에 오른쪽 2미터에서 의자가 보였어요." 같은 포괄적 응답
```

### 2.3 찾기 모드 ("의자 찾아줘")

```
[1] STT → extractFindTarget("의자 찾아줘") → "의자"

[2] POST /detect_json (mode="찾기", query_text="의자")

[3] build_find_sentence("의자", objects)
    └─ objects에서 "의자" contains 검색 (부분 일치)
    └─ 있으면: "의자는 정면 1.5미터에 있어요."
    └─ 없으면: "의자가 없어요. 다른 곳을 보여주세요."
    └─ 찾은 물체보다 큰 위험 물체 있으면: "단, 오른쪽 코앞에 책상이 있으니 주의하세요." 추가
```

### 2.4 대시보드 실시간 업데이트 흐름

```
[대시보드 브라우저]
  └─ GET /events/{session_id} → SSE 연결 유지

[서버 /detect_json 처리 완료 시]
  └─ events.publish(session_id, {...})
    └─ _subscribers[session_id]의 asyncio.Queue에 push
    └─ SSE 스트림으로 브라우저에 전달
    └─ 브라우저: 실시간 탐지 물체, GPS, 문장 갱신

[타임아웃]
  └─ 15초마다 ": keepalive\n\n" → 연결 유지 (프록시 끊김 방지)
```

---

## 3. Android 레이어 분석

### 3.1 TfliteYoloDetector — 추론 엔진

**역할**: 카메라 프레임을 받아 YOLO 모델을 실행하고 Detection 목록을 반환한다.

**입력 전처리 (letterboxing)**

```kotlin
// 원본 이미지를 320x320에 맞추되 비율 유지 + 빈 공간은 검정으로 채움
val scale = minOf(inputSize.toFloat() / origW, inputSize.toFloat() / origH)
val scaledW = (origW * scale + 0.5f).toInt()
val padX = (inputSize - scaledW) / 2
```

왜 letterboxing인가: YOLO 모델은 정사각형 입력을 기대한다. 단순 리사이즈(stretch)하면 물체가 비율 왜곡돼 인식률이 떨어진다.

**NHWC 변환**

```kotlin
// YUV(카메라 포맷) → RGB → 0.0~1.0 정규화 → NHWC Float32
val yy = (yBuffer.get(yIndex).toInt() and 0xFF).coerceAtLeast(16)
val r = ((298 * c + 409 * vv + 128) shr 8).coerceIn(0, 255)
inputBuffer.putFloat(offset, rgbNorm[r])  // rgbNorm[r] = r / 255f
```

왜 직접 YUV 변환인가: Android 카메라는 기본적으로 YUV_420_888 포맷으로 프레임을 제공한다. Bitmap 변환을 거치면 중간 객체 생성·GC 부담이 생기므로 ByteBuffer에 직접 변환한다.

**SamplingPlan 캐시**

```kotlin
// 같은 화면 레이아웃(해상도, 회전)이면 좌표 매핑 테이블 재계산 안 함
cachedPlan?.let { if (it.key == key) return it }
```

캡처 해상도나 회전이 바뀌지 않으면(보통 그렇다) 매 프레임마다 IntArray 두 개를 다시 계산하지 않고 캐시를 재사용한다.

**두 가지 출력 포맷 처리**

```kotlin
// YOLO11n (raw output): shape [1, 84, N] — cx/cy/w/h + 80개 클래스 점수
isRawOutput = (outputRows == 84)
// YOLO26n (end-to-end NMS): shape [1, N, 6] — x1/y1/x2/y2/score/classId
```

모델마다 출력 형식이 달라서 `postProcessRaw()`와 `postProcessEndToEnd()` 두 경로가 있다.

---

### 3.2 MvpPipeline — 온디바이스 ByteTrack-lite

**역할**: 연속 프레임에서 같은 물체를 연결해 track_id를 부여하고, EMA로 좌표·거리를 안정화한다.

**IoU 매칭 로직**

```kotlin
// 이번 프레임 탐지 결과 ↔ 이전 트랙 목록
// 1. 같은 클래스끼리만 매칭 (의자↔의자, 사람↔사람)
// 2. IoU > 0.25인 쌍을 후보로 수집
// 3. IoU 높은 순서로 탐욕적 할당 (헝가리안 알고리즘 단순화 버전)
for ((_, di, ti) in scoredPairs.sortedByDescending { it.first }) {
    if (di in assignedDetectionIds) continue
    if (track.id in assignedTrackIds) continue
    // 매칭 확정
}
```

**왜 IoU 0.25인가**: 너무 낮으면 다른 물체끼리 연결될 수 있고, 너무 높으면 물체가 조금만 움직여도 트랙이 끊겨 새 track_id가 부여된다. 0.25는 "약간 겹치면 같은 물체"라는 경험적 값이다.

**EMA 평활화**

```kotlin
track.cx = EMA_ALPHA * det.cx + (1f - EMA_ALPHA) * track.cx
// EMA_ALPHA = 0.55: 현재 55% + 이전 45%
```

YOLO는 프레임마다 bbox 위치가 조금씩 달라진다. EMA 없이 raw값을 쓰면 "3시 방향 → 2시 방향 → 3시 방향"처럼 방향이 흔들리고, TTS가 매번 다른 말을 하게 된다.

**위험도(riskScore) 계산**

```kotlin
private fun computeRisk(det: Detection): Float {
    val centerWeight = 1f - min(0.6f, abs(det.cx - 0.5f) * 1.2f)  // 화면 중앙일수록 위험
    val distanceWeight = when {         // 거리가 가까울수록 위험
        distanceM <= 0.8f -> 1.0f
        distanceM <= 1.5f -> 0.85f
        ...
    }
    val classWeight = when {            // 차량·위험물일수록 위험
        det.classKo in VoicePolicy.vehicleKo() -> 1.0f
        ...
    }
    val sizeBoost = min(0.25f, area * 1.8f)  // bbox 클수록 추가 위험
    return (centerWeight * distanceWeight * classWeight + sizeBoost).coerceIn(0f, 1f)
}
```

---

### 3.3 VoicePolicy — 정책 관리자

**역할**: `policy.json`을 파싱해 앱 전체에서 사용하는 분류 기준과 임계값을 제공한다.

**초기화 흐름**

```kotlin
fun init(appContext: Context) {
    if (snap != null) return          // 이미 초기화됐으면 skip
    synchronized(this) {
        if (snap != null) return      // double-checked locking
        val cached = prefs.getString(PREF_POLICY_JSON, null)
        val json = when {
            !cached.isNullOrBlank() -> cached      // 캐시된 서버 정책 우선
            else -> assets.open("policy_default.json")...  // 없으면 번들 기본값
        }
        snap = parsePolicy(json)
    }
}
```

**왜 캐시된 서버 정책이 우선인가**: 서버에서 한번 받아온 정책(예: 새 위험 물체 추가, 거리 임계값 조정)이 앱 재시작 후에도 유지돼야 한다. 매번 서버에서 받으면 오프라인일 때 기본값으로 퇴화된다.

**거리 추정 방법**

```kotlin
fun calcDistBboxM(classKo: String, w: Float, h: Float): Double {
    val area = w * h
    val calib = (bboxCalibAreaByClass[classKo] ?: bboxCalibArea).toDouble()
    return sqrt(calib / area)
    // 원리: 물체의 실제 크기가 고정돼 있다고 가정할 때,
    // bbox 면적이 클수록 가깝고, 작을수록 멀다.
    // calib = 물체가 1미터 거리에 있을 때의 기준 bbox 면적
}
```

왜 클래스별로 다른가: 사람(`calib ≈ 0.08`)과 버스(`calib ≈ 0.35`)는 실제 크기가 전혀 다르다. 같은 면적의 bbox라도 버스는 훨씬 멀리 있다.

---

### 3.4 SentenceBuilder — 온디바이스 NLG

**역할**: Detection 목록을 받아 시각장애인이 이해할 수 있는 한국어 문장을 생성한다.

**방향 안정화 (getStableClock)**

```kotlin
private fun getStableClock(classKo: String, cx: Float, index: Int): String {
    val newClock = getClock(cx)
    val uniqueKey = "${classKo}_$index"   // 같은 클래스가 여러 개일 때 구분
    val prev = stableClock[uniqueKey]
    if (prev == null || clockDistance(prev, newClock) >= 2) {
        stableClock[uniqueKey] = newClock  // 2칸 이상 이동해야 방향 변경
    }
    return stableClock[uniqueKey]!!
}
```

**왜 2칸 이상 이동해야 변경하는가**: EMA 후에도 cx가 약간 흔들린다. "11시 → 12시 → 11시"처럼 방향이 왔다갔다하면 TTS가 "왼쪽 오른쪽 왼쪽"을 반복한다. 시계 2칸(예: 11시→1시)이상 이동해야 진짜 방향이 바뀐 것으로 판단한다.

**한국어 조사 처리**

```kotlin
fun josaIGa(word: String): String {
    val last = word.last()
    return if (last in '가'..'힣' && (last.code - 0xAC00) % 28 != 0) "이" else "가"
    // (유니코드 - 0xAC00) % 28 == 0 → 받침 없음 → "가"
    // 예: 의자(자=받침없음) → "의자가", 책(받침있음) → "책이"
}
```

---

### 3.5 MainActivity — 전체 조율자

**동시 실행 제어**

```kotlin
private val inFlightCount = AtomicInteger(0)  // 동시 분석/서버 요청 수
private val MAX_ON_DEVICE_IN_FLIGHT = 1       // 동시 추론은 최대 1개

// 프레임 분석 시작 전
if (inFlightCount.get() >= MAX_ON_DEVICE_IN_FLIGHT) return  // 이미 처리 중이면 skip

inFlightCount.incrementAndGet()
// ... 분석 완료 후
inFlightCount.decrementAndGet()
```

왜 최대 1개인가: TfliteYoloDetector.detect()에 `@Synchronized`가 있어 여러 스레드가 동시에 추론할 수 없고, 이전 결과가 처리 완료되기 전에 새 프레임이 들어오면 혼선이 생긴다.

**TTS 잠금**

```kotlin
private val ttsBusy = AtomicBoolean(false)

// 말하기 전
if (!ttsBusy.compareAndSet(false, true)) return  // 이미 말하는 중이면 skip

// TTS onDone 콜백에서
ttsBusy.set(false)  // 말이 끝나면 해제
```

왜 `compareAndSet`인가: `if (!ttsBusy) { ttsBusy = true; speak() }`는 check-then-act 사이에 다른 스레드가 끼어들 수 있다. `compareAndSet`은 원자적(atomic) 연산이라 안전하다.

---

## 4. 서버 레이어 분석

### 4.1 세션 관리 설계

**session_id 정규화**

```python
def _normalize_session_id(wifi_ssid: str = "", device_id: str = "") -> str:
    preferred = device_id or wifi_ssid  # device_id 우선
    value = (preferred or "").strip().strip('"')
    if not value or value.lower() in {"<unknown ssid>", "unknown ssid", "0x"}:
        return f"anonymous_{uuid.uuid4().hex[:8]}"  # WiFi 없는 익명 기기
    return value
```

**왜 device_id가 wifi_ssid보다 우선인가**  
WiFi SSID는 장소 식별자(같은 공간의 여러 기기)로 설계됐고, device_id는 특정 기기를 식별한다. 현재 MVP는 기기별 대시보드가 목표이므로 device_id 우선. 나중에 장소별 집계가 필요해지면 wifi_ssid를 별도 키로 활용할 수 있다.

**왜 anonymous에 UUID를 붙이는가**  
WiFi 없는 여러 기기가 모두 `"anonymous"`라는 같은 session_id를 가지면 대시보드에서 섞인다. UUID를 붙여서 기기마다 격리한다.

---

### 4.2 SessionTracker — 서버 EMA

**역할**: 여러 프레임에 걸쳐 물체 거리를 안정화하고 "가까워지고 있어요" 변화를 감지한다.

**왜 Android에서 이미 EMA를 했는데 서버에서 또 하는가**

```
Android MvpPipeline EMA: cx/cy/w/h 좌표 안정화 → 방향 흔들림 방지
서버 SessionTracker EMA: distanceM 안정화 → 거리 변화 추이 추적 + 접근 감지
```

Android EMA는 온디바이스에서만 유지되고 서버 재시작 시 사라진다. 서버 EMA는 여러 요청에 걸쳐 누적돼 "이전 프레임과 비교한 접근 속도"를 계산할 수 있다.

**_object_key 설계**

```python
def _object_key(obj: dict) -> str:
    tid = obj.get("track_id")
    if tid not in (None, "", 0, "0"):
        return f"track:{tid}"    # Android ByteTrack이 부여한 ID 사용
    return f"class:{cls}"        # track_id 없으면 클래스명으로 fallback
```

Android가 track_id를 제공하면 "같은 물체"임을 확실히 알 수 있다. 그렇지 않으면 같은 클래스명 = 같은 물체로 근사한다.

**VotingBuffer**

```python
class VotingBuffer:
    def add_frame(self, detected_classes: set[str]) -> None:
        self._frames.append(set(detected_classes))  # 최근 N프레임 유지

    def is_confirmed(self, cls: str) -> bool:
        count = sum(1 for frame in self._frames if cls in frame)
        return (count / len(self._frames)) >= self.threshold  # 60% 이상
```

왜 필요한가: Android 쪽에 이미 voteOnly()가 있는데, 서버 측 VotingBuffer는 `/detect` 엔드포인트(서버 추론 경로, 레거시)에서의 오탐 방지용이다. `/detect_json`은 이미 Android에서 보팅을 거쳐온 결과이므로 실질적으로 VotingBuffer가 항상 통과시킨다.

---

### 4.3 NLG (sentence.py) — 서버 문장 생성

**Android SentenceBuilder vs 서버 sentence.py 차이**

| 항목 | Android SentenceBuilder | 서버 sentence.py |
|------|------------------------|-----------------|
| 언어 | Kotlin | Python |
| 호출 시점 | YOLO 추론 직후 (즉시) | HTTP 응답 생성 시 |
| 입력 | Detection(cx, cy, w, h) | 정규화된 objects 딕셔너리 |
| 거리 계산 | VoicePolicy.calcDistBboxM() | _distance_from_bbox() |
| 실행 조건 | 항상 | 서버 URL 설정 시 |

두 NLG는 구조가 동일하지만 완전히 독립적으로 동작한다. 서버 응답이 오면 서버 문장으로 TTS를 교체하고, 오지 않으면 Android 문장을 그대로 사용한다.

**alert_mode 분류 로직**

```python
def get_alert_mode(obj: dict, is_hazard: bool = False) -> str:
    if is_hazard: return "critical"          # 계단·낙차는 거리 무관
    if is_vehicle and dist_m < v_m: return "critical"
    if is_animal  and dist_m < a_m: return "critical"
    if dist_m < g_m:               return "critical"
    if dist_m < b_m:               return "beep"
    return "silent"
```

**왜 silent가 있는가**: 멀리 있는 물체는 음성 안내 없이 무시한다. 매 프레임마다 "5미터 앞에 의자가 있어요"를 말하면 정작 중요한 경고를 놓친다. 사용자가 직접 "뭐 있어?"라고 물어볼 때 silent 상태의 물체도 포함해 대답한다.

---

### 4.4 DB — 이중 저장 구조

```
detection_events + detections   ← /detect 이벤트 이력 (이벤트 단위)
recent_detections               ← /detect_json 최근 프레임 (질문 응답용)
snapshots                       ← 공간 스냅샷 (공간 변화 감지용)
gps_history                     ← GPS 이동 경로 (대시보드 지도용)
```

**왜 recent_detections와 detection_events가 분리돼 있는가**

- `detection_events`는 **이벤트 단위** 저장: "언제 어디서 무엇을 탐지했다"는 이력. 24시간 분석, 패턴 파악 용도. 삭제 기준: 세션당 최근 200개.
- `recent_detections`는 **최신 상태** 저장: "지금 이 세션에서 마지막으로 본 물체". 질문 응답 시 tracker가 비어있을 때 복원용. 삭제 기준: 세션당 최근 500개.

**백그라운드 이벤트 Writer 패턴**

```python
# /detect 요청 스레드는 큐에 넣고 즉시 반환 (응답 지연 없음)
def enqueue_detection_event(**kwargs) -> bool:
    _event_queue.put_nowait(kwargs)
    return True

# 별도 daemon 스레드가 배치로 DB 저장
def _event_writer_loop():
    while True:
        batch = []
        first = _event_queue.get(timeout=0.25)
        # 최대 24개까지 모아서 한번에 저장
        for item in batch:
            save_detection_event(**item)
```

왜 필요한가: DB 쓰기(특히 PostgreSQL 원격)는 수~수십 ms가 걸린다. 초당 수 회 호출되는 `/detect`가 이 시간을 기다리면 전체 응답 지연이 생긴다.

---

### 4.5 events.py — SSE 브로드캐스트

**구조**

```python
_subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)

@asynccontextmanager
async def subscribe(session_id: str):
    queue = asyncio.Queue(maxsize=16)
    _subscribers[session_id].add(queue)  # 구독 시작
    try:
        yield queue
    finally:
        _subscribers[session_id].discard(queue)  # 연결 끊기면 자동 제거

async def publish(session_id: str, event: dict) -> None:
    for queue in list(_subscribers.get(session_id, ())):
        if queue.full():
            queue.get_nowait()  # 가득 찼으면 가장 오래된 메시지 버림
        queue.put_nowait(payload)
```

**왜 Queue 크기가 16인가**: 대시보드가 잠깐 느려지거나 탭 전환 중일 때 최대 16개 이벤트까지 버퍼링한다. 16개를 넘으면 오래된 것부터 버려서 항상 최신 상태를 보여준다.

**왜 list(_subscribers...) 복사본을 순회하는가**: 순회 중에 `subscribe`/`unsubscribe`로 `_subscribers[session_id]`가 변경될 수 있다. 원본 set을 순회하다 크기가 바뀌면 RuntimeError가 발생한다.

---

## 5. 핵심 알고리즘 이해

### 5.1 EMA (지수이동평균)

```
smooth_t = α × current_t + (1-α) × smooth_{t-1}
α = 0.55: 현재 55% + 이전 45%

예시: 거리 측정값이 1.0 → 1.3 → 0.9 → 1.1 로 흔들릴 때
  t=1: smooth = 1.0
  t=2: smooth = 0.55×1.3 + 0.45×1.0 = 1.165
  t=3: smooth = 0.55×0.9 + 0.45×1.165 = 1.019
  t=4: smooth = 0.55×1.1 + 0.45×1.019 = 1.059  ← 흔들림 줄어듦
```

**α를 0.55로 설정한 이유**: 0.5 미만이면 이전 값에 너무 끌려서 반응이 느리고, 0.7 이상이면 현재 값에 너무 민감해서 흔들림이 많다. 0.55는 "균형점"으로 경험적으로 선택됐다.

### 5.2 bbox 기반 거리 추정

```
calib = 1미터 거리에서 물체의 기준 bbox 면적
area  = 현재 bbox 면적 (w × h, 0.0~1.0 정규화값)

dist = √(calib / area)

예시: 사람(calib=0.08)이 화면 면적의 2%(area=0.02)를 차지하면
  dist = √(0.08 / 0.02) = √4 = 2.0m
```

**한계**: 카메라 앵글, 물체 자세(측면/정면), 실제 개인별 키 차이 등에 따라 오차가 있다. 정확한 측정보다는 "가까운지 먼지" 판단에 집중한다.

### 5.3 IoU (Intersection over Union)

```
IoU = 교집합 넓이 / 합집합 넓이

두 bbox가 많이 겹칠수록 IoU 높음 → 같은 물체일 가능성 높음

MvpPipeline에서 사용:
- IoU > 0.25: 이전 track과 매칭 (같은 물체로 판단)

removeDuplicates에서 사용:
- 같은 클래스, IoU > 0.3: 중복 bbox로 판단 → confidence 낮은 것 제거
```

### 5.4 한국어 받침 유무 판별

```python
(ord(last_char) - 0xAC00) % 28 == 0  → 받침 없음
(ord(last_char) - 0xAC00) % 28 != 0  → 받침 있음

원리:
  한글 유니코드: 0xAC00(가) ~ 0xD7A3(힣)
  가 = 0xAC00, 각 = 0xAC01, ..., 갛 = 0xAC1B (28개 = 받침 종류 수)
  간 = 0xAC04 → (0xAC04 - 0xAC00) % 28 = 4 ≠ 0 → 받침 있음
  가 = 0xAC00 → (0xAC00 - 0xAC00) % 28 = 0 → 받침 없음

따라서:
  "의자" → 자(0xC790) → (0xC790 - 0xAC00) % 28 = 0 → "의자가"
  "책"   → 책(0xCC45) → (0xCC45 - 0xAC00) % 28 = 5 → "책이"
```

---

## 6. Android ↔ 서버 인터페이스

### POST /detect_json 요청 형식

```json
{
  "device_id": "pixel7_abc123",
  "wifi_ssid": "HomeWifi",
  "request_id": "and-1234567890",
  "mode": "장애물",
  "camera_orientation": "front",
  "lat": 37.5665, "lng": 126.9780,
  "detections": [
    {
      "class_ko": "의자",
      "confidence": 0.91,
      "cx": 0.5, "cy": 0.55,
      "w": 0.2, "h": 0.25,
      "zone": "12시",
      "dist_m": 1.5,
      "track_id": 3,
      "risk_score": 0.72,
      "vibration_pattern": "DOUBLE",
      "is_vehicle": false,
      "is_animal": false
    }
  ]
}
```

**각 필드의 의미**
- `zone`: Android SentenceBuilder.getClock()이 계산한 시계 방향 (서버가 참고만 함)
- `dist_m`: VoicePolicy.calcDistBboxM()이 계산한 거리 추정값
- `track_id`: MvpPipeline이 부여한 ByteTrack ID (서버 EMA 연결에 사용)
- `risk_score`: MvpPipeline.computeRisk()가 계산한 0~1 위험도
- `vibration_pattern`: 진동 패턴 (서버가 override 가능)

### POST /detect_json 응답 형식

```json
{
  "mode": "장애물",
  "sentence": "오른쪽 1.5미터에 의자가 있어요. 오른쪽으로 피하세요.",
  "alert_mode": "critical",
  "objects": [...],
  "changes": ["가방이 가까워지고 있어요"],
  "request_id": "and-1234567890",
  "process_ms": 12
}
```

Android는 `sentence`를 TTS로 재생하고 `alert_mode`에 따라 진동·음소거를 결정한다.

---

## 7. 설계 결정 이유 정리

| 설계 결정 | 이유 |
|-----------|------|
| Android TFLite + 서버 NLG | 실시간성(온디바이스)과 품질(서버) 동시 확보 |
| policy.json SSOT | Android·서버 분류 기준 동기화. 오탐 수정 시 앱 재배포 불필요 |
| EMA가 Android·서버 양쪽 존재 | 역할 다름: Android는 좌표 안정화, 서버는 접근 감지 |
| wifi_ssid + device_id 분리 전송 | 장소 식별(wifi)과 기기 식별(device)을 미래에 독립 활용 가능 |
| session_id = device_id 우선 | MVP 단계에서는 기기별 대시보드가 목표 |
| 백그라운드 DB Writer | /detect 응답 지연 없이 DB 쓰기 비동기 처리 |
| SSE keepalive 15초 | 프록시(Nginx, Cloud Run 등) 기본 타임아웃 대비 |
| anonymous_UUID | WiFi 없는 기기들이 같은 session_id 공유로 대시보드 오염 방지 |
| MAX_ON_DEVICE_IN_FLIGHT = 1 | TFLite @Synchronized + GPU delegate 단일 인스턴스 구조상 직렬화 필요 |
| VotingBuffer 초기 3프레임 패스 | 앱 시작 직후 물체가 없다고 잘못 판단하지 않도록 워밍업 허용 |
