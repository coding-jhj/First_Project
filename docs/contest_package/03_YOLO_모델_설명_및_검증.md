# YOLO 모델 설명 및 검증 정리

## 모델 역할

YOLO 모델은 카메라 프레임에서 객체의 위치와 종류, 신뢰도를 산출합니다.

VoiceGuide는 탐지 결과를 그대로 안내하지 않고, 중복 제거와 안정화 과정을 거쳐 사용자에게 필요한 음성·진동 피드백으로 변환합니다.

## 모델 설명 표

| 항목 | 내용 |
|---|---|
| 기본 모델 | `yolo11n_320.tflite` |
| fallback 후보 | `yolo26n_float32.tflite` |
| 실행 위치 | Android 온디바이스 |
| 입력 | CameraX 프레임을 모델 입력 크기에 맞게 변환 |
| 출력 | bbox, class, confidence |
| 실행 Provider | TFLite GPU 우선, 실패 시 XNNPACK fallback |
| 후처리 | NMS/중복 제거, vote, IoU tracking, EMA smoothing |
| 선택 이유 | 네트워크 지연 없이 즉시 안내하기 위해 모바일 온디바이스 구조 선택 |

## 입력/출력 흐름

```text
CameraX frame
→ resize / preprocess
→ TFLite YOLO inference
→ bbox, class, confidence
→ NMS / duplicate removal
→ vote filtering
→ IoU tracking
→ EMA smoothing
→ risk score
→ TTS / vibration / UI / JSON upload
```

## 발표용 설명

> YOLO 모델은 카메라 프레임에서 객체 위치와 종류를 찾습니다. VoiceGuide는 이 결과를 그대로 말하지 않고, 중복 제거와 안정화 과정을 거쳐 보행 중 필요한 안내로 변환합니다.

## 확보된 검증

현재 실행 기준:

```text
python -m pytest tests/ -m "not integration"
23 passed, 9 deselected
```

테스트 범위:

- `/api/policy` 응답 및 policy 구조
- `/detect` 응답 스키마와 `depth_source`
- `/detect_json` 저장 및 `recent_detections` 회귀
- `/spaces/snapshot`
- API key 보호 라우트
- 한국어 NLG 조사/거리 문장
- 서버 런타임 import

## 추가 측정 필요

| 항목 | 이유 |
|---|---|
| Android FPS | 실제 기기와 조명 환경에 따라 달라짐 |
| 모델별 mAP50 | 모델 정확도 비교 필요 |
| 메모리 사용량 | 장시간 실행 안정성 확인 필요 |
| TTS-UI latency | 사용자 체감 지연 확인 필요 |
| 저조도 성능 | 실제 보행 환경에서 검증 필요 |

## 과장 금지

- `yolo26n_float32.tflite`는 fallback 후보로 표현합니다.
- YOLO26n 자동 전환이 검증 완료됐다고 쓰지 않습니다.
- mAP50, FPS, 메모리 수치를 임의로 만들지 않습니다.
- Depth 모델로 정확한 거리를 계산한다고 쓰지 않습니다.
