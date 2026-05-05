# VoiceGuide Function Deep Dive

목적: 팀원이 코드를 함수 단위로 뜯어서 공부하고, "이 함수가 왜 있고 어디로 이어지는지" 설명할 수 있게 만든다.

현재 발표 MVP는 아래 3개다.

| MVP | 핵심 경로 |
|---|---|
| 장애물 안내 | Android `captureAndProcess()` -> `processOnDevice()` 또는 서버 `/detect` -> 문장/TTS |
| 물건찾기 | STT `찾기` 모드 -> target 추출 -> `buildFind()` 또는 `build_find_sentence()` |
| 물건 확인 | STT `확인`/질문 흐름 -> 현재 프레임의 주요 물체 설명 |

## 1. 전체 파일 지도

| 파일 | 역할 | 우선순위 |
|---|---|---|
| `android/.../MainActivity.kt` | 앱 전체 흐름, 카메라, STT, TTS, 서버 fallback | P0 |
| `android/.../YoloDetector.kt` | Android ONNX 객체 탐지 | P0 |
| `android/.../SentenceBuilder.kt` | Android 온디바이스 문장 생성 | P0 |
| `android/.../BoundingBoxOverlay.kt` | bbox 화면 표시 | P1 |
| `android/.../StairsDetector.kt` | 온디바이스 계단 후보 보조 감지 | P2 |
| `android/.../VoiceGuideConstants.kt` | 클래스명, 키워드, 상수 | P0 |
| `src/api/main.py` | FastAPI 앱 생성, health, 시작/종료 처리 | P0 |
| `src/api/routes.py` | `/detect`, `/status`, `/dashboard`, 서버 API | P0 |
| `src/api/db.py` | snapshot, location, GPS 저장/조회 | P1 |
| `src/api/tracker.py` | 객체 추적, voting, 현재 상태 | P1 |
| `src/vision/detect.py` | 서버 YOLO 탐지, 방향/위험도/scene 분석 | P0 |
| `src/depth/depth.py` | YOLO+Depth 결합, bbox fallback | P1 |
| `src/depth/hazard.py` | 계단/낙차 후보 감지 | P2 |
| `src/nlg/sentence.py` | 서버 문장 생성 | P0 |
| `src/nlg/templates.py` | 카메라 방향 보정, 방향 템플릿 | P1 |
| `src/voice/stt.py` | PC/서버용 STT 보조 | P2 |
| `src/voice/tts.py` | 서버 TTS 보조 | P2 |
| ~~`src/ocr/bus_ocr.py`~~ | ~~버스 번호 OCR 실험 기능~~ → **제거됨** (`legacy/ocr_src/`) | — |
| `src/vision/gpt_vision.py` | 옷 매칭/패턴 실험 기능 | P2 |
| `templates/dashboard.html` | 서버 대시보드 화면 | P1 |
| `tools/*.py` | 검증/벤치마크/배포 확인 도구 | P1 |
| `tests/*.py` | 서버/문장/탐지 회귀 테스트 | P1 |

## 2. Android 앱

### `MainActivity.kt`

앱의 중심 파일이다. 발표 MVP 3개를 실제로 묶는 파일이므로 김재현은 이 파일을 가장 먼저 설명할 수 있어야 한다.

