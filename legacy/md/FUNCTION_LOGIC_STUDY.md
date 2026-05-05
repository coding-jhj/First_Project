# 함수와 전체 로직 학습

> 목적: 팀원이 자기 담당 코드를 함수 단위로 설명할 수 있게 만든다.  
> 기준: 현재 실제 실행 흐름은 Android 온디바이스 우선, 서버 사용 시 `src.api.main:app`으로 연결된다.

파일별 함수 역할, 입력/출력, 디버깅 포인트까지 세세히 공부할 때는 `docs/01_study/FUNCTION_DEEP_DIVE.md`를 함께 봅니다.

## 1. 전체 흐름

```text
앱 시작
  -> MainActivity.onCreate()
  -> TTS, STT, 센서, ONNX detector 초기화
  -> 사용자가 분석 시작
  -> startCamera()
  -> startAnalysis()
  -> scheduleNext()
  -> captureAndProcess()

온디바이스 우선
  -> processOnDevice()
  -> YoloDetector.detect()
  -> MainActivity.voteOnly()
  -> MainActivity.classify()
  -> SentenceBuilder.build()
  -> handleSuccess()
  -> speakBuiltIn()

서버 모드
  -> sendToServer()
  -> POST /detect
  -> routes.detect()
  -> detect_and_depth()
  -> detect_objects()
  -> detect_floor_hazards()
  -> tracker.update()
  -> db.save_snapshot(), db.save_gps()
  -> build_sentence()
  -> Android handleSuccess()
```

## 2. Android 핵심 로직 - 김재현

### `MainActivity.onCreate()`

앱의 시작점입니다. 레이아웃을 붙이고, TTS, STT, 센서, 위치 관리자, ONNX detector를 초기화합니다. 버튼 이벤트도 여기서 연결합니다.

확인할 것:

- `btnToggle`이 분석 시작/중지를 바꾸는지
- `btnStt`가 음성 명령을 시작하는지
- `tryInitYoloDetector()` 실패 시 서버 fallback으로 넘어갈 수 있는지

### `requestPermissions()`, `requestLocationPermission()`, `requestSmsPermission()`

권한 요청 함수입니다. 카메라/마이크는 기본 분석에 필요하지만, 위치와 SMS는 해당 기능을 쓸 때만 요청해야 합니다.

개선 기준:

- 처음 실행부터 SMS 권한을 묻지 않는다.
- 위치 권한은 GPS/하차 알림/대시보드 시연 때만 요청한다.

### `startCamera()`

CameraX preview와 `ImageCapture`를 준비합니다. 카메라가 준비되어야 `captureAndProcess()`가 프레임을 저장할 수 있습니다.

### `startAnalysis()`, `scheduleNext()`, `captureAndProcess()`

분석 루프입니다. `INTERVAL_MS` 간격으로 이미지를 캡처하고, 이미 처리 중이면 중복 요청을 막습니다.

중요한 변수:

- `INTERVAL_MS`: 현재 캡처 간격
- `isAnalyzing`: 분석 루프 실행 여부
- `isSending`: 서버/온디바이스 처리 중복 방지

### `shouldUseOnDeviceDetector()`

온디바이스 탐지를 쓸지 결정합니다. 기본은 ONNX detector가 있으면 온디바이스를 우선하고, 실패하거나 서버 모드가 필요한 경우 서버로 넘깁니다.

### `processOnDevice()`

서버 없이 동작하는 핵심 경로입니다.

처리 순서:

1. JPEG를 bitmap으로 읽고 방향을 보정한다.
2. `YoloDetector.detect()`로 객체를 찾는다.
3. `StairsDetector.detect()`로 계단 후보를 보조 탐지한다.
4. `removeDuplicates()`로 겹치는 bbox를 줄인다.
5. `voteOnly()`로 순간 오탐을 줄인다.
6. `classify()`로 음성 안내/무음/비프를 나눈다.
7. `SentenceBuilder.build()` 또는 `buildFind()`로 문장을 만든다.
8. `handleSuccess()`로 UI와 TTS를 처리한다.

