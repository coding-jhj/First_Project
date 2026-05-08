# VoiceGuide 버그 원인 분석 보고서

> 작성일: 2026-05-08  
> 목적: 단순 버그 나열이 아닌, **왜 이런 데이터가 흐르는지 / 왜 이런 설계가 문제인지**를 데이터 흐름과 로직 기반으로 분석

---

## 1. 시스템 전체 데이터 흐름 (먼저 이해해야 할 구조)

```
[Android 앱]
  └─ CameraX 1초마다 프레임 캡처
  └─ TfliteYoloDetector.detect()
       └─ yolo26n_float32.tflite 온디바이스 추론
       └─ Detection(classKo, cx, cy, w, h, confidence) 생성
  └─ MvpPipeline.update(detections)
       └─ IoU 기반 track_id 부여 (ByteTrack-lite)
       └─ EMA로 cx/cy/w/h/distanceM 평활화
       └─ riskScore, vibrationPattern 계산
  └─ HTTP POST /detect_json 전송
       {device_id, wifi_ssid, detections: [{class_ko, cx, cy, w, h, zone, dist_m, track_id, ...}]}

[FastAPI 서버]
  └─ routes.py: /detect_json
       └─ _normalize_session_id(wifi_ssid, device_id) → session_id
       └─ tracker.py: SessionTracker.update() → EMA 서버측 재평활화
       └─ db.py: save_detections() → recent_detections 테이블
       └─ sentence.py: build_sentence() → 한국어 TTS 문장
       └─ events.py: publish() → 대시보드 SSE 브로드캐스트
  └─ JSON 응답: {sentence, alert_mode, objects, ...}

[Android 앱]
  └─ TTS.speak(response.sentence)
  └─ 진동 패턴 실행
```

**핵심 설계 원칙:**
- Android = 추론(YOLO) + 트래킹(ByteTrack) 담당
- 서버 = NLG(문장 생성) + DB 저장 + 대시보드 브로드캐스트 담당
- `wifi_ssid` = 장소 식별 (같은 WiFi = 같은 공간)
- `session_id` = normalize(wifi_ssid, device_id) = 기기 식별

---

## 2. 버그별 심층 분석

---

### [버그 1] routes.py — `save_snapshot` 중복 저장 및 키 불일치

#### 왜 이런 데이터가 서버에 가는가

Android `MainActivity.kt`는 탐지 결과를 전송할 때 `wifi_ssid`와 `device_id`를 **항상 함께** 보낸다.

```kotlin
// MainActivity.kt — sendDetectionJsonToServer()
val payload = JSONObject().apply {
    put("device_id", deviceId)
    put("wifi_ssid", wifiSsid)   // WifiManager로 현재 연결된 SSID 읽어서 전송
    put("detections", detectionArray)
    ...
}
```

`wifi_ssid`를 보내는 이유: **같은 WiFi = 같은 장소**라는 가정 하에, 공간 기억(스냅샷)을 WiFi SSID 단위로 저장하기 위해서다. 예를 들어 "우리 집 WiFi"에 연결돼 있으면, 어제 탐지된 소파·책상 위치를 기억해서 "어제와 비교해 의자가 생겼어요" 같은 안내를 할 수 있다.

#### 어떤 흐름에서 버그가 발생했나

```python
# routes.py — /detect 엔드포인트 (버그 있던 코드)
session_id = _normalize_session_id(wifi_ssid, device_id)
# _normalize_session_id: device_id 우선 → device_id 없으면 wifi_ssid 사용

# 문제 1: get_snapshot은 wifi_ssid로 조회
previous = db.get_snapshot(wifi_ssid) if should_persist and wifi_ssid else None

# 문제 2: save는 두 키로 중복 저장
if objects and should_persist:
    db.save_snapshot(wifi_ssid, objects)   # wifi_ssid 키
    db.save_snapshot(session_id, objects)  # session_id 키 (중복!)
```

