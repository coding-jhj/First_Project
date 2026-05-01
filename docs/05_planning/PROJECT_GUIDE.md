# VoiceGuide Project Guide

이 문서는 프로젝트 운영 기준입니다. 기능 욕심을 줄이고, 강사 피드백에 맞춰 설명 가능한 MVP를 안정화하는 것을 우선합니다.

## 한 문장

VoiceGuide는 Android 카메라와 음성 안내를 사용해 시각장애인의 보행 중 장애물 인지를 보조하는 앱입니다.

## MVP 범위

| 구분 | 포함 |
|---|---|
| 반드시 시연 | Android 카메라, 온디바이스 장애물 탐지, 방향/거리 안내, Android TTS |
| 서버 시연 | GCP Cloud Run `/health`, `/detect`, `/dashboard` |
| 설명 가능 | 서버 실패 시 온디바이스 fallback |
| 실험 기능 | OCR, 신호등, 옷 매칭, SOS, 하차 알림, 공간 기억 |

실험 기능은 발표에서 핵심 성능처럼 말하지 않습니다.

## 팀 역할

| 이름 | 역할 | 지금 해야 할 일 |
|---|---|---|
| 정환주 | 팀장, 서버, 프론트엔드 | MVP 결정, GCP 서버, README/docs 최종 정합성 |
| 신유득 | Vision, ML | 오탐 클래스 정리, 모델/threshold 실험, 평가표 작성 |
| 김재현 | Android, UX | FPS 개선 지침 이행, 권한/화면/TTS 흐름 안정화 |
| 임명광 | NLG, 서버 도움 | 문장 자연화, API 응답 문구 보조, 서버 문서 확인 |
| 문수찬 | Voice, Q&A 시트 | STT/TTS 검증, 발표 예상질문 시트 작성 |

상세 지침은 `docs/04_team/ROLE_GUIDE.md`를 봅니다.

## 개발 순서

1. 현재 코드가 실제로 도는지 확인합니다.
2. README의 동작 확인 항목과 실제 코드가 맞는지 봅니다.
3. Android FPS와 오탐을 먼저 줄입니다.
4. GCP 서버 URL 기준으로 `/health`, `/detect`, `/dashboard`를 확인합니다.
5. 기능 추가는 이 네 가지가 안정화된 뒤에만 합니다.

## 금지

| 금지 | 이유 |
|---|---|
| 발표 직전 새 기능 추가 | 검증 시간이 부족해 전체 신뢰도가 떨어짐 |
| README에 안 되는 기능을 완료처럼 적기 | 강사 질문 때 코드와 문서가 어긋남 |
| GCP 외 배포를 주 경로처럼 설명 | 현재 팀 기준과 다름 |
| 역할과 다른 사람이 몰래 핵심 코드 수정 | 담당자가 설명하지 못함 |
| FPS 문제를 interval만 줄여 해결 | 발열, queue 적체, TTS 겹침이 생김 |

## 완료 기준

| 영역 | 완료 기준 |
|---|---|
| Android | 실제 폰에서 탐지, TTS, 중지/재시작 가능 |
| FPS | `VG_PERF` 로그로 병목 설명 가능 |
| Vision/ML | 오탐 사례와 threshold 조정 근거 정리 |
| Server | GCP URL로 `/health`와 `/dashboard` 확인 |
| NLG | 위험도별 문장 예시를 담당자가 설명 가능 |
| Voice/Q&A | 예상 질문과 답변 시트 준비 |

## 관련 문서

| 문서 | 용도 |
|---|---|
| `README.md` | 외부에 보여줄 현재 기준 요약 |
| `docs/PROJECT_STRUCTURE.md` | 폴더 구조 |
| `docs/01_study/FUNCTION_LOGIC_STUDY.md` | 함수 흐름 학습 |
| `docs/03_server/DEPLOY_GUIDE.md` | GCP 배포 |
| `docs/04_team/ROLE_GUIDE.md` | 역할별 작업 지침 |
| `docs/04_team/ANDROID_PERFORMANCE_GUIDE.md` | Android FPS/오탐 개선 |