| 함수 | 입력 | 출력/부작용 | 연결되는 다음 함수 | 공부 포인트 |
|---|---|---|---|---|
| `onCreate()` | Android lifecycle `Bundle` | UI, TTS, STT, 센서, 버튼 초기화 | `tryInitYoloDetector()`, `startCamera()` | 앱 시작 시 무엇이 준비되는지 |
| `tryInitYoloDetector()` | 없음 | ONNX detector 생성 또는 실패 처리 | `shouldUseOnDeviceDetector()` | 모델 asset이 없을 때 fallback |
| `requestPermissions()` | 없음 | CAMERA/RECORD_AUDIO 요청 | `startCamera()` | 처음부터 SMS/GPS를 묻지 않아야 함 |
| `showSettingsDialog()` | 없음 | 서버 URL/API key 저장 UI 표시 | `getSavedServerUrl()` | GCP URL 입력 위치 |
| `getSavedServerUrl()` | 없음 | 저장된 서버 URL 문자열 | `sendToServer()` | 마지막 `/` 처리 확인 |
| `withSavedApiKey()` | OkHttp Request Builder | `X-API-Key` 헤더 추가 | 서버 API 호출 | API_KEY 설정 시 필요 |
| `onResume()` | lifecycle | 센서/자동 listen 재시작 | `scheduleAutoListen()` | 앱 복귀 후 상태 복원 |
| `onPause()` | lifecycle | 센서/분석 일시 중지 | `stopAnalysis()` | 백그라운드 발열 방지 |
| `onDestroy()` | lifecycle | TTS, detector, recognizer 정리 | 없음 | 리소스 누수 방지 |
| `onSensorChanged()` | 센서 이벤트 | 카메라 방향 갱신 | 서버 `camera_orientation` | 방향 안내 좌우 반전 방지 |
| `initSpeechRecognizer()` | 없음 | STT listener 구성 | `handleSttResult()` | 음성 명령이 어디로 들어오는지 |
| `startListening()` | 없음 | STT 시작 | `handleSttResult()` | TTS 중 STT 충돌 주의 |
| `handleSttResult(text)` | 인식된 한국어 문장 | 모드 분기, 즉시 캡처/저장/질문 처리 | `classifyKeyword()`, `captureAndProcessAsQuestion()` | MVP 3개 명령어 분기 |
| `classifyKeyword(text)` | STT 문장 | `장애물`, `찾기`, `확인` 등 모드 | `handleSttResult()` | 3개 MVP 키워드 우선순위 |
| `startCamera()` | 없음 | CameraX preview/imageCapture 준비 | `captureAndProcess()` | 카메라가 준비되어야 분석 가능 |
| `startAnalysis()` | 없음 | 분석 루프 시작 | `scheduleNext()` | 시작 시 history 초기화 여부 |
| `stopAnalysis()` | 없음 | 분석 루프 중지 | 없음 | 중지 후 백그라운드 결과 무시 |
| `scheduleNext()` | 없음 | 다음 캡처 예약 | `captureAndProcess()` | `INTERVAL_MS`가 FPS 상한을 만듦 |
| `scheduleWatchdog()` | 없음 | 무응답 감시 | `handleFail()` | 분석이 멈췄을 때 사용자 경고 |
| `captureAndProcess()` | 없음 | 사진 저장 후 분석 경로 선택 | `processOnDevice()` 또는 `sendToServer()` | `isSending` 직렬 병목 핵심 |
| `nextRequestId()` | 없음 | `and-...` request_id | `sendToServer()` | GCP 로그와 매칭할 키 |
| `shouldUseOnDeviceDetector()` | 없음 | boolean | `processOnDevice()` | 장애물/찾기/확인은 온디바이스 우선 |
| `processOnDevice(file, requestId)` | 이미지 파일, request id | Android 자체 탐지/문장/TTS | `YoloDetector.detect()`, `SentenceBuilder.build()` | 서버 없이 MVP가 도는 핵심 |
| `sendToServer(file, requestId)` | 이미지 파일, request id | `/detect` 호출 | 서버 `routes.detect()` | GCP 연동 증명은 `VG_LINK` |
| `sendToServerWithMode(file, mode, requestId)` | 이미지, 모드 | 특정 모드 서버 호출 | 서버 `routes.detect()` | 질문/색상 등 서버 모드 |
| `optimizeImageForUpload(file)` | 원본 이미지 | 리사이즈/압축 이미지 | `sendToServer()` | 네트워크 지연 감소 |
| `decodeBitmapUpright(file)` | 이미지 파일 | 회전 보정 bitmap | `processOnDevice()` | EXIF 회전 버그 방지 |
| `voteOnly(detections)` | 탐지 목록 | 안정화된 탐지 목록 | `classify()` | 순간 오탐 제거 |
| `classify(voted)` | voting 결과 | 음성 대상 목록 + beep 여부 | `SentenceBuilder.build()` | 가까운 물체/멀리 물체 분리 |
| `removeDuplicates(detections)` | 탐지 목록 | 중복 bbox 제거 | `voteOnly()` | 같은 물체가 여러 번 말해지는 문제 방지 |
| `iouOverlap(a,b)` | bbox 2개 | IoU 값 | `removeDuplicates()` | NMS와 비슷한 중복 판단 |
| `handleSuccess(sentence, alertMode)` | 문장, 알림 모드 | UI 업데이트, TTS/비프 처리 | `speak()` | TTS 겹침 방지의 마지막 관문 |
| `handleFail()` | 없음 | 실패 횟수 증가, fallback 안내 | `scheduleNext()` | 서버 실패와 탐지 실패를 구분 |
| `speak(text)` | 문장 | STT 중단 후 TTS 경로 선택 | `speakBuiltIn()` | Android OS TTS 우선 |
| `speakBuiltIn(text, immediate)` | 문장, 즉시 여부 | Android TTS 발화 | `onInit()` listener | `ttsBusy` 잠금 확인 |
| `isSpeaking()` | 없음 | TTS busy 여부 | `handleSuccess()` | race condition 방지 |
| `calcFps()` | 없음 | FPS 문자열 | debug UI | 1.4fps 같은 병목 확인 |
| `getWifiSsid()` | 없음 | WiFi SSID/session id | 서버 form `wifi_ssid` | 대시보드 session mismatch 원인 |
| `saveLocation()`, `getLocations()`, `findNearbyLocation()` | label/ssid | SharedPreferences 위치 저장/조회 | 위치목록/저장 모드 | 현재 MVP 밖, 실험/보조 |
| ~~`captureForOcr()`, `captureForBarcode()`~~ | ~~없음~~ | ~~OCR/바코드 실행~~ | — | **제거됨** (ML Kit 의존성 삭제) |
| `triggerSOS()`, `scheduleFallCheck()` | 없음 | SMS/SOS 흐름 | 권한 요청 | 현재 MVP 밖 |
| `startGpsTracking()`, `stopGpsTracking()` | 없음 | GPS 업데이트 | 서버 `/detect` lat/lng | 대시보드 데이터 생성 조건 |

