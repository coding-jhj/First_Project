# VoiceGuide — 시각장애인 보행 보조 앱

> KDT AI Human 3팀 | 프로젝트 기간 2026-04-24 ~ 2026-05-13  
> 최종 업데이트: 2026-05-07

실시간 카메라 영상으로 주변 장애물·위험 요소를 탐지하고 한국어 음성으로 안내하는 Android 앱입니다.  
YOLO 추론은 Android 온디바이스에서 수행하고, 서버(GCP Cloud Run)는 탐지 결과 JSON 수신·세션 상태 배포·DB 저장만 담당합니다.

---

## 목차

1. [아키텍처](#아키텍처)
2. [기능 목록](#기능-목록)
3. [기술 스택](#기술-스택)
4. [서버 실행](#서버-실행)
5. [Android 앱 실행](#android-앱-실행)
6. [음성 명령](#음성-명령)
7. [온디바이스 추론 모델](#온디바이스-추론-모델)
8. [API 명세](#api-명세)
9. [프로젝트 구조](#프로젝트-구조)
10. [테스트 현황](#테스트-현황)

---

## 아키텍처

```
Android 앱 (Kotlin)
 └─ CameraX 캡처
     └─ TfliteYoloDetector (yolo11n_320.tflite, 온디바이스)
         └─ MvpPipeline (트래킹 · 위험도 계산 · 진동)
             └─ SentenceBuilder (한국어 문장 생성)
                 └─ Android TTS 발화
                     │
                     └─ POST /detect (JSON만 전송, 이미지 없음)
                             │
                         FastAPI (GCP Cloud Run)
                          ├─ Tracker 업데이트 (EMA 평활화)
                          ├─ SQLite / PostgreSQL 저장
                          ├─ 대시보드 SSE 배포
                          └─ NLG 안내 문장 반환
```

**설계 원칙:**
- 서버는 이미지를 받지 않고 YOLO 추론을 수행하지 않는다
- 온디바이스 추론이 불가능하면 분석 자체를 하지 않는다 (서버 폴백 없음)
- 정책(`policy.json`)은 Android·서버가 공유하는 단일 진실 공급원(SSOT)
- 인터넷 없이도 기본 탐지·안내 동작 (오프라인 모드)

---

## 기능 목록

| 기능 | 트리거 | 설명 |
|---|---|---|
| 장애물 안내 | 자동 (연속 분석) | 위험도 상위 물체를 방향·거리와 함께 안내 |
| 차량 경고 | 자동 | 차량·버스·트럭 탐지 시 즉각 경보 |
| 물건 찾기 | "X 찾아줘" | 탐지 결과 중 대상 물체 위치·방향 안내 |
| 질문 응답 | "앞에 뭐 있어?" | 현재 탐지 상태 요약 발화 |
| 들고있는 것 확인 | "이거 뭐야?" | 손 앞 가장 가까운 물체 안내 |
| 신호등 모드 | "신호등" | 신호등 색상 탐지 및 횡단 안내 |
| 분석 중지/재개 | "잠깐" / "다시 시작" | 음성으로 분석 제어 |

---

## 기술 스택

| 영역 | 기술 | 비고 |
|---|---|---|
| Android | Kotlin 1.9, CameraX 1.3.1 | minSdk 26 |
| 온디바이스 추론 | TensorFlow Lite 2.17.0 | GPU Delegate → XNNPACK 자동 폴백 |
| 비전 모델 | yolo11n_320.tflite (2.8 MB) | COCO 80클래스, 320×320 |
| NLG | 커스텀 한국어 문장 생성 | 조사 자동화, policy.json SSOT |
| TTS / STT | Android 내장 TTS / SpeechRecognizer | |
| 백엔드 | Python 3.10, FastAPI 0.115.5 | |
| DB | SQLite (기본) / PostgreSQL Supabase | |
| 배포 | GCP Cloud Run (asia-northeast3) | |
| 테스트 | pytest, httpx | |

---

## 서버 실행

### 로컬 실행

```bash
pip install -r requirements.txt
cp .env.example .env      # DATABASE_URL, ELEVENLABS_API_KEY 선택 설정
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

서버 실행에 ML 모델 파일이 필요하지 않습니다 (추론 없음).

### GCP Cloud Run 배포

```bash
gcloud run deploy voiceguide \
  --source . \
  --region asia-northeast3 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 120 \
  --allow-unauthenticated \
  --port 8080
```

### 서버 상태 확인

```
GET /health
→ {"status":"ok","role":"json-router","inference":"disabled","db":"ok"}
```

---

## Android 앱 실행

1. Android Studio에서 `android/` 폴더 열기
2. Gradle Sync 실행 (🐘 아이콘 클릭)
3. USB로 Android 기기 연결 (USB 디버깅 활성화)
4. **Run** (Shift+F10)
5. 앱 실행 후 우상단 설정(⚙) → 서버 URL 입력
   - 비워두면 온디바이스 전용 모드 (서버 미연동)
   - 서버 URL 입력 시 탐지 JSON을 서버·대시보드·DB에 동기화

**Logcat 필터:**

| 태그 | 내용 |
|---|---|
| `VG_PERF` | 추론 시간, FPS, 모델명, GPU/CPU 여부 |
| `VG_DETECT` | 탐지된 물체 목록 (클래스, 신뢰도, 위치) |
| `VG_FLOW` | 요청 라우팅, 서버 연동 상태 |

---

## 음성 명령

| 말하는 내용 | 동작 |
|---|---|
| "시작" / "재개" | 분석 시작 |
| "잠깐" / "멈춰" | 분석 일시 중지 |
| "다시 시작" | 분석 재개 |
| "의자 찾아줘" | 찾기 모드 — 의자 위치 안내 |
| "앞에 뭐 있어?" | 현재 탐지 상태 요약 안내 |
| "이거 뭐야?" | 들고있는것 모드 — 손 앞 물체 안내 |
| "신호등" | 신호등 탐지 모드 |

---

## 온디바이스 추론 모델

앱은 `assets/` 폴더에서 아래 순서로 첫 번째 존재하는 파일을 자동 선택합니다.

```
우선순위: yolo11n_320.tflite → yolo26n_float32.tflite
```

| 파일 | 입력 | 출력 | 크기 | 비고 |
|---|---|---|---|---|
| `yolo11n_320.tflite` | 320×320 | `[1, 84, 2100]` raw | 2.8 MB | 강사님 파인튜닝, 현재 기본값 |
| `yolo26n_float32.tflite` | 320×320 | `[1, 300, 6]` NMS 내장 | 9.8 MB | 폴백용 |

**출력 형식 자동 감지:** `outputRows == 84` 이면 raw 후처리(`postProcessRaw`), 그 외는 NMS 내장 후처리(`postProcessEndToEnd`) 자동 적용.

**성능 지표 (Pixel 6 기준):**

| 항목 | yolo11n_320 |
|---|---|
| GPU 추론 시간 | ~20~35ms |
| CPU(XNNPACK) 추론 시간 | ~60~90ms |
| 전체 FPS | 10fps 이상 |

---

## API 명세

### POST /detect

Android 온디바이스 YOLO 결과를 받아 세션 상태를 갱신하고 안내 문장을 반환합니다.

**요청 예시:**

```json
{
  "device_id": "android-a1b2c3d4",
  "wifi_ssid": "office",
  "mode": "장애물",
  "objects": [
    {
      "class_ko": "자동차",
      "confidence": 0.87,
      "bbox_norm_xywh": [0.5, 0.6, 0.3, 0.2],
      "depth_source": "on_device_bbox"
    }
  ],
  "client_perf": {"infer_ms": 28, "dedup_ms": 2}
}
```

**응답 예시:**

```json
{
  "sentence": "12시 방향 가까이 자동차가 있어요. 위험해요!",
  "alert_mode": "critical",
  "objects": [{"class_ko": "자동차", "direction": "12시", "distance_m": 1.8}],
  "process_ms": 11
}
```

**alert_mode 값:**

| 값 | 동작 |
|---|---|
| `critical` | 즉각 TTS (진행 중 발화 끊고 재생) |
| `normal` | 일반 TTS (현재 발화 끝난 후) |
| `beep` | 진동만 (알림 피로 방지) |
| `silent` | 무음 (중복 억제) |

### GET /dashboard

실시간 대시보드 HTML. 세션별 탐지 물체·타임라인 시각화.

### GET /events/{session_id}

Server-Sent Events(SSE) 스트림. 대시보드 실시간 업데이트용.

### GET /health

서버 상태 및 DB 연결 확인.

---

## 프로젝트 구조

```
VoiceGuide/
├── android/
│   └── app/src/main/
│       ├── java/com/voiceguide/
│       │   ├── MainActivity.kt          # 카메라·STT·TTS·서버 연동 총괄
│       │   ├── TfliteYoloDetector.kt    # TFLite 온디바이스 추론 엔진
│       │   ├── MvpPipeline.kt           # 트래킹·위험도·진동 패턴 결정
│       │   ├── SentenceBuilder.kt       # 한국어 안내 문장 생성
│       │   ├── VoiceGuideConstants.kt   # COCO 클래스 한국어 매핑·상수
│       │   ├── VoicePolicy.kt           # policy.json 파싱 및 정책 적용
│       │   ├── BoundingBoxOverlay.kt    # 디버그용 바운딩박스 오버레이
│       │   └── Detection.kt             # 탐지 결과 데이터 클래스
│       └── assets/
│           ├── yolo11n_320.tflite       # 기본 추론 모델 (2.8 MB)
│           ├── yolo26n_float32.tflite   # 폴백 모델 (9.8 MB)
│           └── policy_default.json      # 탐지 정책 기본값
│
├── src/
│   ├── api/
│   │   ├── main.py          # FastAPI 앱 진입점
│   │   ├── routes.py        # /detect /status /events /sessions /health
│   │   ├── db.py            # 탐지 이벤트·세션·GPS 저장
│   │   ├── tracker.py       # EMA 평활화 + 보팅 + 접근 감지
│   │   └── events.py        # SSE 이벤트 발행/구독
│   ├── nlg/
│   │   └── sentence.py      # 한국어 안내 문장 생성
│   └── config/
│       ├── policy.json      # Android·서버 공통 정책 SSOT
│       └── policy.py        # 정책 로더
│
├── templates/
│   └── dashboard.html       # 실시간 세션 대시보드
├── tests/                   # pytest 단위 테스트
├── tools/                   # 모델 내보내기·서버 점검 도구
├── docs/                    # 날짜별 개발 일지
├── Dockerfile               # GCP Cloud Run 배포용
└── requirements.txt
```

---

## 테스트 현황

### 온디바이스 모드 (2026-05-07 기준)

| 항목 | 결과 |
|---|---|
| FPS | 10fps 이상 안정 |
| 주요 물체 탐지 | 의자·사람·가방·자동차 정상 |
| GPU Delegate | 지원 기기에서 자동 적용 |
| TTS 발화 | 정상 |

### 서버 연동 모드 (2026-05-07 기준)

| 항목 | 결과 |
|---|---|
| JSON 수신 / NLG 문장 반환 | 정상 |
| 대시보드 SSE 업데이트 | 정상 |
| DB 저장 | 정상 |

---

## 팀

KDT AI Human 3팀 (2026-04-24 ~ 2026-05-13)  
GitHub: https://github.com/coding-jhj/VoiceGuide  
서버: https://voiceguide-1063164560758.asia-northeast3.run.app