**흐름 추적:**
1. Android가 `wifi_ssid="HomeWifi"`, `device_id="pixel7"` 전송
2. 서버에서 `session_id = "pixel7"` (device_id 우선)
3. 스냅샷 조회: `get_snapshot("HomeWifi")` → 과거 데이터 조회
4. 스냅샷 저장: `save_snapshot("HomeWifi", ...)` + `save_snapshot("pixel7", ...)` → **2개 키로 저장**
5. 다음 요청에서 조회: `get_snapshot("HomeWifi")` → 정상 작동하는 것처럼 보임
6. **WiFi 없을 때**: `wifi_ssid=""`, `session_id="anonymous_abc123"` → `previous=None` 항상 → **공간 변화 감지 완전 불능**

#### 근본 원인: 설계 변천 과정의 불일치

초기 설계에서는 WiFi SSID가 유일한 장소 식별자였다. 이후 WiFi 없는 실외/지하 환경을 위해 `device_id` 기반의 `session_id` 개념이 추가됐는데, `save`/`get_snapshot`의 키를 통일하지 않은 채로 두 방식이 혼재됐다.

#### 수정 내용

```python
# 수정 후: session_id 하나로 통일
previous = db.get_snapshot(session_id) if should_persist else None
if objects and should_persist:
    db.save_snapshot(session_id, objects)  # 단일 키
```

---

### [버그 2] tracker.py — monkey-patch로 인한 키 체계 불일치

#### 왜 이런 구조가 생겼나 (설계 역사 이해)

VoiceGuide는 처음에 **서버에서 ONNX 추론**을 했다. 그때 `SessionTracker.update()`는 영어 클래스명(`"chair"`, `"person"`)을 키로 쓰는 단순한 EMA 추적기였다.

```python
# 원본 update() — 서버 추론 시절 코드
current_keys = {o["class"] for o in objects}  # "chair", "person" 등 영어 키
self._tracks[cls] = {...}  # "chair" 키로 저장
```

이후 **온디바이스 전환** 후 Android가 `track_id`를 직접 부여하는 ByteTrack-lite를 도입했다. 서버는 이 `track_id`를 활용해 더 정밀한 추적을 해야 했다.

```python
# _mvp_update — 온디바이스 시대의 새 코드
def _object_key(obj):
    tid = obj.get("track_id")
    if tid not in (None, "", 0, "0"):
        return f"track:{tid}"   # "track:1", "track:2" 형태
    return f"class:{cls}"       # "class:의자" 형태
```

기존 `update()`를 삭제하면 기존 테스트가 깨질까봐, 파일 하단에 monkey-patch로 덮어씌웠다.

```python
# tracker.py 하단 (버그 코드)
SessionTracker.update = _mvp_update  # 원본 메서드를 덮어씀
```

#### 어떤 데이터 흐름에서 문제가 생기나

```
Android → track_id=1로 "의자" 탐지 전송

원본 update() (monkey-patch 전 혹시 실행됐다면):
  _tracks["의자"] = {distance_m: 1.5, ...}  ← "의자" 키

_mvp_update (monkey-patch 후):
  _tracks["track:1"] = {distance_m: 1.5, ...}  ← "track:1" 키

다음 프레임 → _mvp_update 실행:
  key = "track:1" → _tracks에서 못 찾음 (이전 키는 "의자")
  → 새 트랙으로 처음부터 시작 → EMA 연결 안 됨 → 거리값 흔들림
```

#### 근본 원인

`_tracks` dict를 원본 `update()`와 `_mvp_update()`가 **다른 키 체계로 공유**했다. 모듈 임포트 타이밍에 따라 두 키가 혼재될 수 있고, 설령 실제로 원본이 실행 안 되더라도 **죽은 코드(dead code)가 있어서 언제든 재발 가능**한 구조였다.

#### 수정 내용

monkey-patch 완전 제거. `_mvp_update`와 `_mvp_get_current_state`를 `SessionTracker` 클래스 메서드로 정식 정의:

