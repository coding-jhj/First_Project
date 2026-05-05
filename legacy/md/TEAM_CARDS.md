# 팀원 발표 카드

> 발표 직전 각자 자기 파트를 30초 안에 설명하기 위한 카드입니다.  
> 기준 역할은 [TEAM.md](TEAM.md)와 동일합니다.

## 정환주 - 팀장, 서버, 프론트엔드

### 한 줄 역할

MVP 범위를 고정하고, GCP 서버와 대시보드, 문서 첫 화면을 정리한다.

### 담당 코드/문서

- `src/api/main.py`
- `src/api/routes.py`
- `src/api/db.py`
- `src/api/tracker.py`
- `templates/dashboard.html`
- `README.md`, `docs/03_server/README.md`

### 말할 문장

```text
저는 팀장, 서버, 프론트엔드를 담당했습니다.
서버 진입점을 src.api.main:app 하나로 고정하고 GCP Cloud Run에 배포했습니다.
Android 요청은 /detect로 들어오고, 대시보드는 /status를 통해 현재 객체와 GPS 흐름을 보여줍니다.
```

## 신유득 - Vision, ML

### 한 줄 역할

탐지 모델과 Depth/OCR 보조 로직을 검증하고 실패 케이스를 정리한다.

### 담당 코드/문서

- `src/vision/detect.py`
- `src/depth/depth.py`
- `src/depth/hazard.py`
- `src/ocr/bus_ocr.py`
- `train/`, `tools/benchmark.py`, `results/`

### 말할 문장

```text
저는 Vision과 ML을 담당했습니다.
YOLO 탐지 결과를 방향과 위험도 계산으로 연결하고, Depth V2가 없을 때 bbox 기반 fallback이 어떻게 동작하는지 검증했습니다.
평가에서는 성공 사례뿐 아니라 오탐과 한계도 같이 정리했습니다.
```

## 김재현 - Android, UX

### 한 줄 역할

Android 앱을 안정적으로 실행하고, 온디바이스 fallback과 사용자 흐름을 정리한다.

### 담당 코드/문서

- `android/app/src/main/java/com/voiceguide/MainActivity.kt`
- `android/app/src/main/java/com/voiceguide/YoloDetector.kt`
- `android/app/src/main/java/com/voiceguide/SentenceBuilder.kt`
- `android/app/src/main/java/com/voiceguide/BoundingBoxOverlay.kt`
- `android/app/src/main/res/layout/activity_main.xml`

### 말할 문장

```text
저는 Android와 UX를 담당했습니다.
CameraX로 이미지를 캡처하고 ONNX 온디바이스 탐지를 우선 사용하게 했습니다.
서버가 없어도 기본 장애물 안내가 유지되며, TTS 겹침과 권한 요청 흐름을 점검했습니다.
```

## 임명광 - NLG, 서버 도움

### 한 줄 역할

탐지 결과를 짧고 자연스러운 한국어 안내 문장으로 바꾼다.

### 담당 코드/문서

- `src/nlg/sentence.py`
- `src/nlg/templates.py`
- `tests/test_sentence.py`
- `src/api/routes.py` 응답 문장 보조

### 말할 문장

```text
저는 NLG와 서버 응답 문장 보조를 담당했습니다.
탐지 결과를 단순 나열하지 않고, 위험도와 방향을 반영한 짧은 문장으로 바꿨습니다.
생활 물체에는 과한 경고를 줄이고, 실제 위험 상황에만 강한 표현을 쓰도록 정리했습니다.
```

## 문수찬 - Voice, Q&A 시트

### 한 줄 역할

STT/TTS 흐름을 검증하고 발표 질문에 대비한 Q&A 시트를 만든다.

### 담당 코드/문서

- `src/voice/stt.py`
- `src/voice/tts.py`
- `android/app/src/main/java/com/voiceguide/MainActivity.kt`의 음성 관련 함수
- `docs/06_presentation/`

### 말할 문장

```text
저는 Voice와 Q&A 시트를 담당했습니다.
Android OS TTS와 서버 TTS fallback의 차이를 정리하고, STT가 실패했을 때 안전하게 대응하는 흐름을 확인했습니다.
발표 질문에 대비해 검증된 기능과 실험 기능을 나눠 Q&A로 정리했습니다.
```

## 연결 구조

```text
김재현(Android/UX)
  -> 온디바이스 탐지와 앱 실행 안정화

정환주(Server/Frontend)
  -> GCP /detect, /health, /dashboard

신유득(Vision/ML)
  -> YOLO, Depth, OCR, 평가

임명광(NLG)
  -> 문장 생성과 alert mode

문수찬(Voice/Q&A)
  -> STT/TTS 검증과 발표 질문 대응
```
