# 역할별 개발 지침

> 목적: 각자가 어떤 코드를 읽고, 어떻게 고치고, 어떤 자료를 조사해야 하는지 명확히 정한다.  
> 공통 기준: 발표 전에는 기능 추가보다 검증, 문서 일치, 안전한 표현을 우선한다.

## 공통 작업 방식

1. 자기 담당 파일을 먼저 읽고 함수 단위로 설명할 수 있게 만든다.
2. README에 "동작 확인"이라고 적을 기능은 APK 또는 서버에서 직접 확인한다.
3. 새 기능을 넣기 전에 기존 기능의 실패 케이스를 먼저 기록한다.
4. 안전 앱이므로 "정확하다", "보장한다" 같은 표현은 검증된 범위에서만 쓴다.
5. PR이나 커밋에는 어떤 기능을 고쳤는지보다 어떤 위험을 줄였는지 적는다.

## 정환주 - 팀장, 서버, 프론트엔드

### 책임

- MVP 범위 고정
- 서버 진입점 단일화: `src.api.main:app`
- GCP Cloud Run 배포와 `/health`, `/detect`, `/dashboard` 확인
- 서버 대시보드와 README 첫 화면 정리
- README와 docs의 최종 표현 검수

### student development guide 기준 Phase 오너십

- Phase 1: 서버 진입점 단일화, dead code 처리 결정, 실행 경로 고정
- Phase 2: README/문서의 "동작 확인" 항목과 실제 동작 일치 검수
- Phase 5: 서버/DB/보안 기본선(API key, CORS, 비밀값 관리) 최종 책임
- Phase 6: 기본 실행 재현(`pytest -m "not integration"` 기준) 확인

### 완료 기준 (정환주 역할)

- `README.md`만 보고 서버 실행 진입점이 `src.api.main:app`로 명확하다.
- `/health`, `/detect`, `/dashboard`가 동일 서버 기준으로 재현된다.
- 서버 문서의 "완료" 표현이 실제 동작과 다르지 않다.
- 배포/대시보드 설명에서 개인정보·GPS 노출 관련 주의가 반영되어 있다.

### 정환주 역할 범위 밖

- Android 성능 튜닝, 권한 UX, bbox 색상 정책의 직접 구현
- YOLO/Depth/OCR 모델 성능 튜닝 및 학습 파이프라인 수정
- STT/TTS 문장 정책의 상세 구현

### 읽을 코드

| 파일 | 봐야 할 함수 |
|---|---|
| `src/api/main.py` | `lifespan`, `health`, `_check_db`, `global_exception_handler` |
| `src/api/routes.py` | `detect`, `_with_perf`, `_should_suppress`, `/status`, `/dashboard` |
| `src/api/db.py` | `init_db`, `save_snapshot`, `save_gps`, `get_gps_track` |
| `src/api/tracker.py` | `SessionTracker.update`, `get_current_state` |
| `templates/dashboard.html` | 대시보드 표시 구조, `/status/{session_id}` 호출 |
| `README.md` | 첫 화면 실행 진입점, MVP 범위, 역할 표 |

### 코드 작성 기준

- `/detect`는 요청 파싱, 모듈 호출, 응답 조립만 담당하게 유지한다.
- 서버 오류가 나도 Android가 읽을 수 있는 `sentence`를 반환한다.
- GCP 환경 변수는 `.env`나 Cloud Run env var로 관리하고 코드에 비밀값을 넣지 않는다.
- CORS는 필요한 origin만 허용한다. `*`는 로컬 실험에서만 사용한다.
- `request_id`와 `[PERF]` 로그를 유지해 Android-서버 연결을 증명한다.
- 대시보드는 시연용 관찰 화면이므로 GPS/객체 상태를 보여주되 개인정보를 과하게 노출하지 않는다.
- README 첫 화면에는 실행 명령과 본 서버 진입점이 먼저 보여야 한다.

### 조사할 자료

- Cloud Run 배포 로그 확인 방법
- FastAPI 예외 처리와 dependency 기반 API key 인증
- SQLite와 PostgreSQL의 SQL 문법 차이
- 안전 서비스의 개인정보/GPS 보관 최소화 사례
- 대시보드 UX에서 실시간 상태를 간결하게 보여주는 사례

## 신유득 - Vision, ML

### 책임