```python
class SessionTracker:
    def update(self, objects):  # _mvp_update 내용이 여기에 직접 들어옴
        key = _object_key(obj)  # track_id 또는 "class:이름"으로 일관된 키
        ...
```

---

### [버그 3] db.py — PostgreSQL 모드에서 탐지 1건마다 DELETE 실행

#### 왜 이런 데이터가 서버에 오는가

Android는 초당 약 3~5회 `/detect_json`을 호출하고, 각 호출에는 탐지된 물체 1~8개가 담긴다. 서버는 이 탐지 결과를 `recent_detections` 테이블에 저장해 대시보드와 질문 응답에 활용한다.

#### 어떤 흐름에서 버그가 발생했나

```python
# db.py — save_detections() 버그 코드 (PostgreSQL 모드)
with _conn() as conn:
    for d in detections:          # N개 탐지 결과 루프
        if _IS_POSTGRES:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO recent_detections ...")  # INSERT
                cur.execute("DELETE FROM recent_detections WHERE session_id = %s "
                           "AND id NOT IN (SELECT ... LIMIT 500)")  # DELETE ← 루프 안!
```

**성능 계산:**
- 탐지 5개 × 초당 4회 = 초당 20번 DELETE 쿼리
- 각 DELETE는 서브쿼리(`SELECT ... LIMIT 500`) 포함
- PostgreSQL은 원격 DB(Supabase)라 네트워크 왕복 비용까지 추가
- → **초당 20개 이상의 무거운 쿼리** → DB 연결 풀 고갈, 응답 지연

#### SQLite는 왜 멀쩡했나

```python
# SQLite 경로 (정상 코드)
for d in detections:
    conn.execute("INSERT INTO recent_detections ...")  # INSERT만 루프 안

if not _IS_POSTGRES:
    conn.execute("DELETE FROM ...")  # DELETE는 루프 밖 1회
```

SQLite는 파일 기반이라 쿼리 실행 비용이 낮고, 구현도 루프 밖으로 DELETE를 올바르게 위치시켰다. PostgreSQL 구현 시 SQLite 코드를 참고하면서 `if _IS_POSTGRES` 분기를 루프 안에 잘못 집어넣었다.

#### 근본 원인

INSERT를 1건씩 실행하는 for 루프 안에 DELETE를 함께 넣은 구조. "INSERT 후 오래된 행 정리"라는 의도는 맞지만, 정리 작업은 **모든 INSERT가 끝난 뒤 1회**만 필요하다.

#### 수정 내용

```python
# 수정 후: rows 목록 먼저 만들고 executemany로 일괄 INSERT, DELETE는 1회
rows = [(device_id, session_id, ...) for d in detections]
with conn.cursor() as cur:
    cur.executemany("INSERT INTO recent_detections ...", rows)  # 일괄 INSERT
    cur.execute("DELETE FROM recent_detections WHERE ...")       # DELETE 1회
```

---

### [버그 4] test_api.py — 잘못된 session_id로 DB 검증

#### 어떤 흐름에서 테스트가 잘못됐나

```python
# test_api.py — 버그 코드
response = client.post("/detect_json", json={
    "device_id": "test_detect_json_device",
    "wifi_ssid": "test_detect_json_wifi",
    ...
})

# DB에서 결과 조회 시 device_id를 그대로 사용
recent = db.get_recent_detections("test_detect_json_device", max_age_s=60)
```

**실제 데이터 흐름:**
```
/detect_json 수신
  → session_id = _normalize_session_id(wifi_ssid="test_detect_json_wifi",
                                        device_id="test_detect_json_device")
  → preferred = device_id or wifi_ssid = "test_detect_json_device"  ← device_id 우선
  → session_id = "test_detect_json_device"

db.save_detections(device_id="test_detect_json_device",
                   session_id="test_detect_json_device", ...)
```

우연히 `device_id == session_id`가 성립해서 통과하지만, `_normalize_session_id` 로직이 변경되거나 wifi_ssid가 우선시되는 상황에서는 조용히 실패한다.

