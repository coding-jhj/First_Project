# OBB Bounding Box And FPS Analysis

작성일: 2026-05-05  
대상 커밋: `5d355bb Enable on-device OBB routing`  
범위: 코드 수정 없이, 최근 merge 내용 기준으로 OBB 바운딩 박스 오차와 FPS 저하 가능 원인 분석

## 결론 요약

현재 문제는 단순히 "OBB가 잘못됐다" 하나로 보기 어렵다. 실제로는 아래 세 가지가 동시에 얽혀 있다.

1. 앱에 실제 OBB ONNX 모델이 들어있지 않을 가능성이 크다.
2. 카메라 Preview 화면과 분석에 사용되는 이미지의 좌표계가 완전히 같지 않을 수 있다.
3. 온디바이스 추론을 여러 개 동시에 돌리는 구조 때문에 CPU 경쟁이 생겨 FPS가 오히려 떨어질 수 있다.

즉, 현재 상태는 "OBB 라우팅을 열어둔 상태"에 가깝고, "정확히 검증된 OBB 전체 파이프라인"이라고 보기에는 아직 확인해야 할 지점이 남아 있다.

## 1. 실제로 OBB 모델이 사용되고 있는지 확인 필요

`YoloDetector.kt`는 assets 폴더에서 다음 순서로 모델을 찾는다.

```text
voiceguide-obb.onnx
best-obb.onnx
yolo11n-obb.onnx
yolo11s-obb.onnx
yolo11m-obb.onnx
yolo11n.onnx
yolo11m.onnx
```

코드상으로는 OBB 모델을 우선 탐색하지만, 현재 Git 기준 assets에는 주로 일반 모델인 `yolo11n.onnx`가 들어있다. 로컬 파일로는 `yolo11m.onnx`도 보이지만, OBB 이름을 가진 모델 파일은 확인되지 않았다.

따라서 앱 디버그 화면에서 다음처럼 보이면 실제 OBB가 아니다.

```text
OBB : OFF
모델 : yolo11n.onnx
```

이 경우 화면에 보이는 박스는 회전 박스가 아니라 일반 axis-aligned bounding box, 즉 AABB다. 물체가 기울어져 있거나 비스듬히 보이면 박스가 물체보다 크게 보이는 것이 정상적으로 발생할 수 있다.

확인해야 할 로그:

```text
VG_PERF: CPU 2스레드 추론 - <modelName> obb=<true/false>
VG_PERF: YOLO output model=<modelName> obb=<true/false> shape=[...]
```

## 2. OBB ONNX 출력 구조 가정이 실제 모델과 맞는지 확인 필요

현재 `YoloDetector.kt`의 후처리 코드는 OBB 모델의 출력 구조를 다음과 같이 가정한다.

```text
[cx, cy, w, h, class scores..., angle]
```

그래서 angle은 마지막 feature로 읽는다.

```text
angleFeature = numFeatures - 1
numClasses = numFeatures - 5
```

이 가정이 실제 export된 ONNX 모델과 다르면 문제가 생긴다. 예를 들어 실제 모델 출력이 다른 순서이거나, angle 값의 단위/범위가 다르면 다음 현상이 생길 수 있다.

- 박스가 물체보다 크게 보인다.
- 회전 각도가 이상하게 적용된다.
- 박스 중심은 대충 맞는데 네 꼭짓점이 어긋난다.
- confidence는 나오지만 OBB 모양이 불안정하다.

특히 Ultralytics 계열 OBB 모델은 export 방식과 버전에 따라 출력 shape와 후처리 방식이 달라질 수 있다. 따라서 앱에서 찍히는 `YOLO output shape` 로그를 반드시 확인해야 한다.

확인 기준:

```text
일반 YOLO: [1, 84, 8400] 또는 비슷한 구조
OBB YOLO: [1, class 수 + 5, N] 구조일 가능성이 큼
```

