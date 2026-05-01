# Server Architecture

> 현재 구조는 단일 FastAPI 서버입니다. 과거 다중 서버/서브 서버 구조는 사용하지 않습니다.

## Current Architecture

```text
Android
  -> POST /detect
  -> FastAPI: src.api.main:app
      -> routes.detect()
      -> detect_and_depth()
      -> tracker.update()
      -> db.save_snapshot() / db.save_gps()
      -> build_sentence()
  -> Android TTS

Dashboard
  -> GET /dashboard
  -> templates/dashboard.html
  -> GET /status/{session_id}
```

## Deployment

| 항목 | 기준 |
|---|---|
| Platform | GCP Cloud Run |
| Entry point | `src.api.main:app` |
| Docker | `Dockerfile` |
| Requirements | `requirements-server.txt` |
| Dashboard | `templates/dashboard.html` |

## Legacy

`legacy/server_db/`와 `legacy/server_db_modified/`는 현재 architecture에 포함되지 않습니다. 발표에서는 "과거 실험 코드" 또는 "학습 기록"으로만 설명합니다.