#### 근본 원인

테스트가 `_normalize_session_id`의 내부 로직(device_id 우선)을 전제하는 암묵적 가정에 의존했다. 테스트는 **실제 데이터 흐름을 그대로 재현**해야 신뢰할 수 있다.

#### 수정 내용

```python
# 수정 후: 실제와 같은 흐름으로 session_id 계산
from src.api.routes import _normalize_session_id
expected_session = _normalize_session_id(
    wifi_ssid="test_detect_json_wifi",
    device_id="test_detect_json_device"
)
recent = db.get_recent_detections(expected_session, max_age_s=60)
```

---

### [버그 5] routes.py — `/status`, `/events`, `/history` normalize 인자 순서

#### 데이터 흐름

대시보드나 앱이 특정 세션의 상태를 조회할 때 URL 경로에 session_id를 직접 넣어 요청한다.

```
GET /status/pixel7_device
GET /events/pixel7_device
GET /history/pixel7_device
```

#### 버그 분석

```python
# 버그 코드
async def get_session_status(session_id: str):
    req_session_id = _normalize_session_id(session_id)
    #                                       ^^^
    #  _normalize_session_id(wifi_ssid="", device_id="")의 1번째 인자 = wifi_ssid
    #  session_id가 wifi_ssid 위치에 바인딩됨
```

`_normalize_session_id` 시그니처: `(wifi_ssid: str = "", device_id: str = "")`  
→ `_normalize_session_id("pixel7_device")`는 `wifi_ssid="pixel7_device"`로 해석  
→ `preferred = device_id or wifi_ssid = "pixel7_device"`이므로 결과적으로 같아 보이지만…  
→ `device_id`가 실제로 전달되지 않아 **device_id 우선 로직이 우회됨**

#### 수정 내용

```python
req_session_id = _normalize_session_id(device_id=session_id)  # 명시적 키워드 인자
```

---

### [버그 6] policy.json — `bbox_calib_area_by_class` 누락

#### 왜 이 데이터가 중요한가

`VoicePolicy.calcDistBboxM(classKo, w, h)` 함수는 물체의 **클래스별 실제 크기 기준**으로 거리를 추정한다.

```kotlin
fun calcDistBboxM(classKo: String, w: Float, h: Float): Double {
    val calib = (s.bboxCalibAreaByClass[classKo] ?: s.bboxCalibArea).toDouble()
    //           ^^^                               ^^^
    //   클래스별 캘리브 값 (예: 사람은 0.08, 버스는 0.35)
    //   없으면 기본값 0.12 사용
    return sqrt(calib / area)
}
```

예를 들어 "사람"은 bbox_calib_area = 0.08, "버스"는 0.35 등 다른 값을 써야 정확한 거리가 나온다.

#### 어떤 흐름에서 버그가 발생했나

```
앱 시작
  → VoicePolicy.init() → policy_default.json 로드 (bbox_calib_area_by_class 있음)
  → refreshPolicyFromServerAsync() → GET /api/policy → src/config/policy.json 수신
     ↑ 이 파일에 bbox_calib_area_by_class 없음!
  → applyFromServerJson() → parsePolicy() → parseBboxCalibByClass() → emptyMap() 반환
  → 이후 모든 거리 계산이 단일 기본값 0.12만 사용

결과: "사람이 2미터 앞에 있어요" → 실제로는 0.8미터인데 다른 거리 안내
```

`parseBboxCalibByClass`가 `optJSONObject()`를 써서 예외는 안 나지만, **거리 정확도가 클래스별 보정 없이 저하**된다.

#### 수정 내용

`src/config/policy.json`에 `policy_default.json`과 동일한 `bbox_calib_area_by_class` 섹션 추가.

---

### [버그 7] VoiceGuideConstants.kt vs templates.py — CLOCK_TO_DIRECTION 불일치

#### 왜 이 데이터가 TTS 출력에 영향을 주나