MVP 3개 관점에서 먼저 볼 경로:

```text
장애물 안내:
handleSttResult("주변 알려줘")
  -> classifyKeyword()
  -> captureAndProcess()
  -> processOnDevice()
  -> SentenceBuilder.build()
  -> handleSuccess()

물건찾기:
handleSttResult("가방 찾아줘")
  -> extractFindTarget()
  -> captureAndProcess()
  -> SentenceBuilder.buildFind()

물건 확인:
handleSttResult("이거 뭐야")
  -> captureAndProcessAsQuestion() 또는 captureAndProcess()
  -> 가장 가까운/중앙 물체 설명
```

### Android 보조 파일

| 파일/함수 | 역할 | 공부 포인트 |
|---|---|---|
| `YoloDetector.detect(bitmap)` | Android ONNX 추론 전체 | 전처리 -> session 실행 -> 후처리 |
| `YoloDetector.bitmapToNCHW()` | bitmap을 모델 입력 tensor로 변환 | RGB 정규화, NCHW 순서 |
| `YoloDetector.postProcess()` | ONNX output을 bbox/class로 변환 | conf threshold, 좌표 변환 |
| `YoloDetector.nms()` / `iou()` | 중복 bbox 제거 | 오탐/중복 탐지와 연결 |
| `YoloDetector.close()` | ONNX session 해제 | lifecycle |
| `SentenceBuilder.build()` | 일반 장애물 문장 | 장애물 안내 MVP |
| `SentenceBuilder.buildFind()` | 특정 물체 찾기 문장 | 물건찾기 MVP |
| `SentenceBuilder.getClock()` | bbox x -> 시계방향 | 방향 안내 |
| `SentenceBuilder.formatDist()` | bbox 크기 -> 대략 거리 | 거리 표현 과장 금지 |
| `SentenceBuilder.extractFindTarget()` | 찾기 명령에서 물체 추출 | "가방 찾아줘" |
| `SentenceBuilder.josa*()` | 한국어 조사 | 자연스러운 TTS |
| `BoundingBoxOverlay.setDetections()` | 화면 bbox 갱신 | 좌표계 mismatch 확인 |
| `BoundingBoxOverlay.clearDetections()` | bbox 제거 | 잔상 방지 |
| `BoundingBoxOverlay.onDraw()` | bbox와 label 그리기 | 발표 화면 복잡도 |
| `StairsDetector.detect()` | 계단 후보 탐지 | 실험 기능 |
| `VoiceGuideConstants.kt` | class/keyword 상수 | Android와 서버 class 이름 일치 |

## 3. 서버 API

### `src/api/main.py`

