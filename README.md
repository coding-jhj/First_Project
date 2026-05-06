# VoiceGuide — 시각장애인 보행 보조 앱

> KDT AI Human 3팀 | 프로젝트 기간 2026-04-24 ~ 2026-05-13

실시간 카메라 영상으로 주변 장애물·위험 요소를 탐지하고 한국어 음성으로 안내하는 Android 앱입니다.  
YOLO 추론과 이미지 분석은 Android 온디바이스에서 수행하고, 서버(GCP Cloud Run)는 탐지 결과 JSON 수신·디바이스별 상태 배포·DB 저장을 담당합니다.

---

## 목차

1. [아키텍처](#아키텍처)
2. [기능 목록](#기능-목록)
3. [기술 스택](#기술-스택)
4. [서버 실행](#서버-실행)
5. [Android 앱 실행](#android-앱-실행)
6. [API 명세](#api-명세)
7. [모델 설명](#모델-설명)
8. [테스트 현황](#테스트-현황)
9. [알려진 이슈 및 개선 계획](#알려진-이슈-및-개선-계획)
10. [프로젝트 구조](#프로젝트-구조)

---

## 아키텍처

```
Android 앱 (Kotlin)
 └─ CameraX 캡처 → yolo11n.onnx (ONNX Runtime) → 탐지 결과 JSON
          ↓
     FastAPI (GCP Cloud Run)
      ├─ JSON 검증/정규화
      ├─ device_id별 최신 결과 배포 (/status/{device_id})
      ├─ DB 저장 (detection_events, detections)
      └─ NLG (sentence.py) → JSON 응답 → Android TTS 재생
```

- **온디바이스**: 서버 없이도 폰 단독 탐지 가능. 배터리·발열 고려해 프레임 수 제어
- **서버 연동**: 이미지 업로드 없이 탐지 JSON만 전송해 대시보드, 팀 위치, DB 기록에 반영
- **정책 SSOT**: `policy.json` 1개로 Android·서버 NLG 규칙 동기화 (`GET /api/policy`)

---

## 기능 목록

### 동작 확인된 기능

| 기능 | 모드 키워드 | 설명 |
|---|---|---|
| 장애물 안내 | 장애물 | 위험도 상위 3개 물체를 방향·거리와 함께 안내 |
| 물건 찾기 | 찾기 | "가방 찾아줘" → 탐지된 물체 중 해당 물체 위치 안내 |
| 물건 확인 | 확인/질문 | "이거 뭐야?" → 앞에 있는 물체 설명 |
| 들고 있는 것 확인 | 들고있는것 | 손 앞 가까운 물체 안내 |
| 차량 경고 | 자동 | 자동차·오토바이·트럭 탐지 시 즉각 경보 |
| 군중 경고 | 자동 | 사람 5명 이상 탐지 시 혼잡 안내 |
| 신호등 색 감지 | 자동 | 빨간불/초록불 HSV 색공간 분류 |
| 안전 경로 제안 | 자동 | 정면 위험 높을 때 좌/우 안전 방향 안내 |
| 공간 기억 | 자동 | 이전 프레임과 비교해 새로 나타난 물체 안내 |
| 어두운 환경 감지 | 자동 | 조도 센서로 어두움 감지 후 주의 안내 |
| 장소 저장/검색 | 저장/위치목록 | GPS 기반 장소 이름 저장 및 목록 조회 |

### 실험 기능 (동작하나 정확도 개선 중)

- 계단 감지 (`StairsDetector.kt` 전용 ONNX 모델)
- 거리 수치 안내 ("약 2미터" 형식)
- 점자 블록 경로 위 장애물 감지
- 바닥 위험 감지 (Depth 맵 기반 좁은 통로·울퉁불퉁한 바닥)

### 예정 기능

옷 색상 매칭, 낙상 감지, 약 알림, 버스 OCR, 하차 알림, 바코드 인식

---

## 기술 스택

| 영역 | 기술 |
|---|---|
| Android | Kotlin, CameraX, ONNX Runtime, OkHttp |
| 서버 | Python 3.10, FastAPI, Uvicorn |
| 비전 | Android ONNX Runtime 기반 YOLOv11n |
| NLG | 커스텀 한국어 문장 생성 (조사 자동화 포함) |
| TTS | Android 내장 TTS / ElevenLabs (고품질) |
| STT | Android SpeechRecognizer |
| DB | SQLite (로컬) / PostgreSQL (Supabase, LTE 환경) |
| 배포 | GCP Cloud Run (asia-northeast3) |

---

## 서버 실행

### 로컬 실행

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경 변수 설정
cp .env.example .env
# 선택: DATABASE_URL, API_KEY, ALLOWED_ORIGINS 설정

# 3. 서버 시작
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

서버 실행에는 YOLO/Depth 모델 파일이 필요하지 않습니다.

### GCP Cloud Run 배포

```bash
gcloud run deploy voiceguide \
  --source . \
  --project [PROJECT_ID] \
  --region asia-northeast3 \
  --allow-unauthenticated
```

Cloud Run 서버 이미지는 Torch/Ultralytics/OpenCV 없이 JSON 라우터 중심으로 빌드됩니다.

### 서버 상태 확인

```
GET /health
→ {"status":"ok", "role":"json-router", "inference":"disabled", "db":"ok"}
```

---

## Android 앱 실행

1. Android Studio에서 `android/` 프로젝트 열기
2. `assets/yolo11n.onnx` 파일 확인 (온디바이스 추론용)
3. 앱 실행 후 우상단 설정(⚙) → 서버 URL 입력
   - 비워두면 온디바이스 전용 모드
   - 서버 URL 입력 시 탐지 JSON을 서버 DB/대시보드에 동기화
4. "▶ 분석 시작" 버튼 또는 음성으로 "시작"

**음성 명령 예시:**

| 말하는 내용 | 동작 |
|---|---|
| "의자 찾아줘" | 찾기 모드 — 의자 탐지 후 위치 안내 |
| "이거 뭐야?" | 확인 모드 — 앞 물체 설명 |
| "중지" | 분석 중지 |
| "다시 시작" | 분석 재개 |

---

## API 명세

### POST /detect

Android 온디바이스 YOLO 결과 JSON을 받아 세션별 상태를 갱신하고, 필요 시 DB에 저장한 뒤 안내 문장을 반환합니다. 서버는 이미지를 받거나 YOLO/Depth 추론을 수행하지 않습니다.

**요청 (application/json):**

| 필드 | 타입 | 설명 |
|---|---|---|
| event_id | string | 탐지 이벤트 ID |
| request_id | string | 요청 추적 ID |
| mode | string | 장애물 / 찾기 / 질문 / 들고있는것 |
| device_id | string | 세션 식별자 |
| wifi_ssid | string | 선택: 공간 식별 보조값 |
| camera_orientation | string | front / back / left / right |
| query_text | string | 찾기 모드에서 탐색할 물체명 |
| objects | array | 온디바이스 탐지 객체 목록 |
| client_perf | object | 앱 추론/후처리 시간 |

**요청 예시:**

```json
{
  "event_id": "and-1778050000000-1",
  "request_id": "and-1778050000000-1",
  "device_id": "device-a",
  "wifi_ssid": "office",
  "mode": "장애물",
  "camera_orientation": "front",
  "objects": [
    {
      "class_ko": "의자",
      "confidence": 0.91,
      "bbox_norm_xywh": [0.4, 0.45, 0.2, 0.25],
      "depth_source": "on_device_bbox"
    }
  ],
  "client_perf": {"infer_ms": 18, "dedup_ms": 1}
}
```

**응답:**

```json
{
  "sentence": "12시 방향 가까이 자동차가 있어요. 위험해요!",
  "alert_mode": "critical",
  "objects": [{"class_ko": "자동차", "direction": "12시", "distance_m": 1.8}],
  "hazards": [],
  "changes": ["사람이 생겼어요"],
  "process_ms": 85,
  "perf": {"detect_ms": 60, "tracker_ms": 2, "nlg_ms": 3}
}
```

**alert_mode 의미:**

| 값 | 동작 |
|---|---|
| critical | 즉각 TTS 재생 (재생 중 끼어들기 가능) |
| beep | 비프음 (경고 피로 방지) |
| silent | 무음 (중복 억제, 2.5초 이내 동일 문장) |

---

## 모델 설명

### 서버 역할

- JSON 수신: Android가 온디바이스에서 만든 탐지 결과를 `/detect`로 전송
- 디바이스별 상태 배포: `/status/{device_id}`, `/sessions`, `/team-locations`에서 최신 결과 조회
- DB 저장: `detection_events`에 원본 JSON, `detections`에 개별 객체 행 저장
- 금지: 서버 YOLO 추론, Depth 추론, 이미지 분석, 이미지 업로드 처리

### yolo11n.onnx (온디바이스)

- 기반: YOLOv11n, ONNX 변환
- 폰 단독 실행 (ONNX Runtime Android)
- 투표(Voting) 필터: 3프레임 중 2회 이상 탐지된 물체만 안내 (오탐 방지)

---

## 테스트 현황

> 테스트 기간: 2026-05-05 기준 실기기 테스트 진행 중 (데이터 축적 중)

### 온디바이스 모드

| 항목 | 결과 |
|---|---|
| FPS | 안정적 (목표 10fps 이상 충족) |
| 사물 탐지 정확도 | 양호 — 의자·사람·가방 등 주요 사물 정상 탐지 |
| 차량 탐지 | 정상 동작 확인 |
| TTS 안내 | 정상 발화 |

### 서버 연동 모드

| 항목 | 결과 |
|---|---|
| 서버 처리 FPS | 6~7 FPS (목표 10fps 미달, 개선 진행 중) |
| 차량 탐지 | 정상 동작 확인 |
| Depth 거리 추정 | bbox 대비 정밀도 향상 확인 |
| TTS·화면 텍스트 동기화 | 불일치 발생 → 2026-05-05 수정 완료 |
| 화면 텍스트 안정성 | 빠른 깜빡임 현상 — 개선 진행 중 |

### 음성 명령 인식

| 명령 | 결과 |
|---|---|
| "중지" / "다시 시작" | 정상 인식 |
| "찾아줘" 계열 | 조용한 환경에서 양호 |
| "이거 뭐야" | 조용한 환경에서 양호 |

---

## 알려진 이슈 및 개선 계획

| 이슈 | 상태 |
|---|---|
| 온디바이스 FPS 안정화 | 개선 중 — 프레임 수 제어·후처리 경량화 적용 |
| 화면 큰 글씨 "분석중" 고정 | 수정 완료 (2026-05-05) |
| 다음 장애물 안내 지연 | 수정 완료 — dedup 시간 5초→2.5초 단축 |
| 화면 텍스트 빠른 깜빡임 | 개선 필요 |
| TTS 음성과 화면 텍스트 불일치 | 개선 필요 |
| 서버 이미지 추론 의존성 | 제거 완료 — JSON 라우터 구조로 전환 |

---

## 프로젝트 구조

```
VoiceGuide/
├── src/
│   ├── api/
│   │   ├── main.py          # FastAPI 앱 진입점
│   │   ├── routes.py        # /detect JSON /tts /gps 등 엔드포인트
│   │   ├── db.py            # 탐지 이벤트·세션·GPS 저장
│   │   └── tracker.py       # 세션별 물체 이동 추적
│   ├── vision/
│   │   └── detect.py        # 로컬/실험용 YOLO 탐지 코드 (서버 런타임 미사용)
│   ├── depth/
│   │   ├── depth.py         # 로컬/실험용 Depth 코드 (서버 런타임 미사용)
│   │   └── hazard.py        # 로컬/실험용 바닥 위험 감지
│   ├── nlg/
│   │   ├── sentence.py      # 한국어 안내 문장 생성
│   │   └── templates.py     # 방향·거리 표현 템플릿
│   ├── voice/
│   │   ├── tts.py           # gTTS / ElevenLabs TTS
│   │   └── stt.py           # Google STT (로컬 데모용)
│   └── config/
│       ├── policy.json      # Android·서버 공통 정책 (SSOT)
│       └── policy.py        # 정책 로더
├── android/
│   └── app/src/main/java/com/voiceguide/
│       ├── MainActivity.kt        # 카메라·STT·TTS·서버 연동 총괄
│       ├── YoloDetector.kt        # ONNX Runtime 온디바이스 추론
│       ├── SentenceBuilder.kt     # 온디바이스 NLG
│       ├── VoiceGuideConstants.kt # COCO 클래스 한국어 매핑·상수
│       ├── VoicePolicy.kt         # 서버 정책 동기화 클라이언트
│       ├── BoundingBoxOverlay.kt  # 디버그용 bbox 오버레이
│       └── StairsDetector.kt      # 계단 전용 탐지기
├── depth_anything_v2/        # 로컬 실험용 Depth Anything V2 모델 코드
├── templates/
│   └── dashboard.html        # 실시간 세션 대시보드
├── tools/                    # 캘리브레이션·벤치마크 스크립트
├── train/                    # 파인튜닝 스크립트
├── tests/                    # pytest 단위 테스트
├── Dockerfile                # GCP Cloud Run 배포용
├── .gcloudignore             # gcloud 업로드 필터
└── requirements.txt
```

---

## 팀

KDT AI Human 3팀 (2026-04-24 ~ 2026-05-13)  
GitHub: https://github.com/coding-jhj/VoiceGuide  
서버: https://voiceguide-1063164560758.asia-northeast3.run.app
