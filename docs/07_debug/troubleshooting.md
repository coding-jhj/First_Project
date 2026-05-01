# VoiceGuide Troubleshooting

현재 기준의 문제 해결 문서입니다. 서버 배포는 GCP Cloud Run을 기준으로 봅니다.

## 기술 스택 기준

| 영역 | 기준 |
|---|---|
| Android | Kotlin, CameraX, ONNX Runtime Android, Android TTS/STT |
| 서버 | FastAPI, Uvicorn, `src.api.main:app` |
| 배포 | GCP Cloud Run |
| Vision/ML | YOLO ONNX/PyTorch, Depth fallback |
| DB | SQLite 기본, `DATABASE_URL` 있을 때 PostgreSQL/Supabase |
| 문장 | `src/nlg/` |

## 자주 나는 문제

### 서버 URL은 되는데 장애물 안내가 안 나옴

확인 순서:

1. Android 서버 URL을 비워도 온디바이스 탐지가 되는지 확인합니다.
2. GCP `/health`가 응답하는지 확인합니다.
3. `sendToServer()` 실패 시 온디바이스 fallback이 유지되는지 봅니다.
4. 서버 응답의 `objects` 배열이 비어 있는지 확인합니다.

담당: 김재현, 정환주

### FPS가 너무 낮음

`docs/04_team/ANDROID_PERFORMANCE_GUIDE.md`를 먼저 봅니다.

원칙:

1. `VG_PERF` 로그 없이 interval부터 줄이지 않습니다.
2. 직렬 처리 병목(`isSending`, TTS, 서버 요청)을 분리합니다.
3. 오래된 프레임은 버리고 최신 프레임만 처리합니다.
4. 최대 동시 처리 수를 제한합니다.

담당: 김재현

### 오탐이 많음

확인:

1. 어떤 클래스가 어떤 환경에서 오탐인지 표로 적습니다.
2. 클래스별 threshold를 조정합니다.
3. FPS 개선과 오탐 개선을 동시에 봅니다.
4. Android 상수와 서버 Vision 설정이 서로 어긋나지 않는지 확인합니다.

담당: 신유득, 김재현

### TTS가 겹치거나 너무 자주 말함

확인:

1. Android TTS busy lock이 동작하는지 확인합니다.
2. critical, voice, beep, silent 조건을 분리합니다.
3. 질문 응답 직후 periodic 안내 억제가 동작하는지 확인합니다.

담당: 김재현, 문수찬

### GCP 첫 요청이 느림

원인: Cloud Run cold start와 모델 warmup.

대응:

1. 시연 전에 `/health`를 열어 서버를 깨웁니다.
2. 필요하면 Cloud Run 최소 인스턴스 1을 검토합니다. 비용이 생길 수 있으므로 팀장이 결정합니다.

담당: 정환주

### Depth V2가 안 뜸

모델 파일이 없으면 bbox fallback으로 동작합니다. 이것은 실패가 아니라 현재 구조의 정상 fallback입니다.

발표 표현:

> 서버 환경에서 Depth 모델이 준비되면 보조 깊이 추정을 사용하고, 없으면 bbox 기반 대략 거리 추정으로 안전하게 fallback합니다.

담당: 신유득

### Supabase 연결이 안 됨

현재 서버는 SQLite로도 동작해야 합니다. `DATABASE_URL`이 없어서 SQLite가 뜨는 것은 정상입니다.

GCP에서 PostgreSQL/Supabase를 쓰려면 Cloud Run 환경변수에 `DATABASE_URL`을 넣고 `/health`에서 `db_mode`를 확인합니다.

담당: 정환주, 임명광 보조

## 발표 전 점검

```bat
cd /d C:\VoiceGuide\VoiceGuide
python tools\probe_server_link.py --base https://voiceguide-1063164560758.asia-northeast3.run.app
```

Android:

1. 서버 URL 비움: 온디바이스 탐지 확인
2. 서버 URL 입력: GCP 연동 확인
3. 분석 시작/중지 반복
4. 권한 거부/허용 흐름 확인
5. 음성 안내 겹침 확인

## 참고

GCP 외 배포 방식은 현재 발표 기준이 아닙니다. 필요한 과거 참고 기록은 `legacy/` 아래에서만 확인합니다.
