# Server Guide

> 현재 기준: 본 서버는 `src.api.main:app` 하나입니다.  
> 과거 `legacy/server_db*` 코드는 학습/실험 기록이며 Android와 GCP 배포의 실행 진입점이 아닙니다.

## 담당

| 이름 | 역할 |
|---|---|
| 정환주 | 서버 책임자, GCP 배포, 프론트엔드/대시보드 |
| 임명광 | NLG 응답 문장과 서버 문서 보조 |
| 신유득 | Vision/ML 결과 검증 |
| 김재현 | Android 서버 연결과 fallback 검증 |
| 문수찬 | Voice와 Q&A 시트 |

## 실행

```bat
cd /d C:\VoiceGuide\VoiceGuide
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

GCP 배포:

```bat
gcloud run deploy voiceguide --source . --region asia-northeast3 --memory 2Gi --cpu 2 --timeout 120 --allow-unauthenticated --port 8080
```

## API 흐름

```text
Android sendToServer()
  -> POST /detect
  -> src/api/routes.py: detect()
  -> src/depth/depth.py: detect_and_depth()
  -> src/vision/detect.py: detect_objects()
  -> src/api/tracker.py: SessionTracker.update()
  -> src/api/db.py: snapshot/GPS 저장
  -> src/nlg/sentence.py: build_sentence()
  -> Android handleSuccess()
```

## Legacy 코드

| 경로 | 현재 의미 |
|---|---|
| `legacy/server_db/` | Supabase 연결 학습/실험 서버 |
| `legacy/server_db_modified/` | blur 등 과거 실험 서버 |

발표나 README에서는 legacy 코드를 본 서버처럼 설명하지 않습니다.
