# VoiceGuide 팀 역할

> 기준일: 2026-05-01  
> 원칙: 각 영역에 단일 책임자를 두고, 발표 전에는 새 기능보다 검증과 문서 일치를 우선한다.

## 역할 분담

| 이름 | 역할 | 주 책임 | 주요 산출물 |
|---|---|---|---|
| 정환주 | 팀장, 서버, 프론트엔드 | MVP 범위 결정, 일정 관리, GCP 서버, API/DB/tracker 통합, 대시보드/첫 화면 정리 | 실행 가능한 서버, 대시보드, README/docs 최종 검수 |
| 신유득 | Vision, ML | YOLO/Depth/OCR/평가, 모델 파일명과 성능 자료 정리 | 탐지 로직 설명, 실패 케이스, benchmark 결과 |
| 김재현 | Android, UX | CameraX, ONNX, UI, 권한, 발열, TTS 겹침 제어 | 안정적인 APK, UX 개선 체크 결과 |
| 임명광 | NLG, 서버 도움 | 한국어 문장, alert mode, API 응답 문구, 서버 문서 보조 | 자연스러운 안내 문장, NLG 테스트 |
| 문수찬 | Voice, Q&A 시트 작성 | STT/TTS 검증, 발표 Q&A, 시연 질문 대비 | Q&A 시트, 음성 테스트 결과 |

## 모듈 연결

```text
김재현(Android)
  -> 온디바이스: YoloDetector.kt -> SentenceBuilder.kt -> Android TTS
  -> 서버 모드: POST /detect

정환주(Server/Frontend)
  -> src/api/routes.py
  -> src/api/db.py, src/api/tracker.py
  -> GCP Cloud Run 배포
  -> templates/dashboard.html, README 첫 화면 정리

신유득(Vision/ML)
  -> src/vision/detect.py
  -> src/depth/depth.py, src/depth/hazard.py
  -> tools/benchmark.py, results/

임명광(NLG)
  -> src/nlg/sentence.py
  -> src/nlg/templates.py
  -> 서버 응답 문장 검수

문수찬(Voice/Q&A)
  -> src/voice/stt.py, src/voice/tts.py
  -> docs/06_presentation/
  -> 발표 질문/답변 시트
```

## 발표 전 책임 기준

| 질문 | 책임자 |
|---|---|
| README만 보고 실행 가능한가? | 정환주 |
| 탐지 결과가 왜 그렇게 나오는지 설명 가능한가? | 신유득 |
| 실제 기기에서 5분 이상 안정적인가? | 김재현 |
| 음성 문장이 과장되거나 반복되지 않는가? | 임명광 |
| 강사님 질문에 역할별로 답변 가능한가? | 문수찬 |

## 협업 원칙

1. 같은 파일을 동시에 크게 고치지 않는다. 필요하면 해당 영역 책임자에게 먼저 공유한다.
2. "동작 확인"이라고 적은 기능은 즉석에서 시연 가능해야 한다.
3. 실험 기능은 README와 발표에서 분리해 말한다.
4. 서버는 `src.api.main:app` 하나만 본 서버로 본다.
5. GCP Cloud Run을 주 배포 경로로 사용한다.
