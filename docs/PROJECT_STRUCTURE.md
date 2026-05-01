# VoiceGuide 폴더 구조

> 기준: 발표와 배포에서 실제로 쓰는 구조를 먼저 보여준다. 과거 실험 코드는 `legacy/`로 분리한다.

## 실행 진입점

| 목적 | 경로 | 상태 |
|---|---|---|
| Android 앱 | `android/` | 본 앱 |
| 서버 API | `src.api.main:app` | 본 서버, GCP 배포 기준 |
| 서버 라우터 | `src/api/routes.py` | `/detect`, `/status`, `/dashboard` |
| DB/tracker | `src/api/db.py`, `src/api/tracker.py` | SQLite 또는 `DATABASE_URL` |
| 대시보드 | `templates/dashboard.html` | `/dashboard`에서 반환 |
| Gradio 데모 | `app.py` | 보조 데모, Android 본 흐름 아님 |

## 루트 파일

| 경로 | 용도 |
|---|---|
| `README.md` | 프로젝트 첫 진입 문서 |
| `Dockerfile` | Cloud Run 컨테이너 빌드 |
| `requirements-server.txt` | 서버 배포 의존성 |
| `requirements.txt` | 전체 개발 의존성 |
| `start.bat`, `stop.bat` | 로컬 보조 스크립트 |
| `.env.example` | 환경 변수 예시 |

## 주요 코드 폴더

| 경로 | 담당 | 역할 |
|---|---|---|
| `android/` | 김재현 | Android 앱, UX, 온디바이스 fallback |
| `src/api/` | 정환주, 임명광 보조 | FastAPI 서버, DB, tracker |
| `src/vision/` | 신유득 | YOLO 탐지, 색상/신호등 보조 분석 |
| `src/depth/` | 신유득 | Depth V2, bbox fallback, 바닥 위험 탐지 |
| `src/ocr/` | 신유득 | 버스 번호 OCR fallback 실험 |
| `src/nlg/` | 임명광 | 한국어 안내 문장, alert mode |
| `src/voice/` | 문수찬 | STT/TTS 서버 보조 모듈 |
| `tools/` | 각 담당 | 배포, benchmark, 검증 스크립트 |
| `tests/` | 각 담당 | pytest 테스트 |
| `train/` | 신유득 | 학습/데이터 준비 스크립트 |
| `templates/` | 정환주 | 프론트엔드/서버 대시보드 HTML |
| `legacy/` | 참고 전용 | 과거 서버 실험 코드 |

## 문서 폴더

| 경로 | 용도 |
|---|---|
| `docs/00_run/` | CMD 실행 절차 |
| `docs/01_study/` | 코드와 함수 학습 |
| `docs/02_meetings/` | 회의록과 피드백 |
| `docs/03_server/` | GCP 기준 서버 문서 |
| `docs/04_team/` | 역할, 체크리스트, 팀 운영 |
| `docs/05_planning/` | PRD, MVP, 리서치 |
| `docs/06_presentation/` | 발표 자료, Q&A |
| `docs/07_debug/` | 성능/탐지 디버그 |

## 핵심 문서

| 문서 | 용도 |
|---|---|
| `README.md` | 현재 MVP와 실행 진입점 |
| `docs/03_server/README.md` | GCP 서버 기준 문서 |
| `docs/04_team/TEAM.md` | 팀 역할 요약 |
| `docs/04_team/ROLE_GUIDE.md` | 역할별 코드 작성·조사 지침 |
| `docs/04_team/ANDROID_PERFORMANCE_GUIDE.md` | Android FPS/오탐 개선 지침 |
| `docs/01_study/FUNCTION_LOGIC_STUDY.md` | 함수별 전체 로직 학습 |
| `docs/04_team/STUDENT_DEVELOPMENT_GUIDELINE.md` | 강사 피드백 기반 개선 가이드 |

## Legacy

| 경로 | 현재 상태 |
|---|---|
| `legacy/server_db/` | Supabase 연결 학습/실험 서버 |
| `legacy/server_db_modified/` | blur 서버 등 과거 실험 |

이 폴더들은 Android 앱과 GCP 배포의 실행 진입점이 아닙니다.

## Git에 올리지 않는 것

| 항목 | 이유 |
|---|---|
| `.env`, `.env.*` | API Key, DB URL 보호 |
| `*.pt`, `*.pth`, `*.onnx`, `*.onnx.data`, `*.tflite` | 대용량 모델 |
| `voiceguide.db` | 로컬 DB |
| `.gradle-*`, `android/app/build/` | 빌드 캐시 |
| `.pytest_cache/`, `.ultralytics/`, `__pycache__/` | 실행 캐시 |
| `runs/`, `datasets/`, `flagged/` | 학습/실험 산출물 |

## 정리 원칙

1. 새 팀원은 `README.md`와 `docs/PROJECT_STRUCTURE.md`만 보고 시작할 수 있어야 한다.
2. 서버 진입점은 `src.api.main:app` 하나로 고정한다.
3. 문서에는 동작 확인, 실험 기능, 예정 기능을 분리해 적는다.
4. GCP를 주 배포 경로로 설명하고, 다른 배포 방식은 참고로만 남긴다.