Android `SentenceBuilder.kt`는 YOLO bbox의 `cx` 값에서 시계 방향("12시", "2시" 등)을 계산한 뒤, `CLOCK_TO_DIRECTION` 맵으로 한국어 방향 표현("바로 앞", "오른쪽" 등)으로 변환해 TTS 문장을 만든다.

```kotlin
// SentenceBuilder.kt
val clock = getStableClock(det.classKo, det.cx, idx)
val dir = CLOCK_TO_DIRECTION[clock] ?: clock  // 맵에 없으면 "5시" 그대로 TTS에서 읽힘
val locStr = "$dir $distStr"
// → "5시 약 1.5미터" 처럼 시계 숫자가 그대로 나옴 (사용자에게 혼란)
```

#### 불일치 항목

| 시계 방향 | Android (버그 전) | Python templates.py |
|-----------|-------------------|---------------------|
| `"12시"` | `"바로"` | `"바로 앞"` |
| `"5시"` | **없음** | `"오른쪽 아래"` |
| `"6시"` | **없음** | `"바로 뒤"` |
| `"7시"` | **없음** | `"왼쪽 아래"` |

Python 서버는 `/detect` 응답에 `direction` 필드로 "5시", "6시", "7시"를 줄 수 있는데, Android가 이를 받아서 `CLOCK_TO_DIRECTION`에서 찾으면 null 반환 → 원래 값 그대로 TTS 출력.

#### 수정 내용

`VoiceGuideConstants.kt`에 누락된 방향 추가 + `"12시"` 값을 `"바로 앞"`으로 통일:

```kotlin
"12시" to "바로 앞",
"5시" to "오른쪽 아래",
"6시" to "바로 뒤",
"7시" to "왼쪽 아래",
```

---

### [버그 8] events.py — asyncio와 동기 컨텍스트 혼용

#### 시스템에서의 역할

`events.py`는 FastAPI SSE(Server-Sent Events)로 대시보드에 실시간 탐지 결과를 브로드캐스트하는 모듈이다.

```
/detect_json 처리 완료
  → events.publish(session_id, {...})
    → _subscribers[session_id]의 모든 Queue에 데이터 넣기
    → 대시보드 브라우저가 SSE로 실시간 수신
```

#### 버그 분석

```python
# 버그 전: 동기 함수
def publish(session_id: str, event: dict) -> None:
    ...
    queue.put_nowait(payload)  # asyncio.Queue를 동기 컨텍스트에서 조작
```

FastAPI의 `/detect_json`은 `async def`로 정의된 코루틴이다. 비동기 이벤트 루프 위에서 실행 중인 코루틴이 `asyncio.Queue`의 `put_nowait()`을 동기 함수에서 호출하면, 이벤트 루프 스케줄러를 거치지 않아 `_subscribers` dict에 동시 접근하는 race condition이 발생할 수 있다.

#### 수정 내용

```python
async def publish(session_id: str, event: dict) -> None:
    # async def로 선언 → await events.publish(...)로 호출
    # 이벤트 루프 안에서 안전하게 Queue 조작
```

routes.py의 호출부도 `await _publish_dashboard_event(...)` 및 `async def _publish_dashboard_event(...)` 로 연쇄 수정.

---

### [버그 9] TfliteYoloDetector.kt — 모델 파일 없을 때 불친절한 크래시

#### 어떤 상황에서 발생하나

```kotlin
// 버그 코드
modelName = listOf("yolo11n_320.tflite", "yolo26n_float32.tflite").first { name ->
    try { context.assets.open(name).close(); true }
    catch (_: Exception) { false }
}
// 두 파일 모두 없으면 → NoSuchElementException 발생
// → tryInitTfliteDetector()가 잡지만 사용자에게 "모델 없음" 메시지
// → 앱 완전 비작동 상태, 원인 파악 어려움
```

APK 빌드 시 `assets/`에 모델 파일 포함을 빠뜨리거나, 파일명을 잘못 입력하면 발생한다.

