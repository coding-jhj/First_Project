# Debug And Validation

## 핵심 검증 기준

발표 전에는 기능 개수보다 아래 항목이 실제로 확인되는지가 중요합니다.

| 항목 | 확인 방법 |
|---|---|
| 문장 생성 | `python -m pytest tests/test_sentence.py` |
| 탐지 로직 | `python -m pytest tests/test_detect.py` |
| 서버 연결 | `/health`, `tools/probe_server_link.py` |
| Android 안내 | 실기기에서 TTS 출력 확인 |
| FPS/지연 | Android 로그의 infer time, frame skipped 확인 |

## 자주 나온 문제

### 1. 바운딩 박스 불일치

탐지 결과와 화면에 그려지는 박스가 어긋나는 문제입니다. 보통 이미지 회전, 프리뷰 비율, 좌표 변환 방식이 맞지 않을 때 발생합니다.

확인할 것:

- 카메라 프레임 해상도
- 모델 입력 크기
- 화면 프리뷰 비율
- 좌표 scaling과 letterbox 여부

### 2. FPS 저하

ONNX 추론은 CPU를 많이 씁니다. 동시에 여러 추론을 실행하면 병렬처럼 보이지만 실제로는 CPU 경쟁 때문에 더 느려질 수 있습니다.

확인할 로그:

```text
stream frame skipped: route=on_device inFlight=3/3
```

이 로그는 이미 처리 중인 프레임이 많아서 새 프레임을 버렸다는 뜻입니다. 실시간 안내에서는 오래된 프레임을 처리하는 것보다 최신 프레임 중심으로 처리하는 편이 낫습니다.

### 3. 문장 규칙 불일치

서버 `sentence.py`와 Android `SentenceBuilder.kt`가 다른 문장을 만들면 시연 중 혼란이 생깁니다.

예:

```text
위험! 바로 앞 자동차! 조심!
바로 코앞에 가방이 있어요. 멈추세요
```

문장 정책을 바꾸면 서버와 Android 테스트를 같이 확인해야 합니다.

### 4. 계단/낙차 감지

계단은 안전과 직접 연결되므로 과장하면 안 됩니다. 실험에서는 YOLO와 Depth 기반 접근을 모두 검토했지만, 발표에서는 "보조 경고"로 설명하는 것이 안전합니다.

## 실패 사례 관리

실패 사례 이미지와 실험 결과는 `legacy/results/`에 보관합니다. docs에는 결론과 확인 방법만 남깁니다.

## 발표 전 최소 테스트

```bat
python -m pytest tests/test_sentence.py tests/test_detect.py
```

통과 기준:

- 문장 규칙 테스트 통과
- 탐지 대상 클래스 테스트 통과
- 서버/Android 문장 정책과 충돌 없음
