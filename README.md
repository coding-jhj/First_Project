# VoiceGuide — 시각장애인 보행 보조 앱

> KDT AI Human 3팀 | 프로젝트 기간 2026-04-24 ~ 2026-05-13

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
7. [API 명세](#api-명세)
8. [테스트 현황](#테스트-현황)
9. [알려진 이슈 및 개선 계획](#알려진-이슈-및-개선-계획)
10. [프로젝트 구조](#프로젝트-구조)

---

## 아키텍처

```
Android 앱 (Kotlin)
 └─ CameraX 캡처
     └─ yolo11n.onnx (ONNX Runtime, 온디바이스)
         └─ 탐지 결과 JSON
             ├─ SentenceBuilder (Android NLG) → TTS 즉시 발화
             └─ POST /detect → FastAPI (GCP Cloud Run)
                              ├─ Tracker 업데이트 (EMA 평활화)
                              ├─ DB 저장 (detection_events)
                              ├─ 대시보드 SSE 배포
                              └─ NLG 문장 → JSON 응답 → TTS 발화
```

**설계 원칙:**
- 서버는 이미지를 받지 않고 YOLO 추론을 수행하지 않는다
- 온디바이스 추론이 불가능하면 분석 자체를 하지 않는다 (서버 폴백 없음)
- 정책(`policy.json`)은 Android·서버가 공유하는 단일 진실 공급원(SSOT)

---

## 기능 목록

### 동작 확인된 기능

| 기능 | 트리거 | 설명 |
|---|---|---|
| 장애물 안내 | 자동 (연속 분석) | 위험도 상위 물체를 방향·거리와 함께 안내 |
| 차량 경고 | 자동 | 차량·오토바이·트럭 탐지 시 즉각 경보 (보팅 우선 통과) |
| 어두운 환경 감지 | 자동 | 조도 센서 10 lux 미만 → 주의 안내 |
| 공간 변화 감지 | 자동 | 이전 프레임 대비 새로 나타난 물체 안내 |
| 물건 찾기 | "X 찾아줘" | 탐지 결과 중 대상 물체 위치·방향 안내 |
| 질문 응답 | "앞에 뭐 있어?" | 3초간 프레임 수집 후 요약 발화 (1회) |
| 들고 있는 것 확인 | "이거 뭐야?" | 손 앞 가장 가까운 물체 안내 |
| 신호등 감지 | 신호등 모드 | 빨간불·초록불 HSV 분류 |
| 안전 경로 제안 | 자동 | 정면 위험 높을 때 좌/우 안전 방향 안내 |
| 장소 저장 | "저장" | 현재 위치(SSID·GPS) 이름 저장 |
| 낙상 감지 | 자동 | 가속도 자유낙하 후 충격 패턴 감지 |

### 실험 기능 (동작하나 정확도 개선 중)

- 계단 감지 (`StairsDetector.kt` 영상 패턴 기반)
- 거리 수치 안내 ("약 2미터" 형식)

---

## 기술 스택

| 영역 | 기술 |
|---|---|
| Android | Kotlin, CameraX, ONNX Runtime, OkHttp |
| 서버 | Python 3.10, FastAPI, Uvicorn |
| 비전 모델 | yolo11n.onnx (ONNX Runtime Android, 온디바이스) |
| NLG | 커스텀 한국어 문장 생성 (조사 자동화, policy.json SSOT) |
| TTS | Android 내장 TTS |
| STT | Android SpeechRecognizer |
| DB | SQLite (로컬) / PostgreSQL Supabase (Cloud Run) |
| 배포 | GCP Cloud Run (asia-northeast3, min-instances=1) |

---

## 서버 실행

### 로컬 실행

```bash
pip install -r requirements.txt
cp .env.example .env          # DATABASE_URL, API_KEY 선택 설정
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

서버 실행에 모델 파일이 필요하지 않습니다 (추론 없음).

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

1. Android Studio에서 `android/` 프로젝트 열기
2. `assets/yolo11n.onnx` 파일 확인 (온디바이스 추론용 필수)
3. 앱 실행 → 우상단 설정(⚙) → 서버 URL 입력
   - 비워두면 온디바이스 전용 모드 (서버 미연동)
   - 서버 URL 입력 시 탐지 JSON을 서버/대시보드/DB에 동기화
4. "▶ 분석 시작" 버튼 또는 음성으로 "시작"

---

## 음성 명령

| 말하는 내용 | 동작 |
|---|---|
| "시작" | 분석 시작 |
| "중지" | 분석 일시 중지 |
| "다시 시작" | 분석 재개 |
| "의자 찾아줘" | 찾기 모드 — 의자 위치 안내 |
| "앞에 뭐 있어?" | 3초간 프레임 수집 후 요약 안내 |
| "이거 뭐야?" | 들고있는것 모드 — 손 앞 물체 안내 |
| "신호등" | 신호등 감지 모드 |
| "다시 읽어줘" | 마지막 안내 문장 재발화 |
| "소리 크게 / 작게" | 볼륨 조절 |

---

## API 명세

### POST /detect

Android 온디바이스 YOLO 결과를 받아 세션 상태를 갱신하고 안내 문장을 반환합니다.  
서버는 이미지를 받거나 추론을 수행하지 않습니다.

**요청 필드:**

| 필드 | 타입 | 설명 |
|---|---|---|
| device_id | string | 기기별 고정 세션 ID |
| wifi_ssid | string | 공간 식별 보조 (선택) |
| mode | string | 장애물 / 찾기 / 질문 / 들고있는것 |
| camera_orientation | string | front / back / left / right |
| objects | array | 온디바이스 탐지 객체 목록 |
| client_perf | object | 앱 추론 시간 (ms) |

**요청 예시:**

```json
{
  "device_id": "android-a1b2c3d4",
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
  "client_perf": {"infer_ms": 22, "dedup_ms": 1}
}
```

**응답:**

```json
{
  "sentence": "12시 방향 가까이 자동차가 있어요. 위험해요!",
  "alert_mode": "critical",
  "objects": [{"class_ko": "자동차", "direction": "12시", "distance_m": 1.8}],
  "changes": ["사람이 생겼어요"],
  "process_ms": 12
}
```

**alert_mode 값:**

| 값 | Android 동작 |
|---|---|
| critical | 즉각 TTS (재생 중 끼어들기 가능) |
| normal | 일반 TTS (현재 발화 끝난 후) |
| beep | 진동만 (경고 피로 방지) |
| silent | 무음 (중복 억제) |

### GET /status/{session_id}

세션의 현재 탐지 상태·GPS·추적 이력 반환. 대시보드에서 사용.

### GET /events/{session_id}

Server-Sent Events(SSE) 스트림. 대시보드 실시간 업데이트용.

### GET /sessions

최근 활동 세션 ID 목록 반환 (GPS 없어도 detection_events 기반으로 보완).

### GET /dashboard

실시간 대시보드 HTML (세션 선택 → 탐지 물체·GPS 경로 표시).

---

## 테스트 현황

### 온디바이스 모드 (2026-05-06 기준)

| 항목 | 결과 |
|---|---|
| FPS | 10fps 이상 안정적 유지 |
| 사물 탐지 정확도 | 의자·사람·가방 등 주요 물체 정상 탐지 |
| 차량 탐지 | 정상 동작 확인 |
| TTS 발화 | 정상 |
| 질문 응답 (3초 요약) | 2026-05-06 전환 완료 |

### 서버 연동 모드 (2026-05-06 기준)

| 항목 | 결과 |
|---|---|
| JSON 수신 / NLG 문장 반환 | 정상 |
| 대시보드 물체 표시 | tracker _voting 버그 수정 후 정상화 |
| DB 저장 | 정상 |
| 서버 오류 응답 반복 | tracker 버그 수정으로 해결 |

---

## 알려진 이슈 및 개선 계획

| 이슈 | 상태 |
|---|---|
| 서버 추론 의존성 제거 | 완료 (2026-05-06) |
| tracker _voting 미초기화 → 매 요청 500 오류 | 수정 완료 (2026-05-06) |
| 대시보드 세션 목록 GPS 없으면 빈 문제 | 수정 완료 (2026-05-06) |
| 걸음감지 자동 트리거 → 진동만 울리고 음성 없음 | 제거 완료, 질문 시 3초 요약으로 전환 (2026-05-06) |
| 화면 텍스트 빠른 깜빡임 | 개선 필요 |
| yolo11n → 클래스 수 축소 파인튜닝 | 예정 |
| 거리 안내 이동 중 비활성화 검증 | 예정 |
| 음성 시나리오 케이스별 픽스 | 예정 |

---

## 프로젝트 구조

```
VoiceGuide/
├── src/
│   ├── api/
│   │   ├── main.py          # FastAPI 앱 진입점, 전역 예외 핸들러
│   │   ├── routes.py        # /detect /gps /status /events /sessions
│   │   ├── db.py            # 탐지 이벤트·세션·GPS·스냅샷 저장
│   │   ├── tracker.py       # EMA 평활화 + 보팅 + 접근 감지
│   │   └── events.py        # SSE 이벤트 발행/구독
│   ├── nlg/
│   │   └── sentence.py      # 한국어 안내 문장 생성 (조사 자동화)
│   └── config/
│       ├── policy.json      # Android·서버 공통 정책 SSOT
│       └── policy.py        # 정책 로더 (ETag 캐싱 포함)
├── android/
│   └── app/src/main/java/com/voiceguide/
│       ├── MainActivity.kt        # 카메라·STT·TTS·서버 연동 총괄
│       ├── YoloDetector.kt        # ONNX Runtime 온디바이스 추론
│       ├── MvpPipeline.kt         # 위험도 계산·진동 패턴 결정
│       ├── SentenceBuilder.kt     # 온디바이스 NLG
│       ├── VoiceGuideConstants.kt # COCO 클래스 한국어 매핑·상수
│       ├── VoicePolicy.kt         # 서버 정책 동기화 클라이언트
│       ├── BoundingBoxOverlay.kt  # 디버그용 bbox 오버레이
│       └── StairsDetector.kt      # 계단 전용 탐지기
├── templates/
│   └── dashboard.html       # 실시간 세션 대시보드 (SSE 기반)
├── docs/                    # 날짜별 개발 일지
├── tools/                   # 모델 내보내기·서버 점검·테스트 도구
├── tests/                   # pytest 단위 테스트
├── Dockerfile               # GCP Cloud Run 배포용 (추론 관련 패키지 제외)
├── .gcloudignore            # gcloud 업로드 필터
└── requirements.txt
```

---

## 팀

KDT AI Human 3팀 (2026-04-24 ~ 2026-05-13)  
GitHub: https://github.com/coding-jhj/VoiceGuide  
서버: https://voiceguide-1063164560758.asia-northeast3.run.app
