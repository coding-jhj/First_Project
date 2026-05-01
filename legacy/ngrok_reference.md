# Legacy Ngrok Reference

현재 발표/배포 기준은 GCP Cloud Run입니다.

이 문서는 GCP 장애 시 로컬 FastAPI 서버를 잠깐 외부에 노출해야 할 때만 보는 참고 문서입니다. README, 발표 자료, 역할 문서에서는 ngrok을 주 배포 방식으로 설명하지 않습니다.

## 임시 실행

```bat
cd /d C:\VoiceGuide\VoiceGuide
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

다른 CMD 창:

```bat
ngrok http 8000
```

Android 서버 URL에는 `Forwarding`에 표시된 `https://...ngrok-free.app` 주소만 입력합니다.

## 제한

| 항목 | 이유 |
|---|---|
| URL이 자주 바뀜 | 무료 플랜은 재시작 때 주소가 바뀜 |
| PC가 꺼지면 중단 | 로컬 PC를 터널링하는 방식 |
| 발표 기준으로 부적합 | 안정성, 재현성, URL 고정성이 낮음 |

따라서 최종 시연은 GCP Cloud Run URL을 우선 사용합니다.
