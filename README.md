# VoiceGuide

VoiceGuide는 시각장애인 보행 보조를 목표로 한 Android 앱입니다. 카메라로 주변 장애물을 탐지하고, 방향과 대략적 거리를 한국어 음성으로 안내합니다.

이 저장소의 기준은 "기능을 많이 적기"가 아니라 "실제로 실행하고 설명할 수 있는 기능만 문서에 적기"입니다.

## 현재 MVP

| 상태 | 기능 | 기준 |
|---|---|---|
| 동작 확인 | Android 카메라 장애물 탐지 | ONNX 모델로 온디바이스 탐지 |
| 동작 확인 | 방향 안내 | bbox 위치를 8시~4시 방향으로 변환 |
| 동작 확인 | 대략적 거리 안내 | bbox 면적 또는 Depth V2 보조값 기반 추정 |
| 동작 확인 | 한국어 TTS 안내 | Android OS TTS 우선, 서버 TTS는 선택 |
| 동작 확인 | 서버 실패 시 fallback | 서버 URL이 없거나 실패하면 온디바이스 탐지 유지 |
| 동작 확인 | GCP 서버 대시보드/GPS 시연 | `src.api.main:app`을 Cloud Run에 배포 |
| 실험 기능 | OCR, 옷 매칭, SOS, 하차 알림, 신호등, 공간 기억 | 발표에서는 "실험 기능"으로만 설명 |

안전 관련 표현은 과장하지 않습니다. "정확한 거리 측정" 대신 "대략적 거리 추정", "안전 보장" 대신 "보행 보조 정보 제공"이라고 설명합니다.

## 실행 진입점

| 목적 | 진입점 | 담당 |
|---|---|---|
| Android 앱 | `android/` | 김재현 |
| 서버 API | `src.api.main:app` | 정환주, 임명광 보조 |
| 서버 라우터 | `src/api/routes.py` | 정환주 |
| DB/tracker | `src/api/db.py`, `src/api/tracker.py` | 정환주, 임명광 보조 |
| 프론트엔드/대시보드 | `templates/dashboard.html`, README 첫 화면 | 정환주 |
| Vision/ML | `src/vision/`, `src/depth/`, `src/ocr/`, `train/`, `tools/benchmark.py` | 신유득 |
| NLG | `src/nlg/` | 임명광 |
| Voice/Q&A | `src/voice/`, `docs/06_presentation/`, Q&A 시트 | 문수찬 |

중복 서버였던 `server_db/`, `server_db_modified/`은 현재 본 서버가 아닙니다. 참고 코드는 `legacy/` 아래에 보관하며, Android와 GCP 배포는 `src/api/main.py`만 사용합니다.

## GCP 서버 실행

로컬 실행:

```bat
cd /d C:\VoiceGuide\VoiceGuide
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

GCP Cloud Run 배포:

```bat
cd /d C:\VoiceGuide\VoiceGuide
gcloud run deploy voiceguide --source . --region asia-northeast3 --memory 2Gi --cpu 2 --timeout 120 --allow-unauthenticated --port 8080
```

배포 확인:

```bat
python tools\probe_server_link.py --base https://voiceguide-135456731041.asia-northeast3.run.app
```

확인할 URL:

| 엔드포인트 | 용도 |
|---|---|
| `/health` | 서버, DB, Depth fallback 상태 확인 |
| `/detect` | Android 이미지 분석 요청 |
| `/status/{session_id}` | 현재 추적 객체와 GPS 상태 확인 |
| `/dashboard` | 시연용 대시보드 |

## 팀 역할

| 이름 | 역할 | 책임 코드/문서 |
|---|---|---|
| 정환주 | 팀장, 서버, 프론트엔드 | 일정·MVP 결정, README/docs 최종 검수, `src/api/`, `templates/`, GCP 배포 |
| 신유득 | Vision, ML | `src/vision/`, `src/depth/`, `src/ocr/`, `train/`, 평가 결과 |
| 김재현 | Android, UX | `android/app/`, UI 안정화, 권한/발열/TTS 겹침 점검 |
| 임명광 | NLG, 서버 도움 | `src/nlg/`, 서버 응답 문장, API 문서 보조 |
| 문수찬 | Voice, Q&A 시트 | `src/voice/`, STT/TTS 검증, 발표 Q&A 시트 |

역할별 작업 지침은 [ROLE_GUIDE.md](docs/04_team/ROLE_GUIDE.md)를 기준으로 봅니다.

## 코드 흐름

```text
Android MainActivity
  -> 온디바이스 우선: YoloDetector.kt -> SentenceBuilder.kt -> Android TTS
  -> 서버 사용 시: POST /detect
       -> src/api/routes.py
       -> src/depth/depth.py: detect_and_depth()
       -> src/vision/detect.py: detect_objects()
       -> src/depth/hazard.py: detect_floor_hazards()
       -> src/api/tracker.py: SessionTracker.update()
       -> src/api/db.py: snapshot/GPS 저장
       -> src/nlg/sentence.py: build_sentence()
       -> Android TTS
```

함수별 상세 학습 문서는 [FUNCTION_LOGIC_STUDY.md](docs/01_study/FUNCTION_LOGIC_STUDY.md)에 정리했습니다.

## 핵심 문서

| 문서 | 용도 |
|---|---|
| [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) | 현재 폴더 구조와 진입점 |
| [docs/03_server/README.md](docs/03_server/README.md) | GCP 기준 서버 문서 |
| [docs/04_team/ROLE_GUIDE.md](docs/04_team/ROLE_GUIDE.md) | 역할별 개발·조사 지침 |
| [docs/04_team/ANDROID_PERFORMANCE_GUIDE.md](docs/04_team/ANDROID_PERFORMANCE_GUIDE.md) | Android FPS/오탐 개선 지침 |
| [docs/01_study/FUNCTION_LOGIC_STUDY.md](docs/01_study/FUNCTION_LOGIC_STUDY.md) | 함수와 전체 로직 학습 |
| [docs/04_team/STUDENT_DEVELOPMENT_GUIDELINE.md](docs/04_team/STUDENT_DEVELOPMENT_GUIDELINE.md) | 강사 피드백 기반 개선 가이드 |

## 개발 원칙

1. 발표 전에는 기능 추가보다 검증을 우선합니다.
2. README의 "동작 확인" 항목은 APK나 서버에서 바로 시연 가능해야 합니다.
3. 서버 진입점은 `src.api.main:app` 하나로 고정합니다.
4. GCP가 주 배포 경로입니다. ngrok, Supabase 단독 서버, Railway/Render 문서는 참고 또는 과거 기록으로만 봅니다.
5. 안전 앱이므로 거리, 신호등, 계단, 차량, SOS 기능은 검증 범위를 넘어 과장하지 않습니다.