하지만 shape만 맞는다고 끝은 아니다. angle이 마지막 feature인지, radian인지, degree인지, 회전 방향이 Android 좌표계와 맞는지도 확인해야 한다.

## 3. 바운딩 박스가 커 보이는 직접 원인

### 3.1 실제 OBB가 아니라 일반 YOLO 박스일 가능성

가장 먼저 볼 것은 모델명이다. OBB 모델이 없으면 일반 YOLO 모델을 사용한다. 일반 YOLO 박스는 회전하지 않는 사각형이라 물체보다 크게 보일 수밖에 없다.

예:

```text
기울어진 계단, 긴 물체, 비스듬한 차량
```

이런 물체는 일반 bbox가 물체를 감싸기 위해 더 넓은 영역을 차지한다.

### 3.2 PreviewView 화면과 분석 이미지 좌표계 불일치

화면에 박스를 그리는 `BoundingBoxOverlay.kt`는 PreviewView가 `FILL_CENTER`처럼 동작한다고 보고 좌표를 변환한다.

흐름은 대략 다음과 같다.

```text
카메라 Preview 화면
  -> PreviewView가 화면 비율에 맞게 crop/scale

분석 이미지
  -> ImageAnalysis 480x360
  -> YUV를 JPEG로 변환
  -> rotation 적용
  -> Bitmap decode
  -> YOLO 640x640 letterbox
  -> detection 좌표를 원본 이미지 비율로 복원
  -> Overlay에서 다시 화면 크기에 맞게 scale
```

문제는 PreviewView가 실제로 보여주는 화면과 분석에 사용한 JPEG가 100% 같은 crop/rotation/scale을 공유한다는 보장이 약하다는 점이다.

그래서 모델 좌표 자체가 맞아도 화면에 그릴 때 다음 문제가 생길 수 있다.

- 박스가 살짝 위/아래/좌/우로 밀림
- 박스가 실제 물체보다 커 보임
- 세로 화면에서 더 어긋남
- 특정 기기 해상도에서만 더 심함

특히 Preview는 전체 화면 `match_parent`이고, 분석 이미지는 `ImageAnalysis`에서 `480x360` target resolution을 사용한다. 서로 종횡비가 다르거나 crop 방식이 다르면 overlay가 물체와 완전히 붙지 않는다.

### 3.3 letterbox 복원은 모델 입력 기준으로만 맞다

`YoloDetector.kt`는 원본 Bitmap을 640x640으로 letterbox한 뒤, 탐지 결과를 다시 원본 Bitmap 비율로 복원한다.

이 복원 자체는 일반적인 방식이다. 다만 여기서의 "원본 Bitmap"은 PreviewView가 보여주는 원본 화면이 아니라, 분석용으로 만든 JPEG/Bitmap이다.

따라서 분석용 Bitmap과 화면 Preview가 다르면 복원 좌표도 화면에 그대로 맞지 않는다.

### 3.4 OBB 중복 제거는 회전 박스 기준이 아니다

현재 중복 제거는 `Detection`의 `cx`, `cy`, `w`, `h`를 사용해서 일반 사각형 IoU로 계산한다. OBB 꼭짓점 기준으로 polygon IoU를 계산하지 않는다.

즉, OBB가 있어도 중복 제거 단계에서는 여전히 축 정렬 박스처럼 판단한다.

영향:

- 더 타이트한 OBB 후보가 있어도 AABB 기준으로 큰 후보가 살아남을 수 있다.
- 회전된 물체에서 중복 제거 품질이 떨어질 수 있다.
- 최종 표시 박스가 기대보다 덜 정교해질 수 있다.

### 3.5 confidence threshold가 낮다

현재 confidence threshold는 `0.25`다. 낮은 threshold는 놓치는 물체를 줄이는 장점이 있지만, 품질이 애매한 후보도 살아남긴 쉽다.

영향:

- 흔들림, 어두운 장면에서 박스가 넓거나 불안정한 후보가 남을 수 있다.
- 박스가 프레임마다 조금씩 커졌다 작아졌다 할 수 있다.
- FPS가 낮을 때 박스 변화가 더 튀어 보인다.

