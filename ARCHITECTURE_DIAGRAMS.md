# VoiceGuide 아키텍처 다이어그램

현재 코드는 온디바이스 추론을 우선합니다. Android 앱이 CameraX 프레임에서 TFLite YOLO를 실행하고, 문장 생성과 TTS를 즉시 처리합니다. 서버는 이미 탐지된 JSON을 받아 tracker, DB, 대시보드, 기록 조회를 담당합니다.

---

## 1. 전체 시스템 구조

```mermaid
graph TB
    subgraph Android["Android 앱 - Kotlin / CameraX"]
        Camera["CameraX<br/>ImageAnalysis 스트림<br/>필요 시 ImageCapture"]
        Yolo["TfliteYoloDetector<br/>yolo11n_320.tflite 기본<br/>yolo26n_float32.tflite fallback<br/>GPU delegate 또는 XNNPACK"]
        Stabilize["프레임 안정화<br/>NMS + 중복 제거<br/>3프레임 vote<br/>MvpPipeline IoU/EMA"]
        PolicyA["VoicePolicy<br/>policy_default.json<br/>서버 /api/policy 동기화"]
        SentenceA["SentenceBuilder<br/>장애물 / 찾기 / 질문 / 들고있는것"]
        Output["TTS + 진동 + UI<br/>tvStatus / tvDetected<br/>BoundingBoxOverlay"]
        Upload["백그라운드 JSON 업로드<br/>POST /detect<br/>GPS heartbeat /gps"]
    end

    subgraph Server["FastAPI 서버 - Cloud Run 또는 로컬"]
        Health["GET /health<br/>json-router<br/>inference disabled"]
        PolicyS["GET /api/policy<br/>ETag 정책 배포"]
        Detect["POST /detect<br/>Android 객체 JSON 정규화"]
        Legacy["POST /detect_json<br/>구형 recent_detections 호환"]
        Tracker["SessionTracker<br/>EMA smoothing<br/>접근 변화 감지"]
        NLG["src/nlg/sentence.py<br/>서버 측 한국어 문장"]
        Writer["비동기 DB writer<br/>queue + batch flush"]
        Realtime["GET /status/{session_id}<br/>GET /events/{session_id}<br/>SSE 대시보드"]
        Team["GET /sessions<br/>GET /team-locations"]
    end

    subgraph Storage["저장소"]
        DB["SQLite 로컬<br/>또는 PostgreSQL / Supabase"]
        Tables["detection_events<br/>detections<br/>snapshots<br/>gps_history<br/>recent_detections"]
        Dashboard["templates/dashboard.html<br/>Leaflet + SSE"]
    end

    Camera --> Yolo --> Stabilize --> SentenceA --> Output
    PolicyS -.정책 동기화.-> PolicyA
    PolicyA --> Stabilize
    Stabilize --> Upload
    Upload --> Detect
    Upload --> Legacy
    Upload --> Realtime
    Detect --> Tracker --> NLG
    Detect --> Writer
    Legacy --> Tracker
    Legacy --> Writer
    Writer --> DB --> Tables
    Realtime --> Dashboard
    Team --> Dashboard
    Health --> Server

    style Android fill:#e8f5e9
    style Server fill:#e3f2fd
    style Storage fill:#fff8e1
    style Output fill:#fce4ec
```

---

## 2. Android 1프레임 처리 흐름

```mermaid
sequenceDiagram
    participant C as CameraX
    participant T as TFLite
    participant M as MvpPipeline
    participant S as SentenceBuilder
    participant U as UI/TTS/진동
    participant A as FastAPI
    participant D as DB writer
    participant V as Dashboard/SSE

    C->>T: ImageProxy 또는 JPEG 파일
    T->>T: 전처리 + YOLO 추론 + postprocess
    T-->>M: Detection 목록
    M->>M: voteOnly, removeDuplicates, IoU tracking, EMA, risk_score
    M-->>S: 안정화된 상위 객체
    S-->>U: 로컬 안내 문장
    U->>U: tvStatus 갱신, TTS, 진동 패턴

    par 비차단 서버 동기화
        M->>A: POST /detect JSON
        A->>A: 객체 정규화, bbox 기반 거리 보정, alert_mode 계산
        A->>D: detection_events/detections 비동기 저장 enqueue
        A->>V: status 이벤트 publish
        A-->>M: process_ms/perf 포함 응답
    and GPS heartbeat
        U->>A: POST /gps
        A->>V: 위치/경로 이벤트 publish
    end
```

핵심 포인트:

- 서버 응답을 기다린 뒤 말하지 않습니다. 사용자는 Android 로컬 `SentenceBuilder` 결과를 즉시 듣습니다.
- 서버는 이미지나 모델 추론을 수행하지 않습니다. `/health`도 `inference: disabled`를 반환합니다.
- `/detect`가 현재 Android 업로드 주 경로이고, `/detect_json`은 구형 포맷 및 테스트 호환용으로 남아 있습니다.

