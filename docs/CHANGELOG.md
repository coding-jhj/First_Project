# VoiceGuide 작업 내역 (2026-04-27 최신)

---

## 2026-04-27 후반 수정 Ver2 (조원 임명광)

> Android 앱 바운딩박스 위치 오차 수정 · 계단 탐지 보완 · 크리티컬/비크리티컬 음성 분기 구현 · StairsDetector 오탐 제거

---

### 1. 바운딩박스 위치 오차 수정 (Android)

#### 원인 3가지 모두 수정

| 원인 | 수정 내용 |
|------|---------|
| 이미지 비율 왜곡 | 640×640 강제 리사이즈 → **Letterboxing** 방식으로 교체 |
| EXIF 회전 미적용 | `BitmapFactory.decodeFile()` 단독 사용 → `decodeBitmapUpright()` 추가 |
| PreviewView 크롭 미보정 | 좌표를 뷰 크기에 직접 곱하던 방식 → **FILL_CENTER 변환** 계산 적용 |

**`YoloDetector.kt` — Letterboxing 도입**

```
기존: 원본 이미지를 640×640으로 비율 무시 강제 리사이즈
     → 왜곡된 좌표로 추론 → 바운딩박스 실제 위치와 불일치

수정: scale = min(640/W, 640/H) 으로 비율 유지 축소 후
     남은 영역을 검정 패딩으로 채워 640×640 완성 (letterbox)
     → 패딩 오프셋(padX, padY)을 역변환해 원본 좌표로 복원
```

`postProcess()` 시그니처 변경: `padX, padY, scaledW, scaledH` 추가
- letterbox 공간의 픽셀 좌표 → 원본 이미지 정규화 [0,1] 좌표로 변환
- 패딩 영역(검정 바깥)에 중심이 있는 탐지 결과 자동 제거

**`MainActivity.kt` — EXIF 회전 보정**

```kotlin
// 신규 추가
private fun decodeBitmapUpright(file: File): Bitmap
```

- `ExifInterface`로 JPEG 회전 태그 읽기 (90°/180°/270°)
- `Matrix.postRotate()` 적용 후 바른 방향 비트맵 반환
- `processOnDevice()`에서 `decodeBitmapUpright()` 호출로 교체

**`BoundingBoxOverlay.kt` — PreviewView FILL_CENTER 보정**

```
기존: setDetections(detections)
      → (det.cx * vw, det.cy * vh) 로 단순 변환 → 크롭된 영역 무시

수정: setDetections(detections, imgW, imgH)
      → fillScale = max(vw/imgW, vh/imgH) 계산
      → offsetX/offsetY 포함한 실제 화면 픽셀로 변환
```

---

### 2. 계단 탐지 문제 분석 및 보완 (Android)

#### 근본 원인 파악

`assets/yolo11m.onnx` **파일이 없음** → 앱이 `yolo11n.onnx`(표준 COCO 80클래스)로 자동 fallback  
→ class 80(계단)이 모델 출력에 아예 존재하지 않아 탐지 불가

**해결 방법 (yolo11m 모델 적용):**
```bash
# 학습된 모델을 ONNX로 변환 후 assets에 복사
python tools/export_onnx.py
# 생성된 yolo11m.onnx → android/app/src/main/assets/ 에 복사 후 재빌드
```

#### `StairsDetector.kt` — 신규 파일 (초기 버전)

yolo11m.onnx 없을 때도 계단을 잡기 위한 이미지 분석 기반 보완 탐지기

```
초기 동작 원리:
1. 이미지를 320px 너비로 다운샘플 (성능 최적화)
2. 하단 65% 영역에서 행(row)별 수직 밝기 차이(계단 디딤면 엣지) 계산
3. 로컬 피크(계단 엣지 라인) 탐지
4. 피크 3개 이상 & 간격이 규칙적(±55% 이내) → 계단으로 판정
5. 탐지된 영역을 [0,1] 정규화 좌표로 반환
```

**`MainActivity.kt` — StairsDetector 통합**

```kotlin
// YOLO가 계단을 잡지 못했을 때 엣지 분석으로 보완
if (detections.none { it.classKo == "계단" }) {
    stairsDetector.detect(bmp)?.let { detections = detections + it }
}
```

- `processOnDevice()` fallback 버그도 함께 수정  
  (기존: 파일 삭제 후 동일 경로로 sendToServer 시도 → 수정: 파일 유지 후 fallback)

---

### 2-1. StairsDetector 오탐 제거 — 전면 재작성 (Android)

#### 문제

초기 버전 기준이 너무 느슨해 **계단이 없는 일반 실내 환경에서도 계단으로 오판**.