#### 수정 내용

```kotlin
modelName = listOf("yolo11n_320.tflite", "yolo26n_float32.tflite").firstOrNull { name ->
    try { context.assets.open(name).close(); true }
    catch (_: Exception) { false }
} ?: throw IllegalStateException(
    "TFLite 모델 파일이 없습니다. assets에 yolo26n_float32.tflite 또는 yolo11n_320.tflite가 필요합니다."
)
// → 명확한 오류 메시지로 원인 즉시 파악 가능
```

---

### [버그 10] db.py — `datetime.now()` timezone 미지정

#### 왜 중요한가

`get_recent_detections()`와 `get_snapshot()`의 cutoff 계산:

```python
# 버그 코드
cutoff = (datetime.now() - timedelta(seconds=max_age_s)).isoformat()
# datetime.now() → 시스템 timezone에 의존하는 naive datetime
# → 서버가 KST(UTC+9)에서 실행되면 "3초 이내" 범위가 UTC 기준으로 엇나감
```

Cloud Run은 UTC 기반으로 실행되고, `detected_at`은 `datetime.now().isoformat()`으로 저장된다. 현재는 우연히 일치하지만 서버 timezone이 바뀌면 조회 범위가 틀려진다.

#### 수정 내용

```python
from datetime import datetime, timezone
cutoff = (datetime.now(timezone.utc) - timedelta(seconds=max_age_s)).isoformat()
```

---

### [버그 11] requirements.txt — torch/torchvision 서버 의존성 포함

#### 왜 이게 문제인가

```
requirements.txt
  torch==2.4.1        ← 2.5GB
  torchvision==0.19.1 ← 500MB
  ultralytics==8.4.33 ← 200MB
```

서버 코드(`src/api/`, `src/nlg/`, `src/config/`)를 전부 검색해도 `import torch`, `import ultralytics`를 사용하는 곳이 **전혀 없다**. 이 패키지들은 모델 학습(`tools/export_onnx.py`, `tools/build_test_images.py`)에만 필요하다.

그러나 서버 Docker 이미지 빌드 시 requirements.txt를 전부 설치하면:
- 이미지 크기: 약 5GB 이상
- Cloud Run 기본 메모리: 512MB ~ 2GB → **배포 실패 또는 메모리 초과**

#### 수정 내용

```
# (dev-only) torch==2.4.1
# (dev-only) torchvision==0.19.1
# (dev-only) ultralytics==8.4.33
```

주석 처리로 서버 배포 시 설치 안 되도록 하되, 개발 참고용으로 목록은 유지.

---

## 3. 종합 교훈

### 설계 측면
| 문제 패턴 | 사례 | 교훈 |
|-----------|------|------|
| 식별자 혼용 | wifi_ssid vs session_id | 한 개념에 한 키. SSOT 원칙 |
| 레거시 코드 방치 | monkey-patch | 전환 완료 후 원본 코드 즉시 제거 |
| 포팅 시 검증 미흡 | SQLite → PostgreSQL 버그 | 다른 DB로 포팅 시 쿼리 실행 횟수 검증 |

### 데이터 흐름 측면
| 문제 패턴 | 사례 | 교훈 |
|-----------|------|------|
| 클라이언트↔서버 스키마 불일치 | CLOCK_TO_DIRECTION, policy.json | Android와 서버가 공유하는 값은 SSOT로 관리 |
| 경계 데이터 처리 미흡 | wifi_ssid="" 엣지케이스 | "권한 없음", "연결 안 됨" 같은 경계값 별도 테스트 |

### 테스트 측면
| 문제 패턴 | 사례 | 교훈 |
|-----------|------|------|
| 우연히 통과하는 테스트 | test_api.py session_id | 테스트는 실제 데이터 흐름을 그대로 재현해야 |
| 미구현 엔드포인트 테스트 | test_server.py /locations | 테스트 대상 존재 여부를 먼저 확인 |
