# VoiceGuide GCP Deploy Guide

이 문서는 현재 발표/시연 기준 서버 배포 절차만 다룹니다.

## 기준

| 항목 | 현재 기준 |
|---|---|
| 배포 플랫폼 | GCP Cloud Run |
| 서버 진입점 | `src.api.main:app` |
| Android 연결 대상 | Cloud Run URL |
| 대시보드 | `/dashboard` |
| 상태 확인 | `/health` |
| 서버 담당 | 정환주 |
| 서버 보조 | 임명광 |
| Vision/ML 검증 | 신유득 |

`legacy/server_db/`, `legacy/server_db_modified/`는 본 서버가 아닙니다. Supabase 연결 학습과 과거 실험 기록으로만 둡니다.

## 배포 전 확인

1. 루트 폴더가 `C:\VoiceGuide\VoiceGuide`인지 확인합니다.
2. Android와 README에 적는 서버 URL은 Cloud Run URL 하나로 통일합니다.
3. `.env`나 GCP 환경변수에 필요한 키가 있는지 확인합니다.
4. 모델 파일이 없으면 Depth V2는 bbox 기반 fallback으로 동작합니다. 이 상태도 실패가 아니라 정상 fallback입니다.

## 로컬 실행

```bat
cd /d C:\VoiceGuide\VoiceGuide
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

확인:

```bat
python tools\probe_server_link.py --base http://127.0.0.1:8000
```

## GCP Cloud Run 배포

```bat
cd /d C:\VoiceGuide\VoiceGuide
gcloud run deploy voiceguide --source . --region asia-northeast3 --memory 2Gi --cpu 2 --timeout 120 --allow-unauthenticated --port 8080
```

배포 후 확인:

```bat
python tools\probe_server_link.py --base https://voiceguide-1063164560758.asia-northeast3.run.app
```

## Android 연결

Android 앱 설정의 서버 URL에는 Cloud Run 기본 URL만 입력합니다.

```text
https://voiceguide-1063164560758.asia-northeast3.run.app
```

`/detect`, `/health`, `/dashboard` 같은 경로는 앱이나 브라우저가 붙일 때만 사용합니다.

## 발표 때 설명할 말

> 서버는 GCP Cloud Run에 올린 FastAPI 하나를 기준으로 운영합니다. Android는 서버가 실패해도 온디바이스 ONNX 탐지를 유지하고, 서버는 대시보드, GPS, 질문 응답, Depth 보조 분석을 맡습니다.

## GCP 이외 문서 처리

GCP 외 배포 방식은 현재 발표 기준이 아닙니다. 필요한 과거 참고 기록은 `legacy/` 아래로 분리합니다.

새 문서에는 GCP 외 배포를 주 경로처럼 적지 않습니다.
