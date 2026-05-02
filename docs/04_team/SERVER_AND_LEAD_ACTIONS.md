# 팀장/서버 실행 체크리스트

> 담당: 정환주 (팀장, 서버, 프론트엔드)  
> 보조: 임명광  
> 목표: 서버 진입점과 발표 범위를 흔들리지 않게 고정한다.

## 1. 서버 기준

| 항목 | 기준 |
|---|---|
| 본 서버 | `src.api.main:app` |
| 라우터 | `src/api/routes.py` |
| DB | `src/api/db.py` |
| tracker | `src/api/tracker.py` |
| 배포 | GCP Cloud Run `voiceguide` |
| 프론트엔드/대시보드 | `templates/dashboard.html`, `/dashboard` |

`legacy/server_db*`는 본 서버가 아닙니다. 발표와 Android 연동에서는 실행하지 않습니다.

## 2. 오늘 확인할 명령

로컬 서버:

```bat
cd /d C:\VoiceGuide\VoiceGuide
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

GCP 배포:

```bat
cd /d C:\VoiceGuide\VoiceGuide
gcloud run deploy voiceguide --source . --region asia-northeast3 --memory 2Gi --cpu 2 --timeout 120 --allow-unauthenticated --port 8080
```

배포 확인:

```bat
python tools\probe_server_link.py --base https://voiceguide-1063164560758.asia-northeast3.run.app
```

성공 기준:

```text
/health HTTP 200
/dashboard HTTP 200
/detect HTTP 200 또는 정상 fallback 응답
```

## 3. 팀장 결정 사항

| 결정 | 현재 기준 |
|---|---|
| 핵심 MVP | 장애물 안내, 물건찾기, 물건 확인 |
| 공통 기반 | 방향 안내, 대략적 거리, TTS, 온디바이스 fallback |
| 서버 보조 | GCP `/health`, `/status`, `/dashboard` 연결 확인 |
| 실험 기능 | OCR, 옷 매칭, SOS, 하차 알림, 신호등, 공간 기억, GPS 대시보드 |
| 서버 진입점 | `src.api.main:app` |
| 배포 경로 | GCP Cloud Run |
| 표현 | 정확/보장 대신 대략/보조/실험 |

## 4. 역할 연결

| 사람 | 서버와 연결되는 지점 |
|---|---|
| 정환주 | FastAPI, DB, GCP, 프론트엔드/대시보드, README 최종 검수 |
| 신유득 | `detect_and_depth()` 결과가 서버 응답에 들어가는지 검증 |
| 김재현 | Android `sendToServer()`와 fallback 검증 |
| 임명광 | `build_sentence()`와 서버 응답 문장 검수 |
| 문수찬 | 서버 장애 대응과 Voice 관련 Q&A 정리 |

## 5. 발표 때 말할 문장

```text
서버 진입점은 src.api.main:app 하나로 고정했습니다.
Android 요청은 /detect로 들어오고, 서버는 Vision/Depth, tracker, DB, NLG를 호출한 뒤 sentence와 alert_mode를 반환합니다.
GCP Cloud Run에 배포해 /health와 /dashboard로 상태를 확인할 수 있습니다.
서버가 실패해도 Android 온디바이스 ONNX 탐지가 기본 장애물 안내를 유지합니다.
```

## 6. 금지 표현

- 정확한 거리 측정
- 안전 보장
- 신호등 판단 보장
- 계단 100% 감지
- 서버가 없으면 앱이 동작하지 않음

## 7. 완료 체크

- [ ] README가 `src.api.main:app`을 본 서버로 설명한다.
- [ ] `docs/03_server/README.md`가 GCP 기준으로 정리됐다.
- [ ] Android와 서버 로그에서 같은 `request_id`를 찾을 수 있다.
- [ ] `/health`에서 DB 상태를 확인했다.
- [ ] 실험 기능을 발표 범위와 분리했다.
- [ ] 문서의 팀 역할이 새 분담과 일치한다.
