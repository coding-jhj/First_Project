# Android FPS and False Positive Guide

> 담당: 김재현  
> 협업: 신유득(Vision/ML), 임명광(NLG), 문수찬(Voice)  
> 원칙: 정환주가 직접 고치는 것이 아니라, Android 담당자가 병목을 측정하고 단계별로 개선한다.

## 왜 지금 이 작업이 중요한가

현재 앱은 기능이 많아지면서 FPS가 낮고 오탐도 많습니다. 시각장애인 보행 보조 앱에서 낮은 FPS는 단순히 화면이 끊기는 문제가 아니라, 사용자가 장애물을 늦게 듣는 문제입니다.

목표는 "무조건 20fps"가 아닙니다. 실제 기기에서 안정적으로 쓸 수 있는 최소 기준을 먼저 맞춥니다.

| 등급 | 기준 | 판단 |
|---|---|---|
| 위험 | 3fps 미만 | 보행 시연 부적합 |
| 경계 | 3~5fps | 실내 천천히만 가능 |
| 최소 목표 | 5fps 이상 | 발표 시연 가능 |
| 권장 목표 | 8~10fps | 안정적 시연 가능 |

## 먼저 측정할 것

Logcat에서 `VG_PERF`를 봅니다.

```text
VG_PERF: request_id|...|route|on_device|decode|...|infer|...|dedup|...|total|...
VG_PERF: request_id|...|route|server|server_ms|...|net_ms|...|total|...
```

| 값 | 의미 | 조치 |
|---|---|---|
| `decode`가 큼 | 이미지 읽기/회전/리사이즈 병목 | 캡처 해상도와 bitmap 변환 확인 |
| `infer`가 큼 | ONNX 추론 병목 | 모델 크기, thread, NNAPI 여부 확인 |
| `dedup`이 큼 | bbox 후처리 병목 | 후보 수 제한, NMS 조건 확인 |
| `net_ms`가 큼 | 서버 왕복 지연 | Cloud Run 단독 보행 모드 지양 |
| `server_ms`가 큼 | 서버 모델/Depth 병목 | Depth 주기, 모델 warmup 확인 |

## 현재 의심 병목

### 1. 캡처 간격 자체가 FPS 상한을 만든다

`MainActivity.kt`의 `INTERVAL_MS`가 크면 실제 추론이 빨라도 FPS가 안 나옵니다.

예:

```text
INTERVAL_MS = 800ms -> 이론상 최대 1.25fps
INTERVAL_MS = 200ms -> 이론상 최대 5fps
INTERVAL_MS = 100ms -> 이론상 최대 10fps
```

주의: 값을 낮추기만 하면 발열과 배터리가 커집니다. 먼저 `infer/total`을 보고 결정합니다.

### 2. `isSending` 하나가 전체 파이프라인을 직렬화한다

현재 흐름은 이전 프레임 처리가 끝나야 다음 프레임 캡처가 시작됩니다.

```text
capture -> decode -> infer -> postprocess -> sentence -> TTS decision -> next capture
```

이 구조는 안전하지만 FPS가 낮습니다. 개선 방향은 "무제한 병렬"이 아니라 "최대 2프레임만 동시에 처리"입니다.

권장 구조:

```text
Camera producer
  -> 최신 프레임만 큐에 넣기

Inference worker
  -> 최대 1~2개 프레임만 처리
  -> 오래된 프레임은 버림

TTS/UI consumer
  -> 최신 결과만 반영
  -> TTS는 반드시 하나씩만 재생
```

## 병렬화 지침

### 하면 좋은 것

- 캡처와 추론을 분리한다.
- inference executor를 별도로 둔다.
- 동시에 처리할 프레임 수는 2개 이하로 제한한다.
- 새 결과가 도착했을 때 더 오래된 결과는 UI/TTS에 반영하지 않는다.
- `request_id` 또는 frame number로 최신 결과인지 확인한다.

### 하면 안 되는 것

- 프레임마다 `Thread { ... }.start()`를 무제한 생성하지 않는다.
- TTS를 병렬 재생하지 않는다.
- 서버 요청을 여러 개 동시에 날려 Cloud Run 지연을 키우지 않는다.
- FPS 때문에 `VOTE_MIN_COUNT`를 무조건 1로 낮추지 않는다.
- 오탐을 숨기려고 bbox를 안 그리는 방식으로 해결하지 않는다.

## 김재현이 볼 함수

| 파일 | 함수 | 봐야 할 점 |
|---|---|---|
| `MainActivity.kt` | `scheduleNext()` | 캡처 주기와 다음 프레임 예약 방식 |
| `MainActivity.kt` | `captureAndProcess()` | `isSending` 때문에 프레임이 얼마나 스킵되는지 |
| `MainActivity.kt` | `processOnDevice()` | decode/infer/dedup 중 어디가 느린지 |
| `MainActivity.kt` | `sendToServer()` | Cloud Run 왕복 지연과 fallback |
| `MainActivity.kt` | `handleSuccess()` | TTS 겹침 방지와 최신 결과 반영 |
| `YoloDetector.kt` | `detect()` | ONNX 추론 시간 |
| `YoloDetector.kt` | `postProcess()` | 후보 bbox 수와 NMS 비용 |

## 오탐 개선 지침

오탐은 Android와 Vision/ML이 같이 봐야 합니다.

| 문제 | 담당 | 조치 |
|---|---|---|
| 작은 물체가 계속 튐 | 김재현 | voting, cooldown, bbox 면적 기준 확인 |
| 특정 class가 자주 오탐 | 신유득 | class별 confidence threshold 조정 |
| 같은 물체 bbox가 여러 개 | 김재현 | NMS, `removeDuplicates()` 확인 |
| 생활 물체에 위험 경고 | 임명광 | `alert_mode`, 문장 정책 조정 |
| 음성이 너무 자주 나옴 | 김재현, 문수찬 | TTS cooldown, `silent/beep/critical` 확인 |

## 실험 순서

1. 현재 상태에서 1분 실행하고 `VG_PERF` 로그를 저장한다.
2. 평균 FPS, `decode`, `infer`, `dedup`, `total`을 표로 적는다.
3. `INTERVAL_MS`를 낮추기 전에 `total`이 200ms 이하인지 확인한다.
4. `total`이 400ms 이상이면 병렬화보다 모델 경량화/후처리 축소가 먼저다.
5. 병렬화는 최대 2프레임 in-flight로 제한한다.
6. 오탐 이미지를 5개 모아 신유득에게 threshold 조정을 요청한다.
7. 변경 후 같은 장소에서 다시 1분 실행해 전후 비교한다.

## 완료 기준

- [ ] 앱 화면 또는 Logcat에서 실제 FPS를 확인했다.
- [ ] 1분 실행 평균 FPS가 5 이상이다.
- [ ] `VG_PERF`로 병목 단계가 설명된다.
- [ ] TTS가 겹치지 않는다.
- [ ] 오탐 사례 5개와 조치 결과가 남아 있다.
- [ ] 김재현이 `captureAndProcess()`부터 `handleSuccess()`까지 직접 설명할 수 있다.
