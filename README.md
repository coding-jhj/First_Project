# VoiceGuide — 시각장애인 보행 보조 앱

> KDT AI Human 3팀 | 프로젝트 기간 2026-04-24 ~ 2026-05-13  
> 최종 업데이트: 2026-05-08

보호자 없이 혼자 이동하는 시각장애인을 위한 Android 온디바이스 보행 보조 앱입니다.  
카메라로 주변 장애물·위험 요소를 탐지하고 진동·음성으로 즉시 안내합니다.  
모든 추론과 위험 판단은 Android 로컬에서 처리하며, 서버는 로그 저장·분석 전용입니다.

---

## 목차

1. [아키텍처](#아키텍처)
2. [MVP 파이프라인](#mvp-파이프라인)
3. [진동 패턴](#진동-패턴)
4. [위험도 계산](#위험도-계산)
5. [기능 목록](#기능-목록)
6. [기술 스택](#기술-스택)
7. [서버 실행](#서버-실행)
8. [Android 앱 실행](#android-앱-실행)
9. [음성 명령](#음성-명령)
10. [온디바이스 추론 모델](#온디바이스-추론-모델)
11. [API 명세](#api-명세)
12. [구현 현황](#구현-현황)
13. [프로젝트 구조](#프로젝트-구조)

---

## 아키텍처

```
Android (로컬 — 네트워크 무관)
 └─ CameraX 캡처
     └─ YoloDetector (yolo11n_320.tflite, 온디바이스)
         └─ 보팅 필터 (WINDOW=3, 중 2회 이상)
             └─ MvpPipeline (BBox Tracking · EMA · 위험도 계산)
                 ├─ 진동 패턴 즉시 출력  ← 긴급 경고 경로 (오프라인 가능)
                 └─ SentenceBuilder → Android TTS 발화
                         │
                         └─ POST /detect_json (비동기, 후처리용)
                                 │
                             FastAPI (GCP Cloud Run)
                              ├─ 로그 저장 (SQLite / PostgreSQL)
                              ├─ 대시보드 SSE 배포
                              └─ 보호자 모니터링용 데이터 수집
```

**설계 원칙:**

| 역할 | 담당 |
|---|---|
| 긴급 경고 (진동·음성) | Android 로컬 — 네트워크 없어도 즉시 동작 |
| 추론 / 트래킹 / 위험도 계산 | Android 로컬 |
| 로그 저장 / 분석 / 모니터링 | 서버 (비동기, 경고 경로 밖) |

서버를 실시간 경고 판단 경로에 끼우면 네트워크 지연이 생명 안전에 직결된다.  
서버는 이미지를 받지 않고 YOLO 추론을 수행하지 않는다 (`/detect` → 410 Gone).

---

## MVP 파이프라인

```
YOLO11n 탐지
    ↓
보팅 필터 (오탐 억제)
    ↓
BBox Tracking (IoU 매칭)
    ↓
EMA 평활화 (흔들림 제거)
    ↓
위험도 계산
    ↓
진동 패턴 출력
```

### 보팅(Voting) 흐름

```
rawDetections
  → removeDuplicates()   // IoU 0.3 이상 중복 bbox 제거
  → voteOnly()           // WINDOW=3 중 2회 이상 = 확정
  → MvpPipeline.update() // 트래킹 + EMA + 위험도 계산
```

`voteBypassKo` 목록(계단, 차량 등)은 보팅 없이 즉시 통과합니다.

### BBox Tracking 파라미터

| 파라미터 | 값 | 설명 |
|---|---|---|
| `IOU_MATCH_THRESHOLD` | 0.25 | 동일 트랙으로 판정하는 최소 IoU |
| `MAX_MISSED_FRAMES` | 12 | 이 프레임 수 이상 미탐지 시 트랙 삭제 |
| `EMA_ALPHA` | 0.55 | 현재 55% + 이전 45% — 흔들림 vs 반응 균형 |

EMA 적용 대상: `cx`, `cy`, `w`, `h`, `distanceM`, `riskScore`

---

## 진동 패턴

오경고가 많으면 사용자가 신뢰를 잃고 앱을 끈다. 진동 피로 최소화가 핵심이다.

| 위험도 | 거리 / 조건 | 진동 패턴 |
|---|---|---|
| 낮음 | 2.5 ~ 4m 전방 객체 | 짧게 1번 |
| 중간 | 1.5 ~ 2.5m, 중앙 근처 | 짧게 2번 |
| 높음 | 1 ~ 1.5m, 접근 중 | 빠르게 3번 |
| 긴급 | 1m 이하 | 길고 강하게 반복 |

```kotlin
// MvpPipeline.kt
risk >= 0.75f → URGENT   // 길고 강하게
risk >= 0.55f → DOUBLE   // 짧게 2번
risk >= 0.35f → SHORT    // 짧게 1번
else          → NONE
```

차량 클래스(`vehicleKo`)는 `risk >= 0.55f`부터 즉시 URGENT로 상향됩니다.

---

## 위험도 계산

```kotlin
risk = centerWeight × distanceWeight × classWeight + sizeBoost
```

| 요소 | 설명 |
|---|---|
| `centerWeight` | 화면 중앙에 가까울수록 높음 (cx 기준) |
| `distanceWeight` | 거리가 가까울수록 높음 (0.8m 이하 = 1.0) |
| `classWeight` | 차량·위험 클래스 가중치 높음 (차량 = 1.0) |
| `sizeBoost` | bbox 면적이 클수록 추가 가산 |

거리는 현재 bbox 면적 기반으로 추정합니다 (FastDepth 교체 예정):

```kotlin
distanceM = sqrt(BBOX_CALIB_AREA / area)   // BBOX_CALIB_AREA = 0.06f
```

---

## 기능 목록

| 기능 | 트리거 | 설명 |
|---|---|---|
| 장애물 진동 경고 | 자동 | 위험도 기반 진동 패턴 즉시 출력 |
| 장애물 음성 안내 | 자동 | 위험 물체를 방향·거리와 함께 TTS 안내 |
| 차량 긴급 경보 | 자동 | 차량·버스·트럭 탐지 시 URGENT 진동 |
| 물건 찾기 | "X 찾아줘" | 탐지된 물체 중 대상 위치·방향 안내 |
| 질문 응답 | "앞에 뭐 있어?" | 현재 탐지 상태 요약 발화 |
| 들고있는 것 확인 | "이거 뭐야?" | 손 앞 가장 가까운 물체 안내 |
| 분석 중지 | "잠깐" / "멈춰" | 음성으로 분석 일시 중지 |
| 분석 재개 | "다시 시작" | 음성으로 분석 재개 |
| 마지막 안내 재발화 | "다시 읽어줘" | 직전 안내 문장 재발화 |
| 볼륨 조절 | "소리 크게/작게" | 음성 안내 볼륨 조절 |

---

## 기술 스택

| 영역 | 기술 | 비고 |
|---|---|---|
| Android | Kotlin 1.9, CameraX 1.3.1 | minSdk 26 |
| 온디바이스 추론 | TensorFlow Lite 2.17.0 | GPU Delegate → XNNPACK 자동 폴백 |
| 비전 모델 | yolo11n_320.tflite (2.8 MB) | 강사님 파인튜닝, n클래스 축소 |
| TTS / STT | Android 내장 TTS / SpeechRecognizer | |
| 진동 | Android Vibrator API | 패턴 계산 완료, HW 출력 연동 예정 |
| HTTP | OkHttp 4.12.0 | 비동기 JSON 전송 |
| 백엔드 | Python 3.10, FastAPI 0.115.5 | 추론 없음, JSON 수신·저장 전용 |
| DB | SQLite (기본) / PostgreSQL Supabase | |
| 배포 | GCP Cloud Run (asia-northeast3) | |
| 테스트 | pytest, httpx | |

---

## 서버 실행

### 로컬 실행

```bash
pip install -r requirements.txt
cp .env.example .env      # DATABASE_URL 등 설정
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

서버에 ML 모델 파일이 필요하지 않습니다 (추론 없음).

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
2. Gradle Sync 실행 (🐘 아이콘)
3. USB로 Android 기기 연결 (USB 디버깅 활성화)
4. **Run** (`Shift+F10`)
5. 앱 실행 후 설정(⚙) → 서버 URL 입력
   - 비워두면 온디바이스 전용 모드 (오프라인 완전 동작)
   - 서버 URL 입력 시 탐지 JSON을 서버·DB에 비동기 전송

**Logcat 필터:**

| 태그 | 내용 |
|---|---|
| `VG_PERF` | 추론 시간, FPS, 모델명, GPU/CPU 여부 |
| `VG_DETECT` | 탐지된 물체 목록 (클래스, 신뢰도, 위치) |
| `VG_FLOW` | 요청 라우팅, 서버 연동 상태 |

---

## 음성 명령

| 예시 발화 | 동작 |
|---|---|
| "잠깐", "멈춰", "그만해" | 분석 일시 중지 |
| "다시 시작", "계속해줘" | 분석 재개 |
| "의자 찾아줘", "어디 있어" | 찾기 모드 — 대상 물체 위치 안내 |
| "앞에 뭐 있어", "지금 어때" | 현재 탐지 상태 요약 안내 |
| "이거 뭐야", "손에 든 게 뭐야" | 손 앞 물체 안내 |
| "다시 읽어줘" | 마지막 안내 문장 재발화 |
| "소리 크게", "소리 작게" | 볼륨 조절 |

---

## 온디바이스 추론 모델

앱은 `assets/` 폴더에서 아래 순서로 첫 번째 존재하는 파일을 자동 선택합니다.

```
우선순위: yolo11n_320.tflite → yolo26n_float32.tflite
```

| 파일 | 입력 크기 | 출력 shape | 크기 | 비고 |
|---|---|---|---|---|
| `yolo11n_320.tflite` | 320×320 | `[1, 84, 2100]` raw | 2.8 MB | 강사님 파인튜닝, 현재 기본값 |
| `yolo26n_float32.tflite` | 320×320 | `[1, 300, 6]` NMS 내장 | 9.8 MB | 폴백용 |

출력 형식은 `outputRows == 84` 여부로 자동 판별해 후처리 함수를 분기합니다.

---

## API 명세

### POST /detect_json

Android 온디바이스 YOLO 결과 JSON을 수신해 로그 저장·대시보드 배포를 수행합니다.  
위험 판단과 진동은 Android에서 이미 처리된 상태입니다.

**요청 예시:**

```json
{
  "device_id": "android-a1b2c3d4",
  "mode": "장애물",
  "objects": [
    {
      "class_ko": "자동차",
      "confidence": 0.87,
      "bbox_norm_xywh": [0.5, 0.6, 0.3, 0.2],
      "risk_score": 0.82,
      "distance_m": 1.2,
      "vibration_pattern": "URGENT"
    }
  ],
  "client_perf": {"infer_ms": 28, "dedup_ms": 2}
}
```

**응답 예시:**

```json
{
  "status": "ok",
  "saved": true,
  "process_ms": 8
}
```

### POST /detect

서버 추론 엔드포인트 — **비활성화됨**

```
410 Gone
{"detail": "Server inference is disabled. Use on-device inference only."}
```

### GET /dashboard

실시간 대시보드 HTML. 세션별 탐지 물체·타임라인 시각화.

### GET /events/{session_id}

Server-Sent Events(SSE) 스트림. 대시보드 실시간 업데이트용.

### GET /status/{session_id}

세션의 현재 탐지 상태·이력 반환.

### GET /sessions

최근 활동 세션 목록 반환.

### GET /health

서버 상태 및 DB 연결 확인.

---

## 구현 현황

| 항목 | 상태 | 파일 |
|---|---|---|
| YOLO11n 온디바이스 추론 | ✅ 완료 | `YoloDetector.kt` |
| BBox Tracking + EMA | ✅ 완료 | `MvpPipeline.kt` |
| 위험도 계산 | ✅ 완료 | `MvpPipeline.kt` |
| 진동 패턴 정의 | ✅ 완료 | `MvpPipeline.kt` |
| 보팅 스레드 안전성 | ✅ 완료 | `MainActivity.kt` |
| JSON SSOT 서버 전송 | ✅ 완료 | `routes.py /detect_json` |
| 서버 추론 비활성화 | ✅ 완료 | `/detect` → 410 반환 |
| FastDepth 거리 추정 | ⬜ 미완료 | 현재 bbox 면적 기반 추정 사용 중 |
| 진동 HW 출력 연동 | ⬜ 미완료 | VibrationPattern 계산만, 실제 출력 미구현 |

---

## 프로젝트 구조

```
VoiceGuide/
├── android/
│   └── app/src/main/
│       ├── java/com/voiceguide/
│       │   ├── MainActivity.kt          # 카메라·STT·TTS·서버 연동 총괄
│       │   ├── YoloDetector.kt          # TFLite 온디바이스 추론 엔진
│       │   ├── MvpPipeline.kt           # 트래킹·EMA·위험도·진동 패턴 결정
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
│   │   ├── routes.py        # /detect_json /status /events /sessions /health
│   │   ├── db.py            # 탐지 이벤트·세션 저장
│   │   └── events.py        # SSE 이벤트 발행/구독
│   └── config/
│       └── policy.json      # 탐지 정책 SSOT
│
├── templates/
│   └── dashboard.html       # 실시간 세션 대시보드
├── tests/                   # pytest 단위 테스트
├── tools/                   # 모델 내보내기·서버 점검 도구
├── docs/                    # 설계 문서·개발 일지
├── Dockerfile               # GCP Cloud Run 배포용
└── requirements.txt
```

---

KDT AI Human 3팀 (2026-04-24 ~ 2026-05-13)  
GitHub: https://github.com/coding-jhj/VoiceGuide  
서버: https://voiceguide-1063164560758.asia-northeast3.run.app
