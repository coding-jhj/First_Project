# FPS 10+ 팀원 지시 및 Dashboard/GPS 정환주 작업 메모

> 작성일: 2026-05-02  
> 목적: Android FPS 개선은 팀원에게 지시하고, Dashboard 지도/GPS 복구는 정환주가 직접 처리한다.  
> 원칙: 먼저 측정하고, 병목을 확인한 뒤, 작은 변경 단위로 검증한다.

## 결론 먼저

현재 상태에서 `INTERVAL_MS = 800L`이면 10fps가 절대 나올 수 없습니다.

```text
800ms 간격 = 이론상 최대 1.25fps
200ms 간격 = 이론상 최대 5fps
100ms 간격 = 이론상 최대 10fps
```

따라서 "fps가 낮고 왔다 갔다 한다"는 문제는 단순 성능 문제가 아니라 구조 문제입니다. 지금은 `ImageCapture`로 JPEG 파일을 찍고, 파일을 다시 decode하고, ONNX 추론 후 다음 프레임을 처리하는 흐름이라 안정적인 10fps에 불리합니다.

GPS 문제는 Android가 `lat/lng`를 `/detect`로 보내고 서버가 DB에 저장한 뒤 Dashboard가 `/status/{session_id}`를 polling하는 구조입니다. Dashboard가 GPS를 못 잡으면 아래 세 곳 중 하나입니다.

1. Android 위치 권한 또는 위치 provider 문제
2. Android가 계속 `0.0, 0.0`을 보내는 문제
3. 서버 DB 또는 Dashboard session id가 맞지 않는 문제

## 담당 분리

| 담당 | 할 일 |
|---|---|
| 김재현(Android) | FPS 루프, CameraX, ONNX 모델, Android 위치 권한/수집/전송 로그 확인 |
| 정환주(Server/Dashboard) | GPS가 서버에 저장되는지 확인하고 Dashboard session/지도 표시를 복구 |
| 신유득(Vision/ML) | 모델 경량화, threshold, yolo11n/yolo11m 선택 검증 |
| 임명광(NLG) | FPS 개선 후 문장/TTS 과다 출력 여부 확인 |

## 김재현에게 줄 FPS 작업 지시

아래 내용은 Android 담당 팀원에게 그대로 전달한다.

### 1. FPS 먼저 확인할 것

Android Logcat에서 아래 태그만 봅니다.

```text
VG_PERF
VG_FLOW
VG_LINK
```

확인할 로그:

```text
VG_PERF: request_id|...|route|on_device|decode|...|infer|...|dedup|...|total|...
VG_FLOW: capture skipped: previous frame still processing
```

1분 동안 실행하고 아래 값을 적습니다.

| 항목 | 기준 |
|---|---|
| 평균 FPS | 10 이상 |
| 최저 FPS | 8 아래로 자주 떨어지면 실패 |
| `total` | 100ms 이하가 목표 |
| `infer` | 70ms 이하가 목표 |
| `capture skipped` | 계속 나오면 파이프라인 병목 |

### 2. FPS 개선 우선순위

#### 1순위: yolo11m 대신 yolo11n을 앱 기본 모델로 사용

현재 assets에는 둘 다 있습니다.

```text
android/app/src/main/assets/yolo11m.onnx
android/app/src/main/assets/yolo11n.onnx
```

`YoloDetector.kt`는 `yolo11m.onnx`가 있으면 먼저 로드합니다. 그런데 `yolo11m.onnx`는 약 80MB이고, `yolo11n.onnx`는 약 10MB입니다. Android 실시간 10fps 목표라면 앱 기본값은 `yolo11n.onnx`여야 합니다.

팀원에게 지시:

```text
Android on-device 기본 모델은 yolo11n.onnx로 고정한다.
yolo11m.onnx는 서버 또는 정확도 비교용으로만 둔다.
```

완료 기준:

```text
VG_PERF에서 infer 시간이 yolo11m 대비 확실히 줄어든다.
1분 실행 중 FPS가 10 이상 유지된다.
```

