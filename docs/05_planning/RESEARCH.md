# VoiceGuide Research Notes

현재 기획 기준에 맞춘 자료조사 요약입니다. 구현 범위는 README의 MVP를 넘기지 않습니다.

## 사용자 니즈

시각장애인 보행 보조에서 중요한 것은 긴 설명보다 즉시 행동으로 이어지는 짧은 안내입니다.

| 니즈 | VoiceGuide 반영 |
|---|---|
| 장애물 위치 파악 | 8시~4시 방향 안내 |
| 충돌 회피 | 가까운 물체 우선 안내 |
| 반복 안내 피로 감소 | voting, dedup, TTS 억제 |
| 서버 장애 대비 | Android 온디바이스 ONNX fallback |

발표에서는 "안전 보장"이 아니라 "보행 보조 정보 제공"이라고 말합니다.

## 기술 선택

| 영역 | 선택 | 이유 |
|---|---|---|
| Android 탐지 | ONNX Runtime Android | 서버 없이 기본 장애물 탐지 가능 |
| 서버 | FastAPI `src.api.main:app` | Android/GCP/대시보드 진입점 통일 |
| 배포 | GCP Cloud Run | 발표 기준을 하나로 고정 |
| 거리 | bbox + Depth fallback | 정확한 실측이 아닌 대략 거리 추정 |
| 음성 | Android TTS 우선 | 네트워크/API 키 의존도 감소 |

## 역할별 조사 과제

| 이름 | 조사할 것 | 결과물 |
|---|---|---|
| 정환주 | GCP Cloud Run, FastAPI health/detect/dashboard 흐름 | 서버 실행 체크리스트 |
| 신유득 | 오탐 클래스, threshold, 모델 크기/FPS 영향 | Vision/ML 평가표 |
| 김재현 | Android CameraX/ONNX 병렬 처리, UX 권한 흐름 | FPS 개선 실험표 |
| 임명광 | 위험도별 한국어 문장, 서버 응답 포맷 | NLG 문장 예시표 |
| 문수찬 | STT/TTS 실패 케이스, 발표 Q&A | Q&A 시트 |

## 기존 서비스와 차별점

| 기존 서비스 한계 | VoiceGuide 방향 |
|---|---|
| 물체 설명 중심 | 방향+거리+행동 안내 |
| 네트워크 의존 | 온디바이스 기본 탐지 |
| 반복 설명 피로 | 중복 억제와 위험도 필터 |
| 한국어 행동 문장 부족 | NLG 담당자가 한국어 문장 개선 |

## 참고 자료

| 자료 | 용도 |
|---|---|
| YOLO/ONNX Runtime Android 공식 문서 | Android 온디바이스 탐지 |
| Depth Anything V2 | 서버 보조 깊이 추정 |
| CameraX 공식 문서 | Android 카메라 |
| 시각장애인 보조기기 UX 연구 | 발표 문제정의 근거 |

새 자료를 추가할 때는 "이 자료가 현재 MVP 검증에 어떤 도움을 주는지"를 한 줄로 함께 적습니다.
