# Server And GCP

## 서버 기준

현재 발표/배포 기준 서버는 `src.api.main:app`입니다. 과거 실험 서버는 `legacy/`에 보관되어 있고, Android와 GCP 배포 설명에는 사용하지 않습니다.

## 주요 API

| 엔드포인트 | 역할 |
|---|---|
| `/health` | 서버, DB, Depth fallback 상태 확인 |
| `/detect` | 이미지 분석 요청 처리 |
| `/status/{session_id}` | 현재 추적 객체와 GPS 상태 확인 |
| `/dashboard` | 시연용 대시보드 |
| `/tts` | 서버 보조 TTS |

## `/detect` 처리 흐름

```text
Android
  -> POST /detect
  -> src/api/routes.py
  -> src/vision/detect.py: YOLO 탐지
  -> src/depth/depth.py: 깊이 추정 또는 bbox fallback
  -> src/depth/hazard.py: 바닥 위험/계단/낙차 판단
  -> src/api/tracker.py: 세션별 객체 추적
  -> src/api/db.py: GPS/스냅샷 저장
  -> src/nlg/sentence.py: 한국어 안내 문장 생성
```

## 서버가 담당하는 것

- Android가 보내는 이미지 분석
- 온디바이스보다 무거운 Depth/보조 분석
- DB 저장과 세션 상태 관리
- 대시보드 제공
- Android 문장 규칙과 같은 서버 문장 생성

## GCP 배포 기준

Cloud Run 배포 명령 예시:

```bat
gcloud run deploy voiceguide --source . --region asia-northeast3 --memory 2Gi --cpu 2 --timeout 120 --allow-unauthenticated --port 8080
```

배포 후 확인:

```bat
python tools\probe_server_link.py --base https://voiceguide-1063164560758.asia-northeast3.run.app
```

## 배포 전 확인 사항

| 항목 | 확인 이유 |
|---|---|
| `Dockerfile` | Cloud Run 빌드 기준 |
| `requirements.txt` | 배포 의존성 단일 기준 |
| `.env` 제외 | API 키, DB URL 보호 |
| 모델 파일 제외 | 대용량 파일은 Git/GCP 빌드에 직접 포함하지 않음 |
| `/health` 응답 | 서버, DB, fallback 상태 확인 |

## 설명할 때 주의할 점

- "서버가 있어야만 앱이 동작한다"가 아니라, "온디바이스가 기본이고 서버는 보조"라고 설명합니다.
- 거리와 위험 판단은 보행 보조 정보이며 안전 보장을 의미하지 않습니다.
- GCP는 발표/배포 기준이며, ngrok이나 과거 서버 폴더는 참고용입니다.