## 4. FPS가 잘 안 나오는 이유

### 4.1 온디바이스 한 프레임 처리 비용이 크다

현재 온디바이스 처리 흐름은 가볍지 않다.

```text
ImageProxy
  -> YUV420 to NV21 변환
  -> JPEG 압축
  -> JPEG 파일 저장
  -> Bitmap decode
  -> 회전 보정
  -> 640x640 letterbox
  -> ARGB pixel 읽기
  -> FloatArray NCHW 변환
  -> ONNX Runtime CPU 추론
  -> StairsDetector 병렬 실행
  -> 후처리, vote, dedup
  -> UI 업데이트
```

모델 추론 자체도 무겁지만, 그 전에 JPEG 압축/저장/디코딩/회전/FloatArray 변환 비용이 계속 들어간다. 그래서 단순히 "ONNX 추론 ms"만 보는 것보다 `decode`, `infer`, `dedup`, `total`을 같이 봐야 한다.

현재 로그는 이 분석을 위해 다음 값을 찍는다.

```text
decode=<ms>
infer=<ms>
dedup=<ms>
total=<ms>
```

실제 체감 FPS는 `total`에 더 가깝다.

### 4.2 온디바이스 in-flight가 최대 3개라 CPU 경쟁이 생긴다

현재 설정:

```text
MAX_ON_DEVICE_IN_FLIGHT = 3
ONNX intraOp threads = 2
ONNX interOp threads = 1
```

이 말은 온디바이스 분석이 최대 3개까지 동시에 진행될 수 있고, 각 ONNX 추론은 내부적으로 CPU 2스레드를 쓴다는 뜻이다.

단순 계산으로도 ONNX만 최대 6개 CPU 스레드를 요구할 수 있다. 여기에 카메라, JPEG 변환, Bitmap 변환, UI, TTS까지 같이 돈다.

그래서 병렬 처리가 항상 FPS를 올리는 구조가 아니다. 오히려 다음처럼 될 수 있다.

```text
프레임 1 추론 시작
프레임 2 추론 시작
프레임 3 추론 시작
CPU 경쟁 발생
각 프레임의 infer 시간이 늘어남
새 프레임은 inFlight=3/3이라 skip
화면 반응이 늦어짐
```

이 로그가 보이면 병목이 이미 발생한 상태다.

```text
stream frame skipped: route=on_device inFlight=3/3
```

이 로그는 실패라기보다, 앱이 밀린 작업 때문에 최신 프레임을 버리고 있다는 의미다. 실시간 안내 앱에서는 오래된 프레임을 처리하는 것보다 최신 프레임 중심으로 가는 것이 맞지만, 너무 자주 발생하면 성능 한계에 도달한 것이다.

### 4.3 YOLO와 StairsDetector를 프레임마다 병렬 실행한다

`processOnDevice()`에서는 한 프레임마다 다음 두 작업을 동시에 실행한다.

```text
YoloDetector.detect(frameBitmap)
StairsDetector.detect(frameBitmap)
```

이론적으로는 병렬이라 빨라 보이지만, 둘 다 CPU와 Bitmap 메모리를 사용한다. 특히 YOLO가 이미 CPU를 많이 쓰는 상태라면 StairsDetector 병렬 실행이 전체 처리시간을 줄이지 못하고 CPU 경쟁만 키울 수 있다.

결과적으로 `infer` 시간이 늘어나고, in-flight가 쌓이고, frame skip이 늘어나는 패턴이 생길 수 있다.

### 4.4 FPS 표시값은 카메라 FPS가 아니다

현재 UI의 FPS는 실제 카메라 프레임률이 아니라, 처리 완료된 결과 사이의 시간 간격으로 계산된다.

계산 방식:

```text
FPS = 1000 / (현재 처리 완료 시각 - 직전 처리 완료 시각)
최근 10개 평균
```

