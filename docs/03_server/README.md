# 서버 문서

현재 VoiceGuide의 본 서버는 하나입니다.

```text
src.api.main:app
```

GCP Cloud Run 배포와 Android 연동 모두 이 진입점만 사용합니다. `legacy/server_db/`, `legacy/server_db_modified/`은 과거 실험 또는 참고 코드이며 본 서버로 실행하지 않습니다.

## 담당

| 이름 | 역할 |
|---|---|
| 정환주 | 서버 책임자, 프론트엔드/대시보드, GCP 배포, API/DB/tracker 통합 |
| 임명광 | NLG 응답 문장과 서버 문서 보조 |
| 신유득 | Vision/ML 결과가 서버 응답에 들어가는지 검증 |
| 김재현 | Android에서 서버 URL/API key 입력과 fallback 검증 |
| 문수찬 | Q&A 시트에 서버 장애 대응 정리 |

## 실행

로컬:

```bat
cd /d C:\VoiceGuide\VoiceGuide
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

GCP Cloud Run:

```bat
cd /d C:\VoiceGuide\VoiceGuide
gcloud run deploy voiceguide --source . --region asia-northeast3 --memory 2Gi --cpu 2 --timeout 120 --allow-unauthenticated --port 8080
```

배포 확인:

```bat
python tools\probe_server_link.py --base https://voiceguide-135456731041.asia-northeast3.run.app
```

## 주요 엔드포인트

| 엔드포인트 | 설명 |
|---|---|
| `GET /health` | 서버 상태, DB 모드, Depth V2 또는 bbox fallback 확인 |
| `POST /detect` | Android 이미지 분석 메인 API |
| `POST /tts` | 선택적 서버 TTS 생성 |
| `POST /ocr/bus` | 실험 기능: 버스 번호 OCR fallback |
| `POST /vision/clothing` | 실험 기능: 옷 매칭/패턴 분석 |
| `GET /status/{session_id}` | 대시보드용 현재 객체/GPS 상태 |
| `GET /dashboard` | 시연용 대시보드 HTML |

## 보안 기준

- 공개 배포에서는 `API_KEY` 환경 변수를 설정한다.
- Android 앱 설정에 같은 API Key를 입력하면 `X-API-Key` 헤더로 전송된다.
- DB 접속 문자열은 `.env` 또는 Cloud Run 환경 변수에만 둔다.
- `/health`로 DB 상태를 확인하되, 민감한 접속 정보는 응답에 포함하지 않는다.
- CORS는 기본적으로 localhost와 Cloud Run URL만 허용한다.

## GCP 외 문서 정리

| 문서/코드 | 현재 의미 |
|---|---|
| `GCP_DEPLOY_NOW.md`, `GCP_GUIDE.md`, `GCP_SERVER_SETUP.md` | 현재 배포 참고 문서 |
| `../../legacy/ngrok_reference.md` | 과거 로컬 터널 참고 기록. 현재 서버 기준 아님 |
| `SUPABASE_QNA.md`, `SERVER_GUIDE.md` | DB 학습/과거 실험 참고 |
| `SERVER_ARCHITECTURE.md` | 과거 다중 서버 아이디어 참고. 현재 구조 아님 |
| `legacy/server_db*` | 본 서버가 아닌 legacy 코드 |

## 완료 기준

- README와 이 문서가 모두 `src.api.main:app`을 본 서버로 설명한다.
- `/detect`가 `src/api/routes.py`에서 제공됨을 팀원이 설명할 수 있다.
- Cloud Run URL의 `/health`, `/detect`, `/dashboard`가 확인된다.
- Android Logcat의 `VG_LINK` request_id와 서버 로그의 `[LINK]` request_id가 연결된다.
- 서버가 실패해도 Android 온디바이스 fallback이 유지된다.
