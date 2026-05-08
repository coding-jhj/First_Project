# VoiceGuide 아키텍처 & 성능 시각화

이 문서는 Mermaid 다이어그램을 포함하고 있습니다. 
GitHub, VS Code Preview, 또는 Mermaid 렌더러에서 보면 자동으로 그림이 표시됩니다.

---

## 1️⃣ 전체 시스템 아키텍처

```mermaid
graph TB
    subgraph Android["🤖 Android 디바이스 (온디바이스)"]
        Camera["📷 CameraX<br/>30fps 프레임 캡처"]
        TFLite["⚙️ TFLite 추론<br/>YOLO26n_float32<br/>29ms/frame"]
        Depth["🔍 Depth Module<br/>(3-4프레임당 1회)<br/>거리 추정"]
        NLG_A["🗣️ NLG 문장생성<br/>policy.json 기반"]
        TTS["🔊 TTS<br/>한국어 음성"]
        UI["📺 UI 표시<br/>tvStatus 갱신"]
        JSON_Send["📤 JSON 전송<br/>(선택)"]
    end
    
    subgraph Server["☁️ 서버 (GCP Cloud Run)"]
        API["🔗 FastAPI<br/>JSON 라우터"]
        NLG_S["🗣️ NLG 재구성<br/>server policy.json"]
        DB_Save["💾 DB 저장<br/>detection_events<br/>detections<br/>recent_detections"]
        Status["📍 Status 배포<br/>GET /status/{device_id}"]
    end
    
    subgraph External["🌐 외부 시스템"]
        Dashboard["📊 대시보드<br/>팀 위치 추적"]
        DB["🗂️ PostgreSQL<br/>(Supabase)<br/>또는 SQLite"]
    end
    
    Camera --> TFLite
    TFLite --> Depth
    Depth --> NLG_A
    NLG_A --> TTS
    NLG_A --> UI
    UI --> JSON_Send
    JSON_Send --> API
    
    API --> NLG_S
    NLG_S --> DB_Save
    DB_Save --> DB
    DB_Save --> Status
    DB --> Dashboard
    
    TTS -.Response.-> UI
    Status -.배포 결과.-> Android

style Android fill:#e1f5ff
style Server fill:#fff3e0
style External fill:#f3e5f5
style TFLite fill:#ffebee
style NLG_A fill:#fffde7
style TTS fill:#e0f2f1
```

---

## 2️⃣ 1회 탐지 사이클 (시간 흐름)

```mermaid
sequenceDiagram
    participant A as Android<br/>카메라
    participant T as TFLite<br/>추론
    participant D as Depth<br/>거리
    participant N as NLG<br/>문장생성
    participant P as TTS<br/>음성
    participant UI as UI<br/>화면
    participant S as 서버<br/>FastAPI
    participant DB as DB<br/>저장
    
    rect rgb(200, 220, 255)
    Note over A,UI: 온디바이스 처리 (30fps, ~150ms)
    
    A->>A: 프레임 캡처<br/>(30ms)
    A->>T: 이미지 전달
    T->>T: YOLO 추론<br/>(29ms)
    
    alt 3-4프레임당 1회
        A->>D: Depth 실행<br/>(~70ms)
        D->>D: 거리 추정
    else 나머지 프레임
        D->>D: 스킵
    end
    
    T->>N: 탐지 결과
    N->>N: 문장 생성<br/>(5ms)
    N->>P: 문장 전달
    N->>UI: 텍스트 전달
    P->>P: TTS 렌더링<br/>(~100ms)
    UI->>UI: 화면 갱신<br/>(10ms)
    
    end
    
    rect rgb(255, 240, 200)
    Note over S,DB: 서버 연동 (선택) - ~300ms 지연
    
    A->>S: JSON 전송<br/>(/detect_json)
    Note over A,S: 네트워크 지연<br/>(150-200ms)
    S->>S: JSON 수신<br/>(20ms)
    S->>N: 서버 NLG<br/>재구성
    N->>S: 문장 응답
    S->>DB: DB 저장<br/>(50ms)
    S->>A: 응답 반환<br/>200 OK
    Note over S,A: 네트워크 지연<br/>(100-150ms)
    A->>UI: 결과 표시
    
    end
    
    Note over A,DB: 전체 왕복: ~300ms = 약 3.3fps<br/>실제: 6-7fps (비동기 + 버퍼링)
```

---

## 3️⃣ 4가지 사용 모드 흐름도