---

## 3. 음성 명령과 모드

```mermaid
graph TD
    Voice["STT 결과"] --> Classify["classifyKeyword()"]

    Classify --> Obstacle["장애물<br/>즉시 캡처/분석"]
    Classify --> Find["찾기<br/>target 추출<br/>예: 의자 찾아줘"]
    Classify --> Question["질문/확인<br/>즉시 캡처<br/>예: 지금 뭐 있어?"]
    Classify --> Held["들고있는것<br/>근거리/손 앞 물체 확인"]
    Classify --> Traffic["신호등<br/>현재는 모드 진입 후 일반 분석 흐름"]
    Classify --> Control["다시읽기 / 중지 / 재시작<br/>볼륨업 / 볼륨다운"]

    Obstacle --> LocalNlg["SentenceBuilder.build()"]
    Find --> LocalNlgFind["SentenceBuilder.buildFind()"]
    Question --> LocalNlg
    Held --> LocalNlgHeld["SentenceBuilder.buildHeld()"]

    LocalNlg --> Speak["TTS/진동/UI"]
    LocalNlgFind --> Speak
    LocalNlgHeld --> Speak
    Traffic --> Speak
    Control --> Speak

    Speak --> Upload["선택: /detect 업로드"]

    style Speak fill:#fce4ec
    style Upload fill:#e3f2fd
```

---

## 4. 서버 API 표면

```mermaid
graph LR
    Client["Android / Dashboard / TestClient"] --> Policy["GET /api/policy"]
    Client --> Detect["POST /detect"]
    Client --> Legacy["POST /detect_json"]
    Client --> Question["POST /question"]
    Client --> GPS["POST /gps"]
    Client --> Status["GET /status/{session_id}"]
    Client --> Events["GET /events/{session_id}"]
    Client --> Sessions["GET /sessions"]
    Client --> Team["GET /team-locations"]
    Client --> Dashboard["GET /dashboard"]
    Client --> Health["GET /health"]

    Detect --> Tracker["tracker.update"]
    Detect --> Queue["db.enqueue_detection_event"]
    Detect --> Snapshot["db.save_snapshot"]
    GPS --> GpsDb["db.save_gps"]
    Queue --> Tables["detection_events + detections"]
    Legacy --> Recent["recent_detections"]
    Status --> Snapshot
    Status --> GpsDb
    Events --> SSE["SSE publish/subscribe"]
```

현재 `feature/jaehyun`의 `routes.py`에는 `/history`, `/routes`, `/gps/route/save`, `/locations` 계열 엔드포인트가 구현되어 있지 않습니다. Android 장소 저장/조회는 현재 앱 내부 `SharedPreferences` 흐름입니다.

---

## 5. 성능/안정화 지점

```mermaid
graph TB
    subgraph AndroidPerf["Android 성능 경로"]
        Stream["INTERVAL_MS 50ms<br/>MAX_ON_DEVICE_IN_FLIGHT 1"]
        ServerSlots["MAX_SERVER_IN_FLIGHT 4"]
        MvpThrottle["MVP_UPDATE_INTERVAL_MS 750ms"]
        UploadThrottle["SERVER_UPLOAD_INTERVAL_MS 250ms<br/>SERVER_FORCE_SEND_FRAMES 5"]
        Model["TFLite GPU FP32<br/>fallback XNNPACK 4 threads"]
    end

    subgraph ServerPerf["서버 성능 경로"]
        NoInfer["이미지 추론 없음"]
        SaveEvery["DETECT_SAVE_EVERY_N_FRAMES 기본 5"]
        SnapshotMin["SNAPSHOT_MIN_INTERVAL_S 기본 1.0"]
        Queue["DETECTION_EVENT_QUEUE_MAX 512<br/>BATCH_SIZE 24<br/>FLUSH_INTERVAL 0.25s"]
        Keep["session별 event 200개<br/>recent_detections 500개<br/>snapshot 20개"]
    end

    Stream --> Model --> MvpThrottle --> UploadThrottle --> ServerSlots
    ServerSlots --> NoInfer --> SaveEvery --> Queue --> Keep
    SaveEvery --> SnapshotMin
```

---

## 6. 현재 문서 기준

- Android 실제 구현: `android/app/src/main/java/com/voiceguide/`
- 서버 실제 구현: `src/api/routes.py`, `src/api/db.py`, `src/api/tracker.py`
- 문장 생성: Android `SentenceBuilder.kt`, 서버 `src/nlg/sentence.py`
- 정책 SSOT: `src/config/policy.json`, Android fallback `assets/policy_default.json`
- 상태 보고서: `CURRENT_STATUS_REPORT.md`
- 시뮬레이션 스크립트: `test_simulation.py`
