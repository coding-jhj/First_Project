# CHANGELOG

## [2026-05-04] Android 성능·UX 개선

### FPS 개선 (8~9 → 10+)

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| `INTERVAL_MS` | 100ms | 50ms — 스케줄러가 처리 완료 직후 빠르게 다음 프레임 시작 |
| ONNX 스레드 | 기본값(1) | `setIntraOpNumThreads(2)` — CPU 코어 2개 활용 |
| 캡처 방식 | `OnImageSavedCallback` (File I/O) | `OnImageCapturedCallback` (메모리 직접 처리) |

**File I/O 제거 효과**: YUV→JPEG→디스크 저장→디스크 읽기 왕복 제거. 온디바이스 모드에서 프레임당 ~20ms 절약.

### 음성·텍스트 동기화 (TTS-text sync)

**문제**: `tvStatus.text` 가 즉시 갱신되고 음성은 수십~수백ms 뒤에 나와 화면과 소리가 어긋남. ElevenLabs TTS는 네트워크 요청으로 최대 1-2초 지연.

**해결**:
- `pendingStatusText` 변수로 표시 예정 텍스트 대기
- 내장 TTS: `UtteranceProgressListener.onStart()` 콜백에서 `tvStatus.text` 업데이트
- ElevenLabs: `MediaPlayer.start()` 직전 `tvStatus.text` 업데이트
- beep/silent 모드(TTS 없음): 즉시 업데이트 유지

### 문장 자연스러움 개선 (SentenceBuilder)

- 위치 뒤 쉼표 추가: `"오른쪽 약 2미터에 의자가 있어요."` → `"오른쪽 약 2미터에, 의자가 있어요."` — TTS 엔진이 방향+거리 읽은 뒤 짧게 쉬고 물체명 읽어 자연스러운 발화 유도

### UI / 접근성 개선

- `tvStatus.accessibilityLiveRegion`: `polite` → `assertive` — TalkBack이 탐지 결과를 즉시 읽음 (이전에는 다른 알림이 끝난 뒤 읽음)

---

## [2026-05-03] 수정내역

기존 `수정내역_2026-05-03.md` 참고.
