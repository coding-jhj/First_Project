# Android And On-Device

## Android 앱 역할

Android 앱은 카메라 프레임을 받고, 온디바이스 추론 또는 서버 요청을 통해 사용자에게 음성 안내를 제공합니다.

## 온디바이스 처리 기준

- 카메라 프레임 콜백은 빠르게 받아야 합니다.
- ONNX 추론은 무거운 작업이므로 동시 실행 수를 제한해야 합니다.
- 오래된 프레임을 모두 처리하기보다 최신 프레임 중심으로 안내하는 것이 실시간성에 유리합니다.
- 서버 `sentence.py`와 Android `SentenceBuilder.kt`의 표현 규칙은 맞춰야 합니다.

## 성능 체크포인트

- FPS가 낮아질 때는 추론 시간, 프레임 스킵, in-flight 개수를 함께 봅니다.
- 온디바이스 추론을 병렬로 너무 많이 늘리면 CPU 경쟁 때문에 오히려 느려질 수 있습니다.
- Android asset의 ONNX 모델과 루트/로컬 모델 파일을 혼동하지 않게 관리합니다.

## 상세 원본

- `legacy/md/ANDROID_PERFORMANCE_GUIDE.md`
- `legacy/md/FPS_GPS_DASHBOARD_ACTION_PLAN.md`
- `legacy/md/FUNCTION_LOGIC_STUDY.md`