| 함수 | 입력 | 출력/부작용 | 공부 포인트 |
|---|---|---|---|
| `lifespan(app)` | FastAPI app | DB init + 4개 워밍업 스레드 시작 | 전부 백그라운드 — Cloud Run 타임아웃 방지 |
| `_warmup_yolo()` | 없음 | YOLO 더미 추론으로 JIT 완료 | 실패해도 서버 유지, 백그라운드 스레드 |
| `_warmup_depth()` | 없음 | Depth V2 모델 로드 | 실패해도 서버 유지, 백그라운드 스레드 |
| `_warmup_ocr()` | 없음 | OCR reader 미리 로드 | 실험 기능, 실패해도 서버 유지 |
| `_warmup_tts()` | 없음 | TTS cache warmup | 서버 TTS 보조 |
| `health()` | HTTP GET | 상태 JSON | GCP 정상 확인 1순위 |
| `_check_db()` | 없음 | `ok` 또는 오류 문자열 | SQLite/PostgreSQL 상태 |
| `global_exception_handler()` | request, exception | fallback JSON | Android가 오류도 문장으로 받을 수 있게 함 |

### `src/api/routes.py`

| 함수 | 입력 | 출력 | 다음 연결 | 공부 포인트 |
|---|---|---|---|---|
| `_verify_api_key()` | headers | 통과 또는 401 | 모든 보호 API | GCP 공개 배포 보안 |
| `_with_perf(payload,t0,request_id,...)` | 응답 payload | perf 필드 추가 JSON | Android/GCP 로그 | request_id 매칭 핵심 |
| `_should_suppress(session_id,sentence,alert_mode)` | 세션/문장/모드 | suppress boolean | `detect()` | 반복 TTS 억제 |
| `_space_changes(current,previous)` | 현재/이전 객체 | 변화 문장 list | `detect()` | 공간 기억, MVP 밖 |
| `detect(...)` | multipart image/mode/gps/request_id | 분석 JSON | Android `sendToServer()` | 서버 메인 API |
| `_build_meal_sentence(objects)` | objects | 식사 안내 문장 | 식사 모드 | 실험 기능 |
| `_extract_find_target(text)` | STT text | target label | 찾기 모드 | 물건찾기 서버 경로 |
| `tts_endpoint(text)` | form text | mp3 file | Android/Gradio | 서버 TTS 보조 |
| `vision_clothing(image,type)` | image/type | 문장 JSON | GPT vision | 실험 기능 |
| `ocr_bus(image,bus_crop)` | image/crop | 버스 번호 JSON | Android bus OCR | 실험 기능 |
| `save_location_endpoint()` | wifi,label | 저장 결과 | DB | MVP 밖 |
| `list_locations()` | wifi | 장소 목록 | DB | MVP 밖 |
| `find_location_endpoint()` | label,wifi | 장소 검색 결과 | DB | MVP 밖 |
| `delete_location_endpoint()` | label | 삭제 결과 | DB | MVP 밖 |
| `get_session_status(session_id)` | session id | objects/gps/track | dashboard | 대시보드 빈 화면 원인 확인 |
| `dashboard()` | 없음 | HTML | browser | `/dashboard` 200 OK 확인 |
| `save_space_snapshot(body)` | JSON body | saved true | DB | 테스트/디버그 |
| `stt_listen()` | 없음 | STT 결과 | PC demo | Cloud Run 실사용 아님 |

`detect()` 내부 흐름:

```text
1. request_id 생성 또는 수신
2. mode가 저장/위치목록이면 이미지 분석 없이 DB 처리
3. image bytes 읽기
4. lat/lng 있으면 save_gps()
5. detect_and_depth()
6. tracker.update()
7. snapshot 변화 비교
8. mode별 문장 생성
9. scene warning 추가
10. 중복 문장 suppress
11. _with_perf()로 request_id/process_ms/perf 추가
```

### `src/api/db.py`

| 함수 | 역할 | 실패 시 영향 |
|---|---|---|
| `_get_pool()` | PostgreSQL pool 생성 | Supabase 사용 시 필요 |
| `_conn()` | SQLite/PostgreSQL connection 반환 | 모든 DB 작업의 입구 |
| `init_db()` | DB 모드에 맞게 table 생성 | 서버 시작 실패 가능 |
| `_init_sqlite()` | SQLite table 생성 | 로컬/GCP 기본 |
| `_init_postgres()` | PostgreSQL table 생성 | Supabase 선택 |
| `get_snapshot()` / `save_snapshot()` | 공간별 객체 상태 조회/저장 | 공간 기억 |
| `save_location()` / `delete_location()` | 장소 저장/삭제 | 실험 기능 |
| `get_locations()` / `find_location()` | 장소 목록/검색 | 위치 기능 |
| `save_gps()` | GPS 기록 저장 | 대시보드 지도 |
| `get_last_gps()` / `get_gps_track()` | 현재 위치/이동 경로 | 대시보드 |