| 오탐 원인 | 내용 |
|---------|------|
| 최소 엣지 강도 너무 낮음 | `8f` → 실내 거의 모든 장면 통과 |
| SNR 조건 없음 | 타일·카펫 등 균일 패턴 걸러내지 못함 |
| 피크 3개로 판정 | 바닥 줄눈·선반·그림자도 3개 이상 발생 |
| 간격 허용 오차 ±55% | 불규칙해도 계단으로 판정 |
| 수평 폭 체크 없음 | 가구 다리·좁은 그림자도 통과 |

#### 수정 — 5가지 조건 모두 통과해야 계단 판정

| 조건 | 기존 | 수정 후 |
|------|------|--------|
| 절대 엣지 강도 | `≥ 8f` | **`≥ 20f`** |
| SNR (신호 대 잡음) | 없음 | **`maxEdge ≥ meanEdge × 3.5`** |
| 최소 피크 수 | 3개 | **4개** |
| 피크 탐지 임계값 | `maxEdge × 0.35` | **`maxEdge × 0.55`** |
| 최소 피크 간격 | 3px | **10px** |
| 간격 편차 허용 | ±55% / 40% 허용 | **±30% / 20% 허용** |
| 수평 폭 커버리지 | 없음 | **≥ 55% 이상** |

**SNR 조건 (가장 핵심):**
```
타일·카펫 → 모든 행에 균일한 엣지 → meanEdge 높음 → maxEdge/meanEdge 낮음 → 탈락
계단      → 대부분 행은 평탄, 경계 행만 강한 엣지 → meanEdge 낮음 → SNR 높음 → 통과
```

**수평 폭 커버리지 조건:**
```
계단 엣지    → 카메라 화면 가로 전체에 걸쳐 나타남 → 커버리지 높음 → 통과
가구 다리·그림자 → 좁은 영역에만 엣지 존재 → 커버리지 낮음 → 탈락
```

---

### 3. 크리티컬/비크리티컬 음성 분기 구현 (Android)

#### 기존 문제

`handleSuccess()` 에서 모든 탐지 결과를 `speak()`(TTS)로만 출력.  
일반 장애물(의자, 테이블 등)에도 매번 음성 안내 → 청각 피로 유발.

#### 수정 동작

| 상황 | 판정 기준 | 출력 방식 |
|------|---------|---------|
| **크리티컬** | 문장이 "위험" 또는 "조심"으로 시작 | **TTS 음성** — 진행 중 음성도 중단하고 즉시 안내 |
| **일반 장애물** | 그 외 모든 탐지 결과 | **비프음** (250ms) |
| **장애물 없음** | "주변에 장애물이 없어요." | 무음 (화면 텍스트만 표시) |

**신규 추가 함수 (`MainActivity.kt`)**

```kotlin
// "위험" / "조심" 시작 문장만 TTS 안내 대상
private fun isCritical(sentence: String) =
    sentence.startsWith("위험") || sentence.startsWith("조심")

// ToneGenerator 기반 단음 비프 (AudioManager.STREAM_MUSIC, 볼륨 80)
private fun beep() {
    toneGen?.startTone(ToneGenerator.TONE_PROP_BEEP, 250)
}
```

크리티컬 상황은 `QUEUE_FLUSH` 모드로 이전 TTS를 중단하고 즉시 새 음성 출력.

---

### 4. 변경 파일 목록

| 파일 | 변경 유형 | 내용 |
|------|---------|------|
| `android/.../YoloDetector.kt` | 수정 | Letterboxing 도입, postProcess 좌표 역변환 |
| `android/.../BoundingBoxOverlay.kt` | 수정 | setDetections 시그니처 변경, FILL_CENTER 보정 |
| `android/.../MainActivity.kt` | 수정 | EXIF 회전, StairsDetector 통합, 음성 분기, fallback 버그 수정 |
| `android/.../StairsDetector.kt` | **신규 → 재수정** | 엣지 패턴 기반 계단 탐지기 신규 작성 후 오탐 문제로 5조건 방식으로 전면 재작성 |

---

> 팀원 공유용 — 오늘 추가/수정된 내용 전체 정리

---

## 요약

기존 MVP 위에 AI 성능 강화·Android 기능 완성·안전성 개선·문서 전면 업데이트를 진행했습니다.  
**git pull 후 아래 설치 명령어 실행해주세요.**

```bash
git pull origin main
pip install ddgs pygame onnx onnxscript
```

> **`depth_anything_v2_vits.pth`** (94MB) — 각자 받아야 합니다 → `SETUP.md` 3단계 참고
>
> **`yolo11m_indoor.pt`** (파인튜닝 모델, 39MB) — `.gitignore`로 git 미포함. 아래 둘 중 하나:
> - 방법 A (권장): 직접 학습 (~9분, GPU 필요)
>   ```bash
>   python train/prepare_dataset.py   # 데이터 다운로드
>   python train/finetune.py          # 학습 → yolo11m_indoor.pt 자동 생성
>   ```
> - 방법 B: 조장에게 구글드라이브로 파일 받기