- YOLO 탐지 로직과 모델 파일명 정리
- Depth V2가 실제로 쓰이는지, fallback인지 확인
- 실패 케이스와 평가 자료 정리
- OCR, 신호등, 계단 등은 실험 기능으로 분리 설명

### 읽을 코드

| 파일 | 봐야 할 함수 |
|---|---|
| `src/vision/detect.py` | `detect_objects`, `_compute_scene_analysis`, `_detect_color`, `_detect_traffic_light_color` |
| `src/depth/depth.py` | `detect_and_depth`, `_check_model`, `_infer_depth_map`, `_bbox_dist_m` |
| `src/depth/hazard.py` | `detect_floor_hazards` |
| `src/ocr/bus_ocr.py` | `recognize_bus_number`, `_preprocess`, `_extract_bus_number` |
| `tools/benchmark.py` | 평가 데이터 입력과 결과 출력 |
| `docs/04_team/TODO_YOODK_VISION_ML.md` | 오탐/threshold/Depth fallback TODO |

### 코드 작성 기준

- 모델 파일명은 README, Android assets, 서버 코드 설명에서 일치시킨다.
- mAP 하나만 말하지 말고 Precision, Recall, False Positive 사례를 함께 본다.
- 거리값은 "대략적 추정"으로 문서화한다.
- 계단/낙차는 실환경 오탐이 있으면 "실험 기능"으로 분리한다.
- 오탐 이미지는 삭제하지 말고 `results/`나 문서에 실패 패턴으로 정리한다.

### 조사할 자료

- YOLO confidence threshold와 class별 threshold 튜닝 사례
- Depth Anything V2의 상대 깊이 한계
- 시각장애 보행 보조에서 false positive가 사용자 신뢰에 미치는 영향
- OCR 실환경 평가 방법: 흔들림, 측면, 야간, 반사

## 김재현 - Android, UX

### 책임

- Android 앱 실행 안정화
- CameraX 캡처 주기, ONNX 추론, 서버 fallback 관리
- 권한 요청을 기능별로 분리
- 화면 디버그 정보와 bbox 색상 UX 정리
- FPS 저하 원인을 측정하고, 직렬 병목을 안전하게 병렬화
- 오탐이 많은 경우 Android voting/threshold/UI 표시 정책을 신유득과 함께 조정

### 읽을 코드

| 파일 | 봐야 할 함수 |
|---|---|
| `android/app/src/main/java/com/voiceguide/MainActivity.kt` | `onCreate`, `startAnalysis`, `captureAndProcess`, `processOnDevice`, `sendToServer`, `handleSuccess` |
| `android/app/src/main/java/com/voiceguide/YoloDetector.kt` | `detect`, `postProcess`, `nms` |
| `android/app/src/main/java/com/voiceguide/SentenceBuilder.kt` | `build`, `buildFind`, `formatDist` |
| `android/app/src/main/java/com/voiceguide/BoundingBoxOverlay.kt` | `setDetections`, `hazardColor`, `onDraw` |
| `android/app/src/main/res/layout/activity_main.xml` | 첫 화면과 버튼 구조 |

### 코드 작성 기준

- 기본 동작은 온디바이스 우선이다. 서버는 URL이 있을 때만 사용한다.
- 캡처 주기는 발열과 배터리를 고려해 유지한다. 발표용 부드러움보다 안정성이 우선이다.
- TTS가 겹치지 않도록 `ttsBusy`, cooldown, `alert_mode` 흐름을 확인한다.
- SMS, 위치 권한은 해당 기능을 실제로 사용할 때만 요청한다.
- 화면에는 사용자에게 의미 없는 IP, confidence %, 디버그 문구를 기본 노출하지 않는다.
- FPS 개선은 추측으로 하지 말고 `VG_PERF` 로그의 `decode`, `infer`, `dedup`, `total` 값을 보고 병목부터 찾는다.
- 병렬화는 "프레임 무제한 처리"가 아니라 최대 동시 처리 수를 제한하는 방식으로 한다.
- TTS는 병렬화 대상이 아니다. 음성 출력은 항상 마지막에 하나씩 제어한다.
- 오탐이 많을 때 `VOTE_MIN_COUNT`만 낮추지 않는다. 모델 threshold, bbox 중복 제거, 거리/위험도 정책을 함께 본다.

### 조사할 자료