### `sendToServer()`

서버 URL이 있을 때 `/detect`로 이미지를 보냅니다. 이미지, WiFi SSID, 모드, GPS, `request_id`를 multipart form으로 전송합니다.

확인할 것:

- 서버 실패 시 `handleFail()`이 호출되는지
- 성공 시 `sentence`, `alert_mode`, `process_ms`, `perf`를 읽는지
- Logcat의 `VG_LINK`, `VG_PERF`가 서버 로그와 연결되는지

### `handleSuccess()`

분석 결과를 실제 음성/UI로 바꾸는 마지막 관문입니다.

중요한 정책:

- `critical`: 즉시 TTS
- `beep`: 짧은 주의 안내
- `silent`: UI만 유지하거나 아무 말도 하지 않음
- 같은 문장 반복 방지
- TTS 재생 중 겹침 방지

## 3. Android ONNX 탐지 - 김재현, 신유득

### `YoloDetector.detect(bitmap)`

Android에서 ONNX Runtime으로 객체를 탐지합니다.

처리 순서:

1. bitmap resize
2. `bitmapToNCHW()`로 모델 입력 tensor 생성
3. ONNX session 실행
4. `postProcess()`로 bbox와 class 변환
5. `nms()`로 중복 bbox 제거

### `SentenceBuilder.build(detections)`

서버 없이 문장을 만드는 Android NLG입니다. 서버의 `src/nlg/sentence.py`와 표현 정책이 크게 어긋나면 안 됩니다.

확인할 것:

- 생활 물체에 과한 경고가 붙지 않는지
- 찾기 모드가 `buildFind()`로 분리되는지
- 거리 표현이 너무 확정적으로 들리지 않는지

### `BoundingBoxOverlay.onDraw()`

탐지 bbox를 화면에 그립니다. 발표 화면에서는 디버그 정보가 과하면 신뢰가 떨어질 수 있습니다.

개선 기준:

- 빨강: 실제 위험
- 노랑: 주의
- 초록/흰색: 일반 정보
- confidence %는 기본 화면에서 숨김

## 4. 서버/프론트엔드 시작 로직 - 정환주

### `src/api/main.py:lifespan()`

서버 시작 시 실행됩니다.

처리 순서:

1. `db.init_db()`로 DB 테이블 생성
2. YOLO 모델 warmup
3. Depth V2 모델 preload 시도
4. OCR/TTS warmup을 background thread로 실행

주의:

- Depth V2 모델이 없어도 서버는 죽으면 안 됩니다.
- warmup 실패는 fallback으로 처리합니다.

### `health()`

서버 상태 확인 API입니다.

응답에서 볼 것:

- `status`: 전체 상태
- `depth_v2`: loaded 또는 fallback
- `db_mode`: sqlite 또는 postgresql
- `db`: DB 연결 상태

### `global_exception_handler()`

서버 내부 오류가 나도 Android가 읽을 수 있는 기본 JSON을 반환합니다. 안전 앱에서는 오류도 음성 안내로 처리되어야 합니다.

### `templates/dashboard.html`

GCP 서버의 `/dashboard`에서 반환되는 시연용 프론트엔드입니다. `/status/{session_id}`를 주기적으로 조회해 현재 객체와 GPS 이동 경로를 보여줍니다.

확인할 것:

- 화면 첫 진입에서 무엇을 보는 페이지인지 바로 이해되는지
- GPS/객체 정보가 발표에 필요한 만큼만 보이는지
- 서버가 응답하지 않을 때 빈 화면으로 멈추지 않는지

## 5. 서버 라우터 - 정환주, 임명광

### `_verify_api_key()`

`API_KEY` 환경 변수가 설정된 경우 요청 헤더를 검사합니다.

허용 헤더:

- `Authorization: Bearer <key>`
- `X-API-Key: <key>`

### `_with_perf()`

모든 주요 응답에 `request_id`, `process_ms`, `perf`를 붙입니다. Android Logcat과 GCP 로그를 연결할 때 중요합니다.