---

## 1. AI 모델

### YOLO11m 파인튜닝 — 계단 클래스 추가

기존 YOLO11m에는 계단 클래스가 없었습니다.  
DuckDuckGo로 계단 이미지 404장을 수집하고 자동 라벨링 후 직접 학습했습니다.

| 항목 | 내용 |
|------|------|
| 학습 데이터 | 계단 이미지 404장 (자동 수집·라벨링) |
| 학습 시간 | RTX 5060 GPU, 약 9분 |
| 계단 mAP50 | **0.992** (정밀도 91.7%, 재현율 100%) |
| 결과 모델 | `yolo11m_indoor.pt` |

- `src/vision/detect.py` — `yolo11m_indoor.pt` 자동 로드, 없으면 `yolo11m.pt` fallback
- `TARGET_CLASSES`에 `stairs → 계단` 추가
- 계단은 항상 `is_ground_level=True` 처리 (위험도 상향)

---

### Depth Anything V2 — GPU 활성화

기존에 주석으로 비활성화되어 있던 Depth V2를 완전히 켰습니다.

- `depth_anything_v2_vits.pth` 파일 있으면 자동 로드, 없으면 bbox 기반 자동 fallback
- GPU(CUDA) 자동 감지, CPU도 지원
- 이미지당 depth map 1회 추론 (bbox별 반복 제거 → 속도 최적화)
- **안전 우선**: bbox 내 하위 30% 깊이값 사용 → 실제보다 약간 가깝게 추정 → 조기 경고

---

### 깊이 맵 기반 계단·낙차·턱 감지 — 신규 (`src/depth/hazard.py`)

YOLO가 잡지 못하는 계단을 Depth V2 출력만으로 감지합니다.

- 이미지 하단 60% 바닥 영역을 12구역으로 분석
- 깊이 급증(>1.2m) → 낙차/계단 하강 경고
- 깊이 급감(>1.0m) → 턱/계단 상승 경고
- 좌우가 중앙보다 가까우면 좁은 통로 경고

```
"조심! 0.7m 앞에 계단이나 낙차가 있어요. 멈추세요."
"발 앞에 턱이나 계단이 있어요. 약 0.8m."
```

---

### 객체 추적기 — 신규 (`src/api/tracker.py`)

프레임마다 튀는 거리값을 EMA(지수이동평균)로 안정화합니다.

- 거리 평활화 (α=0.55): 1.2m→1.8m→1.1m 튀는 것을 1.3m→1.4m→1.35m으로 안정화
- 접근 감지: 0.4m 이상 가까워지면 "사람이 가까워지고 있어요" 자동 생성
- 소멸 감지: 4초간 미탐지 + 3m 이내였던 물체 → "의자가 사라졌어요" 자동 생성

---

## 2. Android 앱

### 캡처 간격 단축

**2초 → 1초** (INTERVAL_MS = 1000L)

### STT 음성 명령 — 신규

| 명령어 | 전환 모드 |
|--------|---------|
| "주변 알려줘", "앞에 뭐 있어" | 장애물 모드 |
| "찾아줘", "어디 있어" | 찾기 모드 |
| "이거 뭐야", "뭐야" | 확인 모드 |

초록 "음성 명령" 버튼으로 실행합니다.

### 카메라 방향 자동 감지 — 신규

가속도 센서(TYPE_ACCELEROMETER)로 폰 기울기를 실시간 감지합니다.

| 기울기 | 감지 방향 |
|--------|---------|
| 세로 정상 | front |
| 세로 뒤집힘 | back |
| 가로 왼쪽 | left |
| 가로 오른쪽 | right |

기존 하드코딩 `"front"` 제거 — 이제 서버에 실제 방향 자동 전송합니다.

### ONNX 온디바이스 추론 — 신규

`android/app/src/main/assets/yolo11m.onnx` 파일이 있으면 서버 없이 폰 단독으로 탐지합니다.

- 서버 있을 때: 서버 추론 (Depth V2 포함, 더 정확)
- 서버 없을 때: 온디바이스 ONNX 추론 자동 전환
- 계단 탐지 시 "조심! 앞에 계단이 있어요." 최우선 출력

ONNX 파일 생성 방법:
```bash
python export_tflite.py
```

### Failsafe 안전 경고 — 신규

| 상황 | 동작 |
|------|------|
| 서버 3회 연속 실패 | "서버 연결이 끊겼어요. 주의해서 이동하세요." 음성 |
| 6초간 결과 없음 | "분석이 중단됐어요. 주의해서 이동하세요." 음성 |
| 카메라 오류 | "카메라를 사용할 수 없어요. 주의하세요." 음성 |