- CameraX와 ONNX Runtime Android 성능 최적화
- Android TalkBack 접근성 가이드
- 모바일 발열/배터리 측정 방법
- 안전 앱 UI에서 색상과 경고 단계 표현 방법
- producer-consumer 구조와 bounded executor 패턴
- ONNX Runtime Android thread 옵션과 NNAPI/CoreML 같은 mobile accelerator 개념

## 임명광 - NLG, 서버 도움

### 책임

- 탐지 결과를 짧고 자연스러운 한국어 안내로 변환
- 위험 물체와 생활 물체의 말투 분리
- 서버 응답 문장과 Android 문장 정책 일치
- 정환주의 서버 문서와 API 응답 예시 보조

### 읽을 코드

| 파일 | 봐야 할 함수 |
|---|---|
| `src/nlg/sentence.py` | `build_sentence`, `build_hazard_sentence`, `build_find_sentence`, `build_question_sentence`, `get_alert_mode` |
| `src/nlg/templates.py` | `CLOCK_TO_DIRECTION`, `get_absolute_clock` |
| `android/app/src/main/java/com/voiceguide/SentenceBuilder.kt` | 서버 없을 때의 온디바이스 문장 |
| `src/api/routes.py` | `detect`에서 문장을 선택하는 분기 |
| `tests/test_sentence.py` | 문장 테스트 |

### 코드 작성 기준

- 한 번의 안내는 1~2문장 안에서 끝낸다.
- "위험", "멈추세요"는 차량, 계단, 낙차 같은 실제 위험에만 사용한다.
- 키보드, 마우스, 책, TV 같은 생활 물체에는 긴급 표현을 붙이지 않는다.
- 같은 문장과 같은 거리 표현이 반복되지 않도록 테스트한다.
- Android `SentenceBuilder.kt`와 서버 `sentence.py`의 표현 정책을 크게 다르게 만들지 않는다.

### 조사할 자료

- 음성 UI의 정보량 제한 사례
- 시각장애인 보행 보조 앱의 안내 문장 패턴
- 한국어 조사 자동화와 자연스러운 거리 표현
- 경고 피로(alert fatigue) 관련 UX 자료

## 문수찬 - Voice, Q&A 시트 작성

### 책임

- STT/TTS 흐름 검증
- Android OS TTS와 서버 TTS fallback 차이 설명
- 발표 Q&A 시트 작성
- 강사님 질문에 역할별 답변이 나오도록 정리

### 읽을 코드

| 파일 | 봐야 할 함수 |
|---|---|
| `src/voice/stt.py` | `_classify`, `extract_label`, `listen_and_classify` |
| `src/voice/tts.py` | `_generate`, `speak`, `warmup_cache` |
| `android/app/src/main/java/com/voiceguide/MainActivity.kt` | `initSpeechRecognizer`, `handleSttResult`, `speakBuiltIn`, `speakElevenLabs` |
| `docs/06_presentation/QA_SHEET.md` | 발표 질문과 답변 |
| `docs/06_presentation/INSTRUCTOR.md` | 강사님 설명용 요약 |
| `docs/06_presentation/PRESENTATION_SCRIPT.md` | 발표 흐름 |

### 코드 작성 기준

- Android에서는 OS SpeechRecognizer와 OS TTS가 기본이다.
- 서버 STT는 Gradio/PC 테스트용임을 문서에 분리한다.
- STT unknown일 때 갑자기 장애물 안내가 시작되지 않도록 fallback 문구를 점검한다.
- 긴급 경고는 네트워크 TTS보다 OS TTS로 즉시 발화되는지 확인한다.
- Q&A에는 "검증된 기능", "실험 기능", "안전상 조심한 표현"을 나눠 적는다.

### 조사할 자료

- Android SpeechRecognizer의 한국어 인식 한계
- TTS 속도와 이해도 관련 접근성 자료
- 발표 Q&A 사례: 보안, GPS, 거리 정확도, 서버 장애 대응
- 시각장애인 사용자 인터뷰 질문 구성

## 매일 점검 질문

1. 어제 실제로 동작 확인한 것은 무엇인가?
2. 오늘 끝낼 파일이나 테스트는 무엇인가?
3. 문서와 코드가 어긋난 곳은 없는가?
4. 발표에서 과장될 수 있는 표현은 없는가?
5. 막힌 부분은 누구에게 넘겨야 하는가?
