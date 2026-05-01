# Meeting Result 2026-04-28

이 문서는 2026-04-28 강사님 피드백을 현재 프로젝트 기준으로 다시 정리한 기록입니다.

## 강사님 피드백 요약

| 피드백 | 현재 대응 |
|---|---|
| 기능이 많아져 핵심이 흐려짐 | README와 발표 범위를 MVP 중심으로 축소 |
| 오탐이 많음 | Vision/ML 담당자가 클래스별 threshold와 실험표 관리 |
| FPS가 낮음 | Android 담당자가 직렬 구조를 병렬/최신 프레임 우선 구조로 개선 |
| 서버 기준이 흐림 | GCP Cloud Run + `src.api.main:app` 하나로 통일 |
| 팀원별 설명이 부족함 | 역할별 지침과 함수 학습 문서 작성 |

## 현재 역할

| 이름 | 역할 |
|---|---|
| 정환주 | 팀장, 서버, 프론트엔드 |
| 신유득 | Vision, ML |
| 김재현 | Android, UX |
| 임명광 | NLG, 서버 도움 |
| 문수찬 | Voice, Q&A 시트 작성 |

## 우선순위

| 우선순위 | 항목 | 담당 |
|---|---|---|
| P0 | Android 온디바이스 탐지 안정화 | 김재현 |
| P0 | GCP 서버 `/health`, `/detect`, `/dashboard` 검증 | 정환주 |
| P1 | 오탐 클래스 표와 threshold 근거 | 신유득 |
| P1 | FPS 병목 로그와 병렬화 계획 | 김재현 |
| P1 | NLG 문장 자연화와 서버 응답 보조 | 임명광 |
| P1 | STT/TTS 검증과 Q&A 시트 | 문수찬 |

## 문서 반영

| 문서 | 반영 내용 |
|---|---|
| `README.md` | MVP/GCP/역할 중심으로 축소 |
| `docs/01_study/FUNCTION_LOGIC_STUDY.md` | 함수와 전체 로직 학습 |
| `docs/04_team/ROLE_GUIDE.md` | 역할별 코드 작성·조사 지침 |
| `docs/04_team/ANDROID_PERFORMANCE_GUIDE.md` | FPS와 오탐 개선 지침 |
| `docs/03_server/DEPLOY_GUIDE.md` | GCP 배포 기준 |

## 발표 표현

기능은 "완성"보다 "동작 확인", "실험", "fallback"으로 나눠 말합니다.

| 위험한 표현 | 바꿀 표현 |
|---|---|
| 정확한 거리 측정 | 대략적 거리 추정 |
| 안전 보장 | 보행 보조 정보 제공 |
| 모든 기능 완성 | 현재 MVP 범위 동작 확인 |
| 서버가 항상 필요 | 서버 없이도 온디바이스 기본 탐지 가능 |