그래서 다음 상황에서 표시 FPS가 실제 체감과 다르게 보일 수 있다.

- 여러 작업이 동시에 끝나면 순간 FPS가 높게 보인다.
- 추론이 밀리면 갑자기 낮게 보인다.
- 오래된 프레임 결과가 늦게 도착해도 FPS 계산에는 반영된다.
- 카메라가 30fps로 들어와도 처리 결과가 5fps면 UI에는 5fps 근처로 보인다.

따라서 성능 판단은 UI FPS 하나만 보면 안 된다. 아래 로그를 같이 봐야 한다.

```text
VG_PERF: route|on_device|decode|...|infer|...|dedup|...|total|...
VG_FLOW: stream frame skipped: route=on_device inFlight=...
```

## 5. 서버 모드와 온디바이스 모드 차이

이번 커밋은 설정에 "온디바이스 우선" 옵션을 추가했다. 이 옵션이 켜져 있으면 서버 URL이 있어도 온디바이스를 우선 사용한다.

따라서 성능 비교를 할 때는 반드시 현재 route를 확인해야 한다.

```text
경로 : ONNX
경로 : SERVER
```

서버 모드와 온디바이스 모드는 병목이 다르다.

| 모드 | 주 병목 | 박스 특징 |
|---|---|---|
| SERVER | 네트워크, 서버 추론, 업로드 이미지 크기 | 서버 모델/Depth 결과 기준 |
| ONNX | Android CPU, 전처리, ONNX Runtime | 앱 내 ONNX 모델 기준 |

서버에서는 `/detect` 응답의 `bbox_format`이 `obb`로 시작할 때만 OBB points를 쓴다. 그렇지 않으면 일반 bbox로 표시한다. 이 변경은 정상 방향이다. 다만 서버와 온디바이스의 모델/후처리가 다르면 박스 품질도 다르게 보인다.

## 6. 현재 코드에서 확인해야 할 로그 목록

Android Studio Logcat에서 아래 tag를 중심으로 보면 된다.

### 6.1 모델 확인

```text
VG_PERF: CPU 2스레드 추론 - <modelName> obb=<true/false>
VG_PERF: YOLO output model=<modelName> obb=<true/false> shape=[...]
```

확인할 것:

- `modelName`이 실제 OBB 모델인지
- `obb=true`인지
- output shape가 기대한 구조인지

### 6.2 처리시간 확인

```text
VG_PERF: request_id|...|route|on_device|model|...|obb_model|...|decode|...|infer|...|dedup|...|total|...|objs|...|obb_objs|...
```

확인할 것:

- `decode`가 큰지
- `infer`가 큰지
- `total`이 `infer`보다 훨씬 큰지
- `obb_objs`가 0인지 아닌지

### 6.3 프레임 밀림 확인

```text
VG_FLOW: stream frame skipped: route=on_device inFlight=3/3
```

확인할 것:

- 이 로그가 자주 뜨는지
- 뜬다면 FPS가 떨어지는 순간과 맞는지

### 6.4 탐지 박스 크기 확인

```text
VG_DETECT: [0] <class> | conf=... | cx=... | w=... h=... | area=...
```

확인할 것:

- `w*h` 면적이 지나치게 큰지
- 같은 물체가 프레임마다 면적이 크게 흔들리는지
- confidence가 낮은 박스가 계속 살아남는지

## 7. 우선순위별 문제 판단

### 1순위: 실제 OBB 모델 적용 여부

OBB 모델이 없거나 `OBB : OFF`라면, 현재 바운딩 박스가 큰 것은 OBB 실패가 아니라 일반 bbox를 보고 있는 것이다.

먼저 확인해야 한다.

```text
모델명이 *-obb.onnx 인가?
OBB : ON 인가?
obb_objs가 0보다 큰가?
```

### 2순위: Preview 좌표계와 분석 좌표계 불일치

모델은 맞는데 화면에서만 어긋난다면, overlay 변환 문제가 더 유력하다.

