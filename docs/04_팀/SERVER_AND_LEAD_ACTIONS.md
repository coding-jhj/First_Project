# 서버 담당 + 팀장 실행 체크리스트

> 기준 문서: `06_student_development_guideline.md`  
> 목표: 발표 전까지 기능 추가보다 검증, 실행 재현, 서버-클라이언트 연동 증명을 우선합니다.

## 1. 서버 담당이 책임지는 범위

| 영역 | 기준 |
|---|---|
| 서버 진입점 | `src.api.main:app` 하나로 고정 |
| 배포 | GCP Cloud Run `voiceguide` 서비스 |
| DB | `src/api/db.py`, SQLite 또는 `DATABASE_URL` 기반 PostgreSQL |
| 대시보드 | `/dashboard`, `/status/{session_id}` |
| 연동 증명 | Android `VG_LINK`와 서버 `[LINK]`의 같은 `request_id` |
| 성능 증명 | Android `VG_PERF`, 서버 `[PERF]` |
| 보안 | API Key, CORS 제한, credential `.env` 관리 |

`legacy/서버_DB/`, `legacy/서버_DB_수정/`은 현재 본 서버가 아닙니다. 발표/배포/Android 연동 기준은 `src/api/main.py`입니다.

## 2. 오늘 서버 담당이 해야 할 일

### 2.1 GCP 재배포

```bat
cd /d C:\VoiceGuide\VoiceGuide
gcloud run deploy voiceguide --source . --region asia-northeast3 --memory 2Gi --cpu 2 --timeout 120 --allow-unauthenticated --port 8080
```

### 2.2 서버 단독 연동 확인

```bat
python tools\probe_server_link.py --base https://voiceguide-135456731041.asia-northeast3.run.app
```

성공 기준:

```text
[detect] HTTP 200
[status] HTTP 200
[dashboard] HTTP 200
[probe] OK
```

### 2.3 Android와 서버 연동 확인

Android Studio Logcat:

```text
VG_FLOW|VG_LINK|VG_PERF|VG_DETECT
```

GCP 로그:

```bat
gcloud run services logs tail voiceguide --region asia-northeast3
```

성공 기준:

```text
Android: VG_LINK request_id=and-...
Server : [LINK] request_id=and-...
Server : [PERF] request_id=and-...
```

같은 `request_id`가 양쪽에 보이면 서버-클라이언트 연동 확인 완료입니다.

## 3. API Key 보안 모드

가이드의 "공개 API에 최소한의 API Key" 요구를 반영해 서버는 `API_KEY` 환경변수가 있을 때 민감 엔드포인트를 보호합니다.

보호 대상:

```text
/detect
/tts
/vision/clothing
/ocr/bus
/locations*
/status/{session_id}
/dashboard
/spaces/snapshot
```

로컬/데모에서 `API_KEY`가 비어 있으면 기존처럼 인증 없이 동작합니다. 운영/공개 시연에서 보호하려면 Cloud Run에 환경변수를 설정합니다.

```bat
gcloud run services update voiceguide ^
  --region asia-northeast3 ^
  --set-env-vars API_KEY=원하는_긴_비밀값
```

Android 앱에서는 설정창에 서버 URL과 같은 API Key를 입력합니다.  
더미 probe는 아래처럼 실행합니다.

```bat
python tools\probe_server_link.py --base https://voiceguide-135456731041.asia-northeast3.run.app --api-key 원하는_긴_비밀값
```

또는:

```bat
set VOICEGUIDE_API_KEY=원하는_긴_비밀값
python tools\probe_server_link.py --base https://voiceguide-135456731041.asia-northeast3.run.app
```

## 4. 서버 담당 완료 기준

- `README.md` 또는 `docs/00_실행/CMD_RUNBOOK.md`만 보고 서버를 실행할 수 있습니다.
- `/detect`의 제공 파일이 `src/api/routes.py`, 앱 진입점이 `src/api/main.py`임을 설명할 수 있습니다.
- `legacy/서버_DB*`는 본 서버가 아니라고 설명할 수 있습니다.
- `probe_server_link.py`가 성공합니다.
- Android와 GCP 로그에서 같은 `request_id`를 확인했습니다.
- `/health`에서 DB 상태가 `ok`로 보입니다.
- 서버 로그 `[PERF]`로 detect/tracker/nlg/total 시간을 구분할 수 있습니다.
- API Key를 켜면 URL만 아는 사람이 `/status`와 `/dashboard`를 볼 수 없습니다.

## 5. 팀장이 해야 할 일

팀장의 역할은 코드를 직접 다 고치는 사람이 아니라, 발표 범위와 책임자를 고정하는 사람입니다.

오늘 결정할 것:

| 결정 | 팀장 액션 |
|---|---|
| MVP 범위 | 장애물 탐지, 방향 안내, 대략 거리, TTS, 서버 fallback, 대시보드/GPS로 고정 |
| 실험 기능 | 옷 매칭, 지폐, 약 알림, 하차, SOS, 신호등, 버스 OCR, 공간 기억은 시연 가능 여부 별도 표시 |
| 서버 진입점 | `src.api.main:app`로 고정 승인 |
| dead code | `legacy/서버_DB*`는 본 서버가 아니라고 팀 공지 |
| 발표 표현 | "정확한 거리"가 아니라 "대략적 거리 추정" 사용 |
| 보안 | 공개 시연 전에 API Key 사용 여부 결정 |
| 일일 점검 | 어제 한 일, 오늘 할 일, 막힌 점을 5-10분 확인 |

팀장 질문 5개:

1. 실제로 되는 기능은 무엇인가요?
2. 동작하지 않거나 불확실한 기능은 무엇인가요?
3. 사용자의 안전을 위해 어떤 보수적 선택을 했나요?
4. 서버가 실패해도 앱은 어떻게 대응하나요?
5. 모델이 틀렸을 때 사용자가 위험해지지 않도록 어떤 장치를 두었나요?

## 6. 발표 때 서버 담당이 말할 문장

```text
서버 진입점은 src.api.main:app 하나로 고정했습니다.
Android 요청에는 request_id를 붙이고, 서버도 같은 request_id를 로그에 남깁니다.
그래서 앱 요청이 서버 /detect, DB/tracker, /status, /dashboard까지 이어지는지 증명할 수 있습니다.
장애물/찾기 기본 기능은 Android ONNX 우선이라 서버가 느리거나 실패해도 기본 탐지는 유지됩니다.
서버는 질문, 색상, OCR, 대시보드/GPS 확인 같은 확장 기능과 시연용 관찰에 사용합니다.
거리 정보는 단안 카메라 기반의 대략적 추정이며, 정확한 거리 측정이라고 표현하지 않습니다.
```

