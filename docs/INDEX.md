# VoiceGuide 문서 인덱스

> 기준: 2026-05-01 현재 실행 가능한 MVP, GCP 서버, 새 역할 분담 기준.

## 먼저 볼 문서

| 문서 | 용도 |
|---|---|
| [../README.md](../README.md) | 프로젝트 첫 진입, MVP, 실행 명령 |
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | 폴더 구조와 실행 진입점 |
| [03_server/README.md](03_server/README.md) | GCP 기준 서버 문서 |
| [04_team/TEAM.md](04_team/TEAM.md) | 팀 역할 요약 |
| [04_team/ROLE_GUIDE.md](04_team/ROLE_GUIDE.md) | 역할별 개발·조사 지침 |
| [04_team/ANDROID_PERFORMANCE_GUIDE.md](04_team/ANDROID_PERFORMANCE_GUIDE.md) | Android FPS/오탐 개선 지침 |
| [01_study/FUNCTION_LOGIC_STUDY.md](01_study/FUNCTION_LOGIC_STUDY.md) | 함수별 전체 로직 학습 |

## 역할별 바로가기

| 담당 | 봐야 할 문서 | 코드 |
|---|---|---|
| 정환주 - 팀장/서버/프론트엔드 | `04_team/SERVER_AND_LEAD_ACTIONS.md`, `03_server/README.md` | `src/api/`, `templates/`, `README.md` |
| 신유득 - Vision/ML | `01_study/FUNCTION_LOGIC_STUDY.md`, `07_debug/DETECTION_DEBUG.md` | `src/vision/`, `src/depth/`, `src/ocr/`, `train/` |
| 김재현 - Android/UX | `04_team/ANDROID_PERFORMANCE_GUIDE.md`, `01_study/FUNCTION_LOGIC_STUDY.md`, `07_debug/PERF_DEBUG.md` | `android/app/` |
| 임명광 - NLG/서버 도움 | `04_team/ROLE_GUIDE.md`, `01_study/FUNCTION_LOGIC_STUDY.md` | `src/nlg/`, `src/api/routes.py` |
| 문수찬 - Voice/Q&A | `06_presentation/`, `04_team/TEAM_BRIEFING.md` | `src/voice/`, 발표 Q&A 시트 |

## 문서 폴더

| 폴더 | 내용 |
|---|---|
| `00_run/` | CMD 실행 절차 |
| `01_study/` | 코드와 함수 학습 |
| `02_meetings/` | 회의록, 피드백 |
| `03_server/` | GCP 서버와 배포 |
| `04_team/` | 역할, 팀 운영, 체크리스트 |
| `05_planning/` | PRD, MVP, 리서치 |
| `06_presentation/` | 발표 자료, Q&A |
| `07_debug/` | 탐지/성능/보정 디버그 |

## 정리 기준

- 본 서버는 `src.api.main:app` 하나입니다.
- 배포 기준은 GCP Cloud Run입니다.
- `legacy/server_db*`는 참고 코드이며 본 서버가 아닙니다.
- README의 동작 확인 항목은 실제 시연 가능한 기능만 적습니다.
- 안전 관련 기능은 검증 범위 밖으로 과장하지 않습니다.