```mermaid
graph TD
    Start["🎙️ 사용자 음성 명령<br/>또는 자동 감지"]
    
    Start --> Mode{탐지 모드}
    
    Mode -->|"🚧 장애물 모드"| Obstacle["탐지 물체 분류<br/>위험도 계산<br/>거리/방향 확인"]
    Obstacle --> ObsNLG["3개 물체<br/>우선순위 정렬<br/>문장 생성"]
    ObsNLG --> ObsOut["12시 방향 1.5m<br/>앞에 의자가 있어요.<br/>조심해서 이동하세요."]
    
    Mode -->|"🔍 찾기 모드"| Find["'가방 찾아줘'<br/>→ 음성 인식<br/>→ 해당 클래스 필터"]
    Find --> FindNLG["탐지된 가방<br/>방향·거리 추출<br/>문장 생성"]
    FindNLG --> FindOut["3시 방향 2미터에<br/>가방이 있어요."]
    
    Mode -->|"❓ 확인 모드"| Question["'이거 뭐야?'<br/>→ 정면 가장 가까운<br/>물체 분류"]
    Question --> QuestNLG["단일 물체<br/>상세 설명<br/>문장 생성"]
    QuestNLG --> QuestOut["당신 앞에는<br/>노트북 컴퓨터가 있어요."]
    
    Mode -->|"👋 들고있는것 모드"| Held["손 앞 30cm 범위<br/>물체 탐지"]
    Held --> HeldNLG["근처 물체 확인<br/>문장 생성"]
    HeldNLG --> HeldOut["당신이 손에<br/>휴대폰을 들고 있어요."]
    
    ObsOut --> Decision{"서버 연동<br/>활성화?"}
    FindOut --> Decision
    QuestOut --> Decision
    HeldOut --> Decision
    
    Decision -->|"✅ Yes"| ServerSync["JSON 패킹<br/>/detect_json POST<br/>서버 검증 + DB 저장<br/>팀 위치 배포"]
    Decision -->|"❌ No"| LocalOnly["온디바이스만<br/>처리 완료"]
    
    ServerSync --> End["🔊 TTS 음성<br/>📺 UI 텍스트"]
    LocalOnly --> End
    
    style Obstacle fill:#ffebee
    style Find fill:#e8f5e9
    style Question fill:#fff3e0
    style Held fill:#f3e5f5
    style ServerSync fill:#e3f2fd
    style End fill:#c8e6c9
```

---

## 4️⃣ 성능 메트릭스: 현재 vs 목표

```mermaid
graph LR
    subgraph perf["성능 메트릭스 (현재 vs 목표)"]
        direction TB
        
        subgraph ondev["온디바이스 성능 ✅"]
            yolo["YOLO 추론<br/>29ms ✅<br/>(목표: <30ms)"]
            cap["카메라 캡처<br/>30fps ✅<br/>(목표: 30fps)"]
            nlg["NLG 생성<br/>5ms ✅<br/>(목표: <10ms)"]
            tts["TTS 렌더링<br/>100ms ✅<br/>(목표: <150ms)"]
        end
        
        subgraph server["서버 성능 ⚠️"]
            svr_fps["서버 FPS<br/>6-7fps ❌<br/>(목표: 10fps)"]
            resp["응답 시간<br/>~300ms ⚠️<br/>(목표: <200ms)"]
            latency["네트워크 지연<br/>150-200ms 🌐<br/>(제어 불가)"]
        end
        
        subgraph qual["품질 지표 ⚠️"]
            acc["탐지 정확도<br/>85-90% ⚠️<br/>(목표: >90%)"]
            sync["TTS-UI 동기화<br/>70% ⚠️<br/>(목표: 100%)"]
            flick["화면 깜빡임<br/>발생 중 ❌<br/>(목표: 0)"]
        end
    end
    
    yolo --> nvid_margin["병목 분석:<br/>서버가 제약"]
    cap --> nvid_margin
    nlg --> nvid_margin
    tts --> nvid_margin
    
    svr_fps --> improve["개선 필요:<br/>양자화<br/>배치 처리"]
    resp --> improve
    latency --> improve
    
    style ondev fill:#e8f5e9
    style server fill:#fff3e0
    style qual fill:#ffebee
    style improve fill:#fff9c4
```

---

## 📌 어디서 열어볼까?

### VS Code에서:
1. 마크다운 미리보기 (⌘K ⌘V)
2. 또는 [이 파일을 GitHub에 푸시](https://github.com)하면 자동 렌더링

### 온라인 렌더러:
- https://mermaid.live/
- 코드를 복사해서 붙여넣으면 실시간 렌더링 가능

### 더 자세히:
- [CURRENT_STATUS_REPORT.md](../CURRENT_STATUS_REPORT.md) - 상세 분석
- [SIMULATION_RESULTS.md](../SIMULATION_RESULTS.md) - 테스트 결과
