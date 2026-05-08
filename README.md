# VoiceGuide — 시각장애인 보행 보조 앱

> KDT AI Human 3팀 | 2026-04-24 ~ 2026-05-13

시각장애인이 혼자 이동할 때, 카메라로 앞의 장애물을 감지하고 **진동과 음성으로 즉시 안내**하는 Android 앱입니다.

---

## 지금 동작하는 것 (MVP)

```
카메라
  → YOLO 온디바이스 탐지 (Android 내에서 처리)
    → 위험도 계산 + 진동 출력
      → 서버로 탐지 결과 JSON 전송
        → NLG 안내 문장 생성 → TTS 음성 출력
          → 대시보드에 실시간 시각화
```

| 기능 | 상태 |
|---|---|
| 장애물 탐지 (장애물 모드) | ✅ 동작 |
| 위험도 기반 진동 패턴 | ✅ 동작 |
| 음성 안내 문장 (TTS) | ✅ 동작 |
| 서버 전송 + DB 저장 | ✅ 동작 |
| 대시보드 실시간 현황 | ✅ 동작 |
| 대시보드 24시간 탐지 내역 | ✅ 동작 |
| 이동 경로 지도 시각화 | ✅ 동작 |

---

## 아키텍처

```
Android (로컬)
 └─ CameraX
     └─ YoloDetector (yolo11n_320.tflite, 온디바이스)
         └─ 보팅 필터 (3프레임 중 2회 이상 확정)
             └─ MvpPipeline (트래킹 · EMA · 위험도)
                 ├─ 진동 즉시 출력  ← 오프라인에서도 동작
                 └─ POST /detect (탐지 결과 JSON 전송)
                         │
                     FastAPI (GCP Cloud Run)
                      ├─ NLG 안내 문장 생성
                      ├─ DB 저장 (탐지 이벤트, GPS)
                      └─ 대시보드 SSE 배포
                         │
                     sentence + alert_mode 반환
                         │
                     Android TTS 발화
```

서버는 이미지를 받지 않습니다. YOLO 추론은 Android에서만 실행합니다.

---

## 기술 스택

| 영역 | 기술 |
|---|---|
| Android | Kotlin, CameraX, TFLite |
| 온디바이스 모델 | yolo11n_320.tflite (2.8 MB) |
| TTS / STT | Android 내장 |
| 백엔드 | Python 3.10, FastAPI |
| DB | SQLite / PostgreSQL (GCP Cloud SQL) |
| 배포 | GCP Cloud Run |
| 대시보드 지도 | Leaflet.js |

---

## 서버 실행

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

서버에 ML 모델이 필요하지 않습니다.

### 배포된 서버

```
https://voiceguide-1063164560758.asia-northeast3.run.app
GET /health  →  {"status":"ok","db":"ok"}
GET /dashboard  →  실시간 대시보드
```

---

## Android 앱 실행

1. Android Studio에서 `android/` 폴더 열기
2. Gradle Sync
3. USB로 기기 연결 (USB 디버깅 활성화)
4. Run (`Shift+F10`)
5. 설정(⚙) → 서버 URL 입력

서버 URL 없이 실행하면 진동만 동작합니다 (오프라인 모드).

---

## 대시보드

```
GET /dashboard
```

세션 ID를 입력하면 해당 기기의 탐지 현황과 이동 경로를 실시간으로 확인할 수 있습니다.

---

## 프로젝트 구조

```
VoiceGuide/
├── android/app/src/main/java/com/voiceguide/
│   ├── MainActivity.kt        # 카메라·TTS·서버 연동
│   ├── YoloDetector.kt        # TFLite 추론
│   ├── MvpPipeline.kt         # 트래킹·위험도·진동
│   └── VoicePolicy.kt         # policy.json 파싱
│
├── src/api/
│   ├── main.py                # FastAPI 진입점
│   ├── routes.py              # /detect /dashboard /events /health
│   ├── db.py                  # 탐지 이벤트·GPS 저장
│   └── tracker.py             # EMA 평활화
├── src/nlg/sentence.py        # 한국어 안내 문장 생성
│
├── templates/dashboard.html   # 실시간 대시보드
├── Dockerfile
└── requirements.txt
```

---

GitHub: https://github.com/coding-jhj/VoiceGuide
