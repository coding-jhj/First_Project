# VoiceGuide Master Study

이 문서는 팀원이 어떤 순서로 프로젝트를 공부해야 하는지 정리한 입구 문서입니다.

## 먼저 읽을 순서

1. `README.md`
2. `docs/PROJECT_STRUCTURE.md`
3. `docs/01_study/FUNCTION_LOGIC_STUDY.md`
4. `docs/01_study/FUNCTION_DEEP_DIVE.md`
5. `docs/04_team/ROLE_GUIDE.md`
6. 본인 담당 문서

## 역할별 학습 경로

| 이름 | 담당 | 먼저 볼 문서 | 코드 |
|---|---|---|---|
| 정환주 | 팀장, 서버, 프론트엔드 | `docs/03_server/README.md`, `docs/03_server/DEPLOY_GUIDE.md`, `docs/01_study/FUNCTION_DEEP_DIVE.md` | `src/api/`, `templates/` |
| 신유득 | Vision, ML | `docs/01_study/FUNCTION_DEEP_DIVE.md`, `docs/07_debug/DETECTION_DEBUG.md` | `src/vision/`, `src/depth/`, `train/` |
| 김재현 | Android, UX | `docs/04_team/ANDROID_PERFORMANCE_GUIDE.md`, `docs/01_study/FUNCTION_DEEP_DIVE.md`, `docs/07_debug/PERF_DEBUG.md` | `android/app/` |
| 임명광 | NLG, 서버 도움 | `docs/04_team/ROLE_GUIDE.md`, `docs/01_study/FUNCTION_DEEP_DIVE.md`, `docs/03_server/SERVER_ROLE_GUIDE.md` | `src/nlg/`, `src/api/routes.py` |
| 문수찬 | Voice, Q&A 시트 | `docs/06_presentation/`, `docs/04_team/ROLE_GUIDE.md` | `src/voice/` |

## 전체 로직 암기용

```text
Android
  -> CameraX frame
  -> on-device ONNX detect
  -> SentenceBuilder
  -> Android TTS

Server option
  -> POST /detect
  -> src/api/routes.py
  -> detect_and_depth()
  -> detect_objects()
  -> hazard detection
  -> tracker/db
  -> build_sentence()
  -> Android TTS
```

## 함수별로 공부할 때

먼저 `docs/01_study/FUNCTION_LOGIC_STUDY.md`로 전체 흐름을 잡고, `docs/01_study/FUNCTION_DEEP_DIVE.md`에서 함수 이름, 입력, 출력, 연결 관계를 파일별로 따라갑니다.

| 질문 | 볼 곳 |
|---|---|
| Android에서 프레임이 어디서 시작되나 | `MainActivity.kt` |
| ONNX 결과가 어디서 문장으로 바뀌나 | `YoloDetector.kt`, `SentenceBuilder.kt` |
| 서버 `/detect`가 무엇을 호출하나 | `src/api/routes.py` |
| Vision/ML 결과 구조는 무엇인가 | `src/vision/`, `src/depth/` |
| 문장이 왜 그렇게 나오나 | `src/nlg/` |
| TTS가 왜 겹치거나 안 겹치나 | Android TTS 흐름, `src/voice/` |

## 발표 대비 핵심 답변

| 질문 | 답변 방향 |
|---|---|
| 왜 GCP인가 | 발표 기준 배포를 하나로 통일해 재현성을 높이기 위해 Cloud Run을 사용합니다. |
| 서버가 꺼지면 어떻게 되나 | Android 온디바이스 ONNX 탐지는 유지되고, 서버 기능만 fallback됩니다. |
| 거리는 정확한가 | 정확한 측정이 아니라 bbox/Depth 기반 대략 거리 추정입니다. |
| 오탐은 어떻게 줄이나 | 클래스별 threshold, voting, 최신 프레임 우선 처리로 줄입니다. |
| FPS가 낮으면 어떻게 하나 | 직렬 구조를 bounded 병렬 처리로 바꾸고 `VG_PERF`로 병목을 측정합니다. |

## 공부 원칙

1. README에 적힌 기능과 실제 코드가 맞는지 먼저 봅니다.
2. 본인 담당 함수는 입력/출력/호출 위치까지 설명할 수 있어야 합니다.
3. 발표 전에는 새 기능보다 실패 원인과 fallback을 설명할 수 있어야 합니다.
4. GCP 외 서버 문서는 참고 기록으로만 보고, 현재 기준은 `src.api.main:app` + GCP입니다.