### `_should_suppress()`

같은 문장이 짧은 시간 안에 반복되면 `silent`로 내려 경고 피로를 줄입니다. 단, `critical`은 항상 통과합니다.

### `detect()`

서버의 핵심 API입니다.

모드별 흐름:

| mode | 흐름 |
|---|---|
| 저장 | 이미지 분석 없이 위치 이름을 DB에 저장 |
| 위치목록 | 이미지 분석 없이 저장 위치 목록 반환 |
| 질문 | 현재 프레임과 tracker 상태를 합쳐 즉시 답변 |
| 찾기 | 특정 물체 위치 안내 |
| 색상 | 가장 중요한 물체의 색상 안내 *(실험 기능)* |
| 식사 | 식탁/음식 위치 중심 안내 *(실험 기능)* |
| 기본 | 장애물, hazard, scene, NLG 전체 흐름 |

기본 분석 흐름:

1. 이미지 bytes 읽기
2. GPS가 있으면 `db.save_gps()`
3. `detect_and_depth()` 호출
4. `tracker.update()`로 흔들림 보정
5. 이전 snapshot과 비교해 변화 감지
6. hazard가 있으면 `build_hazard_sentence()`
7. 일반 상황이면 `build_sentence()`
8. scene warning을 덧붙임
9. 반복 문장 suppress 후 응답

### `_build_meal_sentence()` *(실험 기능)*

식사 모드 전용 문장입니다. 음식/식기 위치만 짧게 말합니다. 발표 MVP 범위 밖.

### `_extract_find_target()`

찾기 명령에서 동사를 제거하고 대상 물체 이름만 남깁니다.

## 6. Vision/ML - 신유득

### `src/vision/detect.py:detect_objects()`

서버 YOLO 탐지의 핵심입니다.

처리 순서:

1. 이미지 bytes를 OpenCV 이미지로 변환
2. YOLO 추론 실행
3. 대상 class만 필터링
4. class별 confidence threshold 적용
5. bbox 중심으로 8시~4시 방향 계산
6. bbox 면적으로 대략 거리 계산
7. class, 거리, 방향, 바닥 여부로 risk score 계산
8. 색상/신호등/버스 crop 보조 정보 계산
9. scene 분석 생성
10. risk 상위 3개만 반환

주의:

- class별 threshold가 낮으면 오탐이 늘어난다.
- `distance_m`은 실제 측정값이 아니라 추정값이다.
- 신호등과 OCR은 실험 기능으로 설명한다.

### `_compute_scene_analysis()`

전체 탐지 결과를 보고 안전 방향, 군중 경고, 위험 물체, 신호등 메시지를 만든다.

### `_check_tactile_block_obstruction()`

화면 하단 중앙의 보행 경로 영역에 장애물이 있는지 확인합니다. 오탐 가능성이 있으므로 발표에서는 보조 기능으로 설명합니다.

### `src/depth/depth.py:detect_and_depth()`

YOLO와 Depth를 합치는 함수입니다.

처리 순서:

1. `detect_objects()`로 bbox 기반 객체 탐지
2. Depth V2 모델 파일이 있으면 `_infer_depth_map()` 실행
3. `_bbox_dist_m()`로 각 bbox 거리 보정
4. `detect_floor_hazards()`로 계단/낙차 후보 감지
5. 모델이 없으면 `depth_source = "bbox"`로 fallback

중요 표현:

- Depth V2가 있으면 "상대 깊이 기반 보조 추정"
- 없으면 "bbox 기반 fallback"

### `src/depth/hazard.py:detect_floor_hazards()`

Depth map을 12구역으로 나눠 바닥의 급격한 깊이 변화를 찾습니다. 계단/낙차 오탐이 있을 수 있으므로 실험 기능으로 둡니다.

## 7. DB와 tracker - 정환주

### `db.init_db()`

SQLite 또는 PostgreSQL/Supabase 모드에 맞춰 테이블을 생성합니다.

주요 테이블:

