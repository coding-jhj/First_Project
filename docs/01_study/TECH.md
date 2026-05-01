# VoiceGuide Tech Notes

이 문서는 현재 코드 기준의 기술 요약입니다. 오래된 역할 분배나 과거 배포 방식은 쓰지 않습니다.

## 현재 파이프라인

```text
Android MainActivity
  -> CameraX frame
  -> on-device ONNX path
       -> YoloDetector.kt
       -> SentenceBuilder.kt
       -> Android TextToSpeech
  -> server path when needed
       -> POST /detect
       -> src/api/routes.py
       -> detect_and_depth()
       -> detect_objects()
       -> detect_floor_hazards()
       -> SessionTracker.update()
       -> build_sentence()
       -> Android TextToSpeech
```

## 역할 기준

| 이름 | 담당 |
|---|---|
| 정환주 | 팀장, 서버, 프론트엔드, GCP 배포 |
| 신유득 | Vision, ML, 모델/오탐/평가 |
| 김재현 | Android, UX, FPS/권한/사용 흐름 |
| 임명광 | NLG, 서버 도움, 응답 문장 |
| 문수찬 | Voice, Q&A 시트, STT/TTS 검증 |

## 모듈

| 영역 | 주요 파일 | 공부할 함수 |
|---|---|---|
| Android | `android/app/src/main/java/com/voiceguide/` | `startAnalysis`, `captureAndProcess`, `processOnDevice`, `sendToServer`, `speak` |
| ONNX 탐지 | `YoloDetector.kt` | `detect`, 전처리, 후처리, NMS |
| Android 문장 | `SentenceBuilder.kt` | 방향/거리/위험도 문장 생성 |
| API | `src/api/main.py`, `src/api/routes.py` | `detect`, `health`, dashboard/status 흐름 |
| Vision/ML | `src/vision/`, `src/depth/`, `src/ocr/` | `detect_objects`, `detect_and_depth`, hazard 감지 |
| Tracker/DB | `src/api/tracker.py`, `src/api/db.py` | `update`, snapshot/GPS 저장 |
| NLG | `src/nlg/` | `build_sentence`, 조사/방향/행동 템플릿 |
| Voice | `src/voice/` | STT/TTS 유틸, 발표용 음성 검증 |

함수 단위 학습은 `docs/01_study/FUNCTION_LOGIC_STUDY.md`를 기준으로 합니다.

## 서버 기준

서버 진입점은 하나입니다.

```text
src.api.main:app
```

로컬:

```bat
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

GCP:

```bat
gcloud run deploy voiceguide --source . --region asia-northeast3 --memory 2Gi --cpu 2 --timeout 120 --allow-unauthenticated --port 8080
```

`legacy/server_db*`는 본 서버가 아니며 Android 연결이나 발표 기준으로 실행하지 않습니다.

## Android FPS 개선 기준

김재현 담당자는 `docs/04_team/ANDROID_PERFORMANCE_GUIDE.md`를 기준으로 작업합니다.

핵심은 기능 추가가 아니라 병목 측정과 병렬화입니다.

1. `VG_PERF` 로그로 capture, preprocess, YOLO, postprocess, TTS 시간을 분리합니다.
2. `INTERVAL_MS`를 무작정 낮추지 않습니다.
3. `isSending` 하나로 전체 프레임을 막는 직렬 구조를 bounded in-flight 구조로 바꿉니다.
4. 프레임은 최신 프레임 우선으로 처리하고, 오래된 프레임은 버립니다.
5. FPS가 올라도 오탐이 늘면 실패입니다. Vision/ML 담당 신유득과 클래스별 임계값을 같이 조정합니다.

## 발표 표현 원칙

| 금지 표현 | 권장 표현 |
|---|---|
| 정확한 거리 측정 | 대략적 거리 추정 |
| 안전 보장 | 보행 보조 정보 제공 |
| 완성된 자율 보행 | 장애물 인지와 회피 판단 보조 |
| 모든 상황 탐지 | 현재 테스트 범위에서 동작 확인 |

새 기능보다 검증 가능한 흐름을 우선합니다.