확인 방법:

- 같은 프레임 이미지를 저장해서 모델 좌표를 이미지 위에 직접 그려본다.
- 앱 Preview 위에 그린 결과와 비교한다.
- 저장 이미지에서는 맞고 앱 화면에서 틀리면 Preview/Overlay 좌표계 문제다.

### 3순위: ONNX output layout 불일치

OBB 모델을 쓰는데 꼭짓점이 이상하거나 회전이 이상하면 output layout 문제 가능성이 높다.

확인 방법:

- Android에서 찍힌 output shape 확인
- Python에서 같은 ONNX 모델로 한 장 추론
- Python 후처리 결과와 Android 후처리 결과 비교

### 4순위: CPU 병렬 처리 과부하

박스가 맞더라도 FPS가 낮으면 in-flight와 CPU 경쟁을 봐야 한다.

확인 기준:

```text
infer가 150ms 이상이면 단일 추론 기준 약 6.6fps 이하
total이 200ms 이상이면 전체 파이프라인 기준 약 5fps 이하
inFlight=3/3 skip이 자주 뜨면 이미 밀리고 있음
```

## 8. 발표/보고용 설명 문장

강사님께 설명할 때는 아래처럼 말하면 된다.

```text
최근 커밋은 OBB 모델을 사용할 수 있도록 Android 온디바이스 라우팅과 후처리 경로를 추가한 것입니다.
다만 현재 확인 결과, 실제 앱 assets에 OBB ONNX 모델이 들어있는지와 ONNX 출력 구조가 Android 후처리 가정과 일치하는지 검증이 필요합니다.
또한 PreviewView 화면과 분석 이미지의 crop/scale/rotation 좌표계가 완전히 같지 않으면 박스가 실제 물체보다 커 보이거나 살짝 밀릴 수 있습니다.
FPS 저하는 온디바이스 추론이 CPU 기반으로 돌고, 동시에 최대 3개 프레임을 처리하면서 CPU 스레드 경쟁이 발생할 수 있기 때문입니다.
따라서 다음 단계는 코드 수정 전에 Logcat에서 modelName, obb flag, output shape, infer/total ms, inFlight skip 로그를 확인하는 것입니다.
```

## 9. 코드 수정 없이 지금 해야 할 확인 순서

1. 앱 실행 후 설정에서 디버그 모드를 켠다.
2. 화면에 표시되는 `모델`, `OBB`, `FPS`, `추론`, `전체` 값을 확인한다.
3. Logcat에서 `VG_PERF`, `VG_FLOW`, `VG_DETECT`를 필터링한다.
4. `modelName`이 실제 OBB 모델인지 확인한다.
5. `obb_model=true`인데 `obb_objs=0`이면 후처리 또는 모델 출력 문제를 의심한다.
6. `inFlight=3/3` skip이 자주 뜨면 병렬 추론 과부하를 의심한다.
7. 저장 이미지 기준 박스는 맞는데 Preview 화면에서만 틀리면 overlay 좌표계 문제를 의심한다.

## 10. 현재 단계에서의 판단

현재 코드는 OBB 지원을 시작하기 위한 구조는 들어왔지만, 다음 검증 전까지는 "OBB가 정확히 동작한다"고 확정하면 안 된다.

특히 가장 중요한 체크는 이 세 가지다.

```text
1. 실제 OBB ONNX 모델이 assets에 포함되어 있는가?
2. Android 후처리가 그 OBB 모델의 출력 구조와 일치하는가?
3. PreviewView와 분석 Bitmap의 좌표계가 같은가?
```

FPS 문제는 다음 한 문장으로 정리할 수 있다.

```text
현재 온디바이스 경로는 전처리 비용이 크고, CPU ONNX 추론을 최대 3개까지 동시에 돌릴 수 있어서 병렬화가 오히려 CPU 경쟁을 만들어 FPS를 떨어뜨릴 가능성이 크다.
```