### `src/api/tracker.py`

| 클래스/함수 | 역할 | 공부 포인트 |
|---|---|---|
| `VotingBuffer` | 최근 프레임 다수결 | 오탐과 반응속도 trade-off |
| `SessionTracker` | 세션별 객체 상태 관리 | `/status/{session_id}` 데이터 원천 |
| `SessionTracker.update(objects)` | 객체 smoothing/변화 감지 | distance EMA, 접근 감지 |
| `SessionTracker.get_current_state()` | 최근 객체 조회 | 대시보드/질문 모드 |
| `get_tracker(session_id)` | tracker singleton 반환 | WiFi/session 단위 분리 |

## 4. Vision/ML

| 파일/함수 | 입력 | 출력 | 공부 포인트 |
|---|---|---|---|
| `detect.py:_detect_color()` | 이미지 crop 좌표 | 색상명 | 색상은 실험 기능 |
| `detect.py:_detect_traffic_light_color()` | 신호등 crop | 빨강/초록 등 | 발표에서 보장 금지 |
| `detect.py:detect_objects()` | JPEG bytes | `(objects, scene)` | 서버 탐지 핵심 |
| `detect.py:_check_tactile_block_obstruction()` | detections/scene/크기 | scene warning 수정 | 실험 기능 |
| `detect.py:_compute_scene_analysis()` | 객체 목록 | scene dict | 군중/위험물/안전방향 |
| `depth.py:_check_model()` | 없음 | bool | Depth 없으면 bbox fallback |
| `depth.py:_load_model()` | 없음 | torch model | 실패해도 서버 유지 |
| `depth.py:_infer_depth_map()` | 이미지 | depth map/None | Depth V2 실행 |
| `depth.py:_bbox_dist_m()` | depth map+bbox | 거리 추정값 | 대략 거리 |
| `depth.py:detect_and_depth()` | image bytes | objects, hazards, scene | YOLO+Depth 통합 |
| `hazard.py:detect_floor_hazards()` | depth map | hazard list | 계단/낙차 후보, 실험 기능 |
| `bus_ocr.py:recognize_bus_number()` | image bytes/crop | bus number/None | OCR 실험 기능 |
| `gpt_vision.py:analyze_clothing()` | image bytes/type | 문장 | 옷 매칭 실험 기능 |

`detect_objects()` 공부 순서:

```text
bytes -> cv2 image
YOLO predict
class별 threshold
bbox 정규화
direction 계산
distance_m 추정
risk_score 계산
color/traffic 보조
scene 분석
위험도 상위 객체 반환
```

## 5. NLG

| 함수 | 입력 | 출력 | MVP 연결 |
|---|---|---|---|
| `get_alert_mode(obj,is_hazard)` | 객체/위험 여부 | `critical/beep/silent` | TTS 정책 |
| `_josa()`, `_i_ga()`, `_eul_reul()`, `_un_neun()` | 단어 | 조사 | 한국어 자연화 |
| `_format_dist(dist_m)` | 거리 숫자 | "약 1미터" | 대략 거리 |
| `_primary(obj,abs_clock)` | 1순위 객체 | 핵심 문장 | 장애물 안내 |
| `_secondary(obj,abs_clock)` | 보조 객체 | 짧은 추가 문장 | 정보량 제한 |
| `build_sentence(objects,changes,camera_orientation)` | 객체/변화/방향 | 일반 안내 문장 | 장애물 안내 |
| `build_hazard_sentence(...)` | hazard | 위험 문장 | 실험/보조 |
| `build_find_sentence(target,objects,orientation)` | 찾을 물체/객체 | 찾기 문장 | 물건찾기 |
| `build_question_sentence(...)` | 현재/추적 상태 | 질문 답변 | 물건 확인 |
| `build_navigation_sentence(...)` | 위치 정보 | 저장/목록 문장 | MVP 밖 |
| `templates.get_absolute_clock()` | image clock/orientation | 보정 clock | 카메라 방향 보정 |

## 6. Voice

| 파일/함수 | 역할 | 현재 기준 |
|---|---|---|
| `stt.py:_classify(text)` | PC STT 문장을 모드로 분류 | Android 실사용은 `MainActivity` 중심 |
| `stt.py:extract_label(text)` | 저장 label 추출 | 위치 저장 보조 |
| `stt.py:listen_and_classify()` | PC 마이크 STT | Cloud Run 실사용 아님 |
| `tts.py:_cache_path(text)` | 문장별 mp3 cache path | 서버 TTS 보조 |
| `tts.py:_generate(text,path)` | 음성 생성 | Android 긴급 안내는 OS TTS |
| `tts.py:speak(text)` | PC에서 음성 재생 | Gradio/로컬 demo |
| `tts.py:warmup_cache()` | 자주 쓰는 문장 미리 생성 | 서버 시작 보조 |