네트워크 타임아웃도 단축했습니다 (15초→5초, 30초→8초).

### UI 추가

- 초록 "음성 명령" 버튼
- 모드/방향 상태 표시 텍스트 (`모드: 장애물 | 방향: 정면`)

---

## 3. 서버

### NLG 문장 품질 개선 (`src/nlg/sentence.py`)

거리 기반 긴박도 4단계 — 기존의 텍스트 라벨(가까이/보통) 대신 실제 미터값으로 판단합니다.

| 거리 | 출력 예시 |
|------|---------|
| 0.5m 미만 | `"위험! 바로 앞 의자!"` |
| 0.5~1.0m | `"멈추세요! 바로 앞에 의자가 있어요. 약 70cm."` |
| 1.0~2.5m | `"바로 앞에 의자가 있어요. 약 1.2m. 멈추세요."` |
| 2.5m 이상 | `"바로 앞에 의자가 있어요. 약 3.0m."` |

바닥 장애물 전용 문장도 추가했습니다.
```
"조심! 발 아래 배낭. 오른쪽으로 피해가세요."
```

### 서버 안전성

- **전역 예외 핸들러** — 서버 오류 시에도 Android에 `"분석 중 오류가 발생했어요. 주의해서 이동하세요."` 반환
- **FastAPI lifespan** — 기존 deprecated `on_event` 방식 교체

### TTS 캐시 (`src/voice/tts.py`)

같은 문장은 `__tts_cache__/` 폴더에 MP3로 저장해 다음부터 네트워크 없이 즉시 재생합니다.

### Gradio 데모 개선 (`app.py`)

- 장애물/찾기/확인 모드 라디오 버튼 추가
- 탐지 결과 이미지에 바운딩 박스 시각화
- 추론 시간(ms), Depth V2 사용 여부 표시
- 계단/낙차 감지 시 화면 하단 빨간 배너 표시

---

## 4. 버그 수정

| 버그 | 수정 내용 |
|------|---------|
| Android 앱 크래시 | `yolo11n.onnx` → `yolo11m.onnx` 파일명 불일치 수정 |
| 거리 긴급도 오판 | area_ratio 라벨 대신 distance_m 직접 사용 |
| 거리 99.9m 표시 | area_ratio=0일 때 10.0m로 cap |
| Gradio 방향 오표시 | `"far_left"` 등 잘못된 키 → `CLOCK_TO_DIRECTION` 직접 사용 |
| 테스트 3개 실패 | fixture 누락(`conftest.py` 추가), direction 값 오류 수정 |
| "가방" 중복 | handbag→핸드백, backpack→배낭으로 구분 |
| FastAPI 경고 | deprecated `on_event` → `lifespan` 방식 교체 |

---

## 5. 테스트

**12/12 전부 통과** (`pytest tests/`)

새로 추가된 테스트:
- `stairs` 클래스 포함 확인
- `hazards` 응답 필드 확인
- `/stt` 엔드포인트 확인
- direction 값 `8시~4시` 기준으로 수정

---

## 6. 문서

| 파일 | 수정 내용 |
|------|---------|
| `docs/INSTRUCTOR.md` | 강사님 설명 스크립트 현재 구현 기준 전면 재작성 |
| `docs/PRESENTATION.md` | **신규** — 발표 스크립트, 경쟁사 비교, Q&A |
| `docs/CODE_FLOW.md` | **신규** — 코드 흐름 이해 가이드 |
| `docs/CALIBRATION_TEST.md` | **신규** — 거리 실측 보정 방법 |
| `docs/mvp_checklist.md` | 미완성 → 전부 완료, 파인튜닝·계단·Failsafe 추가 |
| `docs/PROJECT_GUIDE.md` | 미완성 섹션 제거, 현재 기능 목록으로 교체 |
| `docs/TECH.md` | 파이프라인 YOLO11n→11m, left/center/right→8시~4시 교체 |
| `docs/troubleshooting.md` | CONF 0.45→0.60, 계단 오류 항목 추가 |
| `SETUP.md` | 캡처 2초→1초, 모델 다운로드, APK 무선 설치 추가 |
| `README.md` | YOLO11n→11m, 파이프라인 최신화 |

---

## 7. 변경되지 않은 것

- 기존 Android 앱 핵심 구조 (CameraX, OkHttp, TTS)
- FastAPI 엔드포인트 `/detect`, `/spaces/snapshot` 인터페이스
- SQLite DB 스키마
- 한국어 조사 처리 로직 (이/가, 을/를)
- 기존 커밋 히스토리
- `RESEARCH.md`, `TEAM.md`, `PRD.md` (초기 기획 문서 — 역사 보존)