- `snapshots`: 공간별 최근 객체 상태
- `saved_locations`: 개인 위치 저장
- `gps_history`: 대시보드용 GPS 이동 기록

### `save_snapshot()`, `get_snapshot()`

공간별 최근 객체 목록을 저장하고 읽습니다. `save_snapshot()`은 공간별 최근 20개만 유지해 DB가 무한히 커지지 않도록 합니다.

### `save_gps()`, `get_gps_track()`

GPS 기록을 저장하고 대시보드에서 그릴 이동 경로를 반환합니다. 세션별 최근 200개만 유지합니다.

### `SessionTracker.update()`

객체가 프레임마다 조금씩 흔들리는 것을 줄이고, 접근/사라짐 변화를 감지합니다.

발표 설명:

```text
탐지 결과를 매 프레임 그대로 읽으면 음성이 너무 흔들립니다.
tracker가 최근 프레임을 부드럽게 이어서 같은 물체를 안정적으로 안내합니다.
```

## 8. NLG - 임명광

### `get_alert_mode()`

객체를 `critical`, `beep`, `silent`로 나눕니다.

기준:

- 차량/동물/바닥 위험이 가까우면 `critical`
- 멀리 있지만 주의가 필요하면 `beep`
- 말할 필요가 없으면 `silent`

### `build_sentence()`

일반 장애물 안내 문장을 만듭니다. 최대 2개 물체만 말해 음성 정보량을 줄입니다.

### `build_hazard_sentence()`

계단/낙차 같은 바닥 위험을 최우선으로 말합니다.

### `build_find_sentence()`

사용자가 찾는 물체가 있으면 방향과 거리를 말합니다. 없으면 카메라를 움직여 달라고 안내합니다.

### `build_question_sentence()`

"지금 뭐가 있어?" 같은 질문에 현재 프레임, hazard, tracker 상태를 합쳐 답합니다.

### `_josa()`, `_i_ga()`, `_eul_reul()`, `_un_neun()`

한국어 조사 자동화 함수입니다. 문장이 기계적으로 들리지 않게 만드는 핵심 보조 함수입니다.

## 9. Voice - 문수찬

### `src/voice/stt.py:_classify()`

인식된 문장을 키워드 기반으로 모드에 매핑합니다.

주의:

- Android 실제 사용은 `MainActivity.classifyKeyword()`가 중심입니다.
- 서버 STT는 Gradio/PC 테스트용입니다.

### `extract_label()`

"여기 저장해줘 회의실" 같은 문장에서 장소 이름만 추출합니다.

### `listen_and_classify()`

PC 마이크로 음성을 받아 Google Speech API로 텍스트를 얻습니다. Cloud Run에서는 마이크가 없으므로 실사용 경로가 아닙니다.

### `src/voice/tts.py`

서버 TTS 보조 모듈입니다. Android의 긴급 안내는 OS TTS가 우선입니다.

## 10. 역할별 공부 순서

| 담당 | 1단계 | 2단계 | 3단계 |
|---|---|---|---|
| 정환주 | `main.py` | `routes.py` | `db.py`, `templates/dashboard.html`, GCP 로그 |
| 신유득 | `detect.py` | `depth.py` | `benchmark.py`, 실패 케이스 |
| 김재현 | `MainActivity.kt` | `YoloDetector.kt` | UI XML, TalkBack |
| 임명광 | `sentence.py` | `SentenceBuilder.kt` | `tests/test_sentence.py` |
| 문수찬 | `stt.py`, `tts.py` | `MainActivity` 음성 함수 | Q&A 시트 |

## 11. 발표에서 조심할 말

| 말하지 않기 | 대신 말하기 |
|---|---|
| 정확한 거리 측정 | 대략적 거리 추정 |
| 안전하게 길을 안내 | 보행 보조 정보를 제공 |
| 신호등을 판단 | 신호등 색상을 보조적으로 안내 |
| 계단을 100% 감지 | 계단/낙차 후보를 실험적으로 감지 |
| 서버가 항상 필요 | 서버 없이도 온디바이스 fallback 가능 |