## 7. Dashboard

| JS 함수/영역 | 역할 | 서버 연결 |
|---|---|---|
| `POLL_MS`, `SERVER_BASE` | 2초 폴링 설정 | 현재 origin 사용 |
| `renderObjects(objects)` | 왼쪽 객체 카드 렌더링 | `/status/{session_id}.objects` |
| `renderGps(gps,track)` | 지도 marker/path 표시 | `/status/{session_id}.gps/track` |
| `poll()` | status API 반복 호출 | `GET /status/{session_id}` |
| `showToast(msg)` | 새 탐지 toast | objects count 변화 |
| `sessionId change listener` | 세션 변경 시 지도 초기화 | Android `wifi_ssid`와 맞춰야 함 |

대시보드가 비어 보이는 원인:

```text
/dashboard = HTML은 정상
/status/__default__ = 200 OK
하지만 objects=[], gps=null, track=[] 이면 표시할 내용이 없다.
```

## 8. Tools와 Tests

| 파일 | 함수/테스트 | 용도 |
|---|---|---|
| `tools/probe_server_link.py` | `main()` | GCP `/detect`, `/status`, `/dashboard` 상관 확인 |
| `tools/benchmark.py` | `bench_response_time()` | 전체 응답 시간 측정 |
| `tools/benchmark.py` | `bench_detection_pipeline()` | 탐지 pipeline 시간 측정 |
| `tools/benchmark.py` | `bench_direction_accuracy()` | 방향 계산 검증 |
| `tools/benchmark.py` | `bench_sentence_generation()` | NLG 속도/결과 검증 |
| `tools/benchmark.py` | `bench_precision_recall()` | 테스트 이미지 평가 |
| `tools/benchmark.py` | `bench_depth_model()` | Depth 모델 상태 |
| `tests/test_server.py` | `/health`, `/detect`, `/status`, `/dashboard` | 서버 회귀 테스트 |
| `tests/test_sentence.py` | 문장 생성 tests | NLG 회귀 테스트 |
| `tests/test_detect.py` | 탐지 schema tests | Vision 회귀 테스트 |
| `tests/test_api.py` | API/security tests | API key와 endpoint |
| `tests/test_imports.py` | import tests | 의존성 확인 |

## 9. 함수 공부 템플릿

각자 자기 파일에서 아래 5문장을 채워야 한다.

```text
1. 이 함수의 입력은 무엇이다.
2. 이 함수의 출력 또는 부작용은 무엇이다.
3. 이 함수가 실패하면 사용자에게 어떤 문제가 생긴다.
4. 이 함수 다음에는 어떤 함수가 호출된다.
5. 발표에서는 이 함수를 이렇게 설명한다.
```

예시:

```text
MainActivity.processOnDevice()
1. 입력: 캡처된 이미지 파일과 request_id.
2. 출력/부작용: ONNX 탐지, 문장 생성, UI/TTS 업데이트.
3. 실패하면 서버 fallback 또는 handleFail로 이어진다.
4. YoloDetector.detect -> SentenceBuilder.build -> handleSuccess.
5. 서버 없이도 기본 장애물 안내가 되는 핵심 함수라고 설명한다.
```

## 10. 현재 최우선 디버깅 포인트

| 문제 | 먼저 볼 함수 |
|---|---|
| FPS 1.4fps | `captureAndProcess`, `processOnDevice`, `YoloDetector.detect`, `calcFps` |
| 대시보드 빈 화면 | `getWifiSsid`, `sendToServer`, `db.save_gps`, `get_session_status`, dashboard `poll()` |
| 물건찾기 실패 | `classifyKeyword`, `extractFindTarget`, `SentenceBuilder.buildFind`, `build_find_sentence` |
| 물건 확인이 어색함 | `handleSttResult`, `build_question_sentence`, `SentenceBuilder.build` |
| 오탐 많음 | `YoloDetector.postProcess`, `removeDuplicates`, `voteOnly`, `detect_objects` |
| TTS 겹침 | `handleSuccess`, `speak`, `speakBuiltIn`, `isSpeaking` |