#### 2순위: `INTERVAL_MS`를 100ms 이하로 낮추되, 무작정 낮추지 말 것

`MainActivity.kt`의 현재 값:

```kotlin
private const val INTERVAL_MS = 800L
```

10fps 목표면 100ms 이하가 필요합니다.

단, `total`이 100ms보다 크면 interval만 낮춰도 프레임 스킵이 늘어납니다. 그래서 순서는 다음과 같습니다.

1. `yolo11n`으로 바꾼다.
2. `VG_PERF total`이 100ms 이하인지 본다.
3. 그 다음 `INTERVAL_MS = 100L`을 시도한다.
4. `capture skipped`가 많으면 interval 문제가 아니라 처리 구조 문제로 본다.

#### 3순위: `ImageCapture` 파일 저장 루프를 `ImageAnalysis`로 바꾸기

현재 구조는 매 프레임을 임시 JPEG 파일로 저장하고 다시 읽습니다.

```text
CameraX ImageCapture
-> temp jpg 저장
-> BitmapFactory decode
-> EXIF 회전
-> ONNX
```

10fps 안정 목표에서는 이 구조가 흔들릴 수 있습니다. Android 담당자는 다음 구조로 바꿉니다.

```text
CameraX ImageAnalysis
-> 최신 ImageProxy만 유지
-> Bitmap 또는 ByteBuffer 변환
-> ONNX
-> 오래된 결과는 버림
```

반드시 지킬 것:

```text
STRATEGY_KEEP_ONLY_LATEST 사용
in-flight 추론은 최대 1개
TTS는 기존처럼 하나씩만 출력
request_id 또는 frameSeq로 최신 결과만 UI에 반영
```

### 3. FPS가 왔다 갔다 하는 원인별 조치

| 증상 | 원인 후보 | 조치 |
|---|---|---|
| FPS가 1~2 근처 | `INTERVAL_MS = 800L` | 100ms 목표로 조정 |
| FPS가 3~6에서 흔들림 | `yolo11m` 추론이 무거움 | 앱 기본 모델을 `yolo11n`으로 고정 |
| `capture skipped`가 많음 | 이전 프레임 처리 중 | ImageAnalysis + 최신 프레임만 처리 |
| `decode`가 큼 | JPEG 저장/회전 비용 | 파일 저장 제거 |
| `infer`가 큼 | ONNX 모델/스레드 병목 | 모델 경량화, thread 수 재측정 |
| `dedup`이 큼 | 후보 bbox 과다 | 후보 수 제한, threshold 조정 |

## 정환주 Dashboard/GPS 작업 메모

아래 내용은 팀원에게 맡기는 FPS 작업이 아니라 정환주가 직접 확인할 서버/Dashboard 작업이다.

### Android에서 먼저 확인

`MainActivity.kt`는 분석 시작 시 `requestLocationPermission { startGpsTracking() }`을 호출하고, `/detect`에 아래 값을 보냅니다.

```kotlin
.addFormDataPart("lat", currentLat.toString())
.addFormDataPart("lng", currentLng.toString())
```

문제는 `currentLat/currentLng` 기본값이 `0.0`이고, GPS가 잡히기 전에는 계속 `0.0`이 전송될 수 있다는 점입니다.

Android 담당에게 로그 확인만 요청할 것:

1. 앱 설정에서 위치 권한이 "허용"인지 확인한다.
2. Android 12 이상이면 "정확한 위치"가 켜져 있는지 확인한다.
3. 실내에서는 GPS만으로 안 잡힐 수 있으므로 실외에서 1분 테스트한다.
4. Logcat에 `VG_GPS` 태그를 추가해서 위치 수신 때마다 `lat/lng/provider/accuracy`를 출력한다.
5. `/detect` 요청 직전에도 `lat/lng`가 `0.0`인지 로그로 확인한다.

Android 쪽에서 위치값이 계속 `0.0`이면 Android 담당에게 요청할 수정 방향:

