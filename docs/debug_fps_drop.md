# FPS 75 → 2.6 하락 원인 분석

> 2026-05-07 — 재배포 후 발생. 코드 변경 없이 원인 파악 목적.

---

## 결론 먼저

**가장 유력한 원인 3개**, 순서대로 확인해야 한다.

| 우선순위 | 의심 원인 | 근거 |
|---|---|---|
| 1순위 | NNAPI 비활성화 → CPU fallback | 재배포 후 모델/ops 변경 시 자주 발생 |
| 2순위 | FastDepth가 동기 추론으로 추가됨 | 미팅에서 "FastDepth 넣어봄"이라고 언급 |
| 3순위 | 프레임마다 새 Thread 생성 | 코드 구조 문제 (원래부터 있었지만 누적 악화 가능) |

---

## 원인 1: NNAPI 비활성화 (가장 유력)

### 무슨 일이 벌어지나

`YoloDetector.kt:73`에서 NNAPI 세션을 먼저 시도하고, 실패하면 CPU로 조용히 fallback한다:

```
NNAPI (GPU/DSP 가속) → 실패 시 → CPU 추론
```

NNAPI가 켜진 상태에서는 YOLO 추론이 20~30ms.  
CPU fallback이면 200~400ms — **10배 이상 느려진다**.

### 왜 재배포 후에 갑자기 생기나

NNAPI는 **모델 파일이 달라지면** 다시 컴파일을 시도한다.  
이때 새 ops나 레이어가 NNAPI 지원 목록에 없으면 전체 세션을 거부한다.

- FastDepth를 넣으면서 ONNX 모델 파일이 바뀌었다면 → NNAPI 거부 가능
- 원래 `yolo11n.onnx`만 있었는데 `yolo11m.onnx`가 추가됐거나 교체됐다면 → 모델 크기 자체가 다름

### 확인 방법

Logcat에서 `tag:VG_PERF`를 필터해서 아래 중 어느 줄이 출력되는지 확인:

```
✅ 정상: "NNAPI + CPU 4 스레드 — yolo11n.onnx"
❌ 문제: "NNAPI 세션 실패 → CPU 4 스레드 fallback — yolo11n.onnx"
❌ 문제: "CPU 4 스레드 추론 — yolo11m.onnx"   ← 80MB 모델이 로드됨
```

---

## 원인 2: FastDepth 동기 추론

### 무슨 일이 벌어지나

미팅에서 "FastDepth를 넣어봤다"고 했는데, 만약 YOLO 추론 루프와 같은 Thread 안에서 FastDepth를 순서대로(동기) 실행하면:

```
YOLO 추론 (30ms)
+ FastDepth 추론 (100~300ms)
= 프레임당 130~330ms → 3~7 FPS
```

2.6 FPS = 약 385ms/프레임 → FastDepth가 350ms 잡아먹고 있는 수치와 일치.

### 확인 방법

`processOnDevice` 안에서 FastDepth 관련 코드가 있는지 확인.  
Logcat에서 `inferMs` 값이 300ms 이상인지 확인:

```
tag:VG_PERF 필터 → "infer|NNN" 숫자 확인
```

---

## 원인 3: 프레임마다 새 Thread 생성

### 무슨 일이 벌어지나

`MainActivity.kt:1317`에서 매 프레임마다 `Thread { ... }.start()`를 호출한다.  
OS Thread 하나를 만들고 죽이는 비용이 프레임마다 발생한다.

게다가 그 안에서 `CompletableFuture.supplyAsync`를 2개 더 만든다 (YOLO + 계단).  
즉 프레임 하나당 OS 스레드 1개 + ForkJoinPool 작업 2개 = 동시에 3개 스레드가 경쟁한다.

`MAX_ON_DEVICE_IN_FLIGHT = 3`이면 최악의 경우:
- 3 × (Thread 1개 + ForkJoin 2개) = 9개 스레드가 동시에 CPU 코어 4개를 두고 싸움

### 이게 재배포 후 악화될 수 있는 이유

FastDepth가 추가되어 한 프레임의 처리 시간이 길어지면,  
in-flight 프레임이 MAX까지 쌓이는 상황이 더 자주 발생 → 스레드 경합 심화.

---

## 원인 4: 프레임마다 디스크 I/O (구조적 문제)

### 무슨 일이 벌어지나

스트림 프레임이 들어오면 `imageProxyToJpegFile()` (MainActivity:1150)에서:

```
YUV 프레임 → NV21 변환 → JPEG 압축 → 디스크에 temp 파일 저장
→ 디스크에서 읽기 → Bitmap 디코딩 → YOLO 입력
```

**카메라 메모리에 있는 데이터를 굳이 디스크에 썼다가 다시 읽는다.**

- YUV→NV21 변환 루프: 크로마 플레인을 픽셀 단위로 Kotlin 루프로 처리 → O(W×H/2) 반복
- JPEG 파일 write + read: SSD라도 10~30ms 추가
- Bitmap decode: 5~10ms 추가

단독으로 FPS를 2.6까지 낮추진 않지만, 원인 1~3과 겹치면 누적된다.

---

## 지금 당장 해야 할 확인 순서

### Step 1 — 로그캣 확인 (앱 실행 직후)

Android Studio → Logcat → 필터: `VG_PERF`

```
찾아야 할 줄:
  NNAPI + CPU N 스레드 — yolo11n.onnx    → 정상
  NNAPI 세션 실패 → ...                  → 원인 1 확정
  CPU N 스레드 추론 — yolo11m.onnx       → 모델 교체됨
```

### Step 2 — 추론 시간 확인

Logcat 필터: `VG_PERF` → `infer|` 값 확인

```
infer|20~50ms   → NNAPI 정상 (원인 2나 3)
infer|200ms 이상 → NNAPI CPU fallback 또는 FastDepth 포함
infer|350ms 이상 → FastDepth 동기 실행 유력
```

### Step 3 — assets 폴더 확인

```
android/app/src/main/assets/ 에 어떤 .onnx 파일이 있는지 확인
  yolo11n.onnx만 있음 → 정상
  yolo11m.onnx가 있거나 yolo11n.onnx가 없음 → 모델 교체됨
  fastdepth.onnx 또는 depth*.onnx가 있음 → FastDepth 추가됨
```

---

## 빠른 임시 조치

코드를 바꾸지 않고 FPS를 확인하려면:

1. **Settings → 온디바이스 우선 OFF** 해보기 — 서버로 빠지면 추론 시간 빠짐 → NNAPI 문제 확인
2. **디버그 모드 ON** (설정 버튼 롱프레스) → 화면에 `추론: Nms` 직접 표시됨 → 어느 단계가 느린지 바로 보임