```text
GPS_PROVIDER만 쓰지 말고 FusedLocationProviderClient를 사용한다.
최소한 NETWORK_PROVIDER fallback을 추가한다.
lastKnownLocation은 GPS_PROVIDER와 NETWORK_PROVIDER를 둘 다 확인한다.
lat/lng가 0.0이면 서버에 저장하지 않거나 "GPS not ready" 상태를 UI에 표시한다.
```

### 정환주가 서버에서 확인할 것

서버는 `/detect`에서 `lat/lng`를 받고, 0이 아니면 저장합니다.

```python
if lat != 0.0 or lng != 0.0:
    db.save_gps(session_id, lat, lng)
```

확인 명령:

```bat
cd /d C:\VoiceGuide\VoiceGuide
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

브라우저 또는 curl로 확인:

```text
GET http://127.0.0.1:8000/health
GET http://127.0.0.1:8000/sessions
GET http://127.0.0.1:8000/status/__default__
GET http://127.0.0.1:8000/dashboard
```

판단 기준:

| 결과 | 의미 |
|---|---|
| `/health` 실패 | 서버 실행 또는 DB 초기화 문제 |
| `/sessions`가 빈 배열 | GPS가 DB에 저장되지 않음 |
| `/status/__default__`의 `gps`가 null | session id 불일치 또는 GPS 미저장 |
| `gps`가 있는데 지도만 안 움직임 | Dashboard JS/session 입력 문제 |

### 정환주가 Dashboard에서 확인할 것

서버는 `session_id = wifi_ssid or "__default__"`로 씁니다. Android가 WiFi SSID를 보내면 Dashboard에서 `__default__`가 아니라 해당 SSID session을 선택해야 합니다.

정환주 작업:

```text
Dashboard 오른쪽 위 session 검색 버튼을 누른다.
목록에 뜨는 session id를 선택한다.
직접 입력한다면 Android Logcat의 wifi_ssid 값과 정확히 맞춘다.
```

## 정환주 서버 복구 순서

1. 서버 실행 진입점이 `src.api.main:app`인지 확인한다. `app.py`나 `legacy/server_db*`를 실행하지 않는다.
2. `/health`가 `status: ok` 또는 `degraded`라도 JSON으로 나오는지 확인한다.
3. Android 설정의 서버 URL이 `/detect`를 붙이지 않은 base URL인지 확인한다.
   - 예: `http://192.168.0.10:8000`
   - 예: `https://...run.app`
4. Android와 서버가 같은 네트워크에 있는지 확인한다.
5. 로컬 서버라면 PC 방화벽에서 8000 포트를 허용한다.
6. Cloud Run이면 배포 URL의 `/health`와 `/dashboard`가 브라우저에서 열리는지 확인한다.
7. Android Logcat `VG_LINK`에서 HTTP status와 `total/server/net` 시간을 본다.

## 최종 완료 기준

FPS 완료:

- [ ] 앱 기본 ONNX 모델이 `yolo11n.onnx`이다.
- [ ] `INTERVAL_MS` 또는 ImageAnalysis 구조상 10fps가 가능한 상태다.
- [ ] 1분 실행 평균 FPS가 10 이상이다.
- [ ] 최저 FPS가 반복적으로 8 아래로 떨어지지 않는다.
- [ ] `VG_PERF`에서 `decode/infer/dedup/total` 병목을 설명할 수 있다.
- [ ] TTS가 겹치지 않는다.

GPS/Dashboard 완료: 정환주 담당

- [ ] Android Logcat에서 실제 `lat/lng`가 `0.0`이 아닌 값으로 찍힌다.
- [ ] `/detect` 서버 로그에 같은 `lat/lng`가 찍힌다.
- [ ] `/sessions`에 Android session id가 보인다.
- [ ] `/status/{session_id}`의 `gps`가 null이 아니다.
- [ ] `/dashboard`에서 같은 session id를 선택하면 지도 marker가 이동한다.

## 김재현에게 줄 한 줄 FPS 지시

```text
FPS는 yolo11n 고정 + 100ms 이하 캡처 주기 + ImageAnalysis 최신 프레임 처리로 10fps를 맞춰 주세요. GPS/Dashboard는 정환주가 서버와 화면 쪽에서 따로 처리합니다.
```
