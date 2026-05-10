# Gamma AI 발표자료 제작 지시사항

아래 내용을 Gamma AI에 그대로 붙여넣어 발표자료를 생성하세요.  
목표는 `VoiceGuide` 1차 프로젝트 발표용 PPT이며, 기존 산출물의 문제였던 작은 글자, 이상한 박스, 겹치는 장식, 칙칙한 색감을 반드시 피해야 합니다.

---

## Gamma에 넣을 최종 프롬프트

VoiceGuide 프로젝트의 1차 발표용 PPT를 만들어줘.

발표 대상은 교수/심사위원이며, 기술 구현을 모르는 사람도 이해할 수 있어야 하지만 내용은 얕으면 안 된다.  
핵심 메시지는 다음 문장이다.

> 정확도보다 실사용 가능한 실시간 FPS 확보를 우선시했다.

### 디자인 방향

- 어두운 테마 금지.
- 순백 배경만 반복하지 말고, 연한 민트 그레이 또는 따뜻한 아이보리 배경을 사용한다.
- 메인 색상은 네이비, 청록, 코랄 정도로 제한한다.
- 보라색/파란색 그라데이션, 큰 원 장식, 불필요한 테두리 박스, 복잡한 카드 남발 금지.
- 슬라이드 상단에 굵은 띠나 장식선을 넣지 않는다.
- 모든 글자는 발표장에서 보일 만큼 크게 만든다.
- 본문은 최소 20pt 이상, 제목은 36pt 이상으로 한다.
- 표는 꼭 필요한 경우만 사용하고, 가능하면 3단 컬럼, 타임라인, 번호 리스트로 표현한다.
- 한 슬라이드에는 핵심 메시지 하나만 둔다.
- 텍스트가 서로 겹치거나 도형과 겹치지 않게 충분한 여백을 둔다.
- “슬라이드 번호” 같은 기본 플레이스홀더가 보이지 않게 한다.
- 발표용으로 전문적이고 깔끔한 정보 디자인 느낌으로 만든다. 스타트업 IR 자료처럼 세련되지만 과장된 마케팅 느낌은 피한다.

### 반드시 포함할 내용

필수 목차:

1. 프로젝트 개요
2. 팀 구성 및 역할
3. 수행 절차 및 방법
4. 수행 경과
5. 자체 평가 의견

필수 포함 요소:

- 전체 아키텍처
- 파이프라인 노드 설명
- 고객여정지도와 Pain Point
- 생성 결과물: 객체탐지 결과, TTS 문장, JSON 업로드, 대시보드
- 데모 영상 또는 데모 시나리오 5~10분
- GitHub 링크: https://github.com/coding-jhj/VoiceGuide
- 성능 검증 지표: FPS, mAP50, 추론시간(ms), 메모리 사용량, latency

### 프로젝트 핵심 내용

VoiceGuide는 스마트폰 카메라 하나로 보행 중 전방 객체를 감지하고, 위험도에 따라 음성 안내와 진동 피드백을 제공하는 시각장애인 보행 보조 앱이다.

현재 구조는 서버에서 객체를 추론하는 방식이 아니라 Android 앱에서 온디바이스로 먼저 판단하는 구조다. 서버는 탐지/GPS 기록, 상태 조회, 대시보드 시각화, 이력 관리를 담당한다.

핵심 기술:

- Android CameraX
- TFLite YOLO
- yolo11n_320 기본 모델
- yolo26n_float32 fallback
- ByteTrack-lite 또는 IoU 기반 tracking
- 위험도 Smoothing
- risk_score 기반 진동 패턴
- 로컬 TTS 문장 생성
- FastAPI JSON 서버
- Leaflet dashboard

주요 API:

- POST /detect
- POST /gps
- GET /status/{session_id}
- GET /history/{session_id}
- GET /events/{session_id}
- GET /dashboard

확보된 검증 내용:

- 서버/시뮬레이션 테스트 22/22 통과
- 서버 요청 평균 약 26.37ms
- NLG 문장 생성 약 0.015ms
- Android 앱은 CameraX, TFLite YOLO, TTS, 진동 피드백, 서버 업로드 흐름을 연결함

아직 추가 측정이 필요한 항목:

- 실제 기기 모델별 FPS
- mAP50
- 메모리 사용량
- TTS-UI latency
- 저조도 환경 성능

이 값들은 임의로 만들어내지 말고 “추가 측정 필요” 또는 “발표 전 실기 측정값 반영”으로 정직하게 표시한다.

---

## 추천 슬라이드 구성

### 1. 표지

제목: VoiceGuide  
부제: 실시간 객체 탐지 기반 시각장애인 보행 보조 앱  
핵심 문장: 정확도보다 실사용 가능한 실시간 FPS 확보를 우선시했습니다.  
키워드: YOLO26n fallback, ByteTrack-lite, 위험도 Smoothing, 진동 패턴, 모바일 추론, JSON 기반 서버

디자인:

- 큰 제목과 한 줄 메시지를 중심에 둔다.
- 오른쪽에는 키워드만 간결하게 배치한다.
- 큰 원, 굵은 상단 띠, 다중 박스 금지.

### 2. 프로젝트 개요

핵심:

- 스마트폰 카메라로 전방 객체 감지
- Android 온디바이스 추론
- 음성/TTS와 진동 피드백
- 서버는 기록과 대시보드 담당

한 줄 메시지:

> 핵심 방향은 서버 추론형 앱이 아니라 Android 온디바이스 즉시 판단 구조입니다.

### 3. 팀 구성 및 역할

파트 중심으로 구성:

- Android 앱: CameraX, TFLite 연결, TTS, 진동 피드백
- AI 모델: YOLO11n/YOLO26n, 후처리, fallback
- 서버/DB/API: FastAPI, /detect, /gps, 상태/이력 API
- 대시보드/데모: Leaflet dashboard, simulator.py, 데모 영상

표보다 번호 리스트 또는 4개 역할 블록으로 표현한다.

### 4. 문제 정의

내용:

- GPS 안내는 경로에는 강하지만 전방 장애물을 보지 못함
- 흰 지팡이는 근거리 촉각 정보 중심
- 전용 웨어러블은 비용과 착용 부담이 큼

한 줄 메시지:

> 보행 중 정말 필요한 정보는 길 안내가 아니라 지금 앞의 위험입니다.

### 5. 고객여정지도와 Pain Point

상황별 구성:

- 횡단보도: 차량 접근 인지 어려움 → 차량/자전거 감지, 위험도 상향
- 실내/보도: 의자·문·계단 미감지 → 거리·방향 기반 음성 안내
- 혼잡한 장소: 움직이는 객체 추적 어려움 → IoU tracking + EMA smoothing

### 6. 기존 방식의 한계

비교:

- 흰 지팡이: 근거리 중심
- GPS 안내 앱: 경로 중심
- 서버 추론형 앱: 지연과 오프라인 취약성

결론:

> 앱에서 먼저 판단하고, 서버는 기록과 모니터링을 맡는 구조가 필요합니다.

### 7. 전체 아키텍처

흐름:

CameraX → TFLite YOLO → Tracking → Risk Analyzer → TTS/Vibration  
그리고 서버로 POST /detect, POST /gps 전송

강조:

- Android 즉시 안내
- 서버 기록/대시보드 분리
- JSON 기반 상태 공유

### 8. 파이프라인 노드 설명

노드별 설명:

- CameraX: 프레임 입력, YUV → RGB, 320x320 letterbox
- TFLite YOLO: bbox, class, confidence 산출
- Vote + Tracking: 중복 제거, 3프레임 vote, IoU 0.25 기준 track 연결
- Risk Analyzer: 중심성, 거리, 클래스 가중치로 risk_score 계산
- Feedback/Server: SentenceBuilder 문장, 진동 패턴, JSON 업로드

### 9. 기술 선정 이유

내용:

- YOLO11n/yolo11n_320: 기본 탐지 모델
- YOLO26n/yolo26n_float32: fallback 구조
- ByteTrack-lite: 같은 객체를 프레임 간 이어서 ID 안정화
- 모바일 추론: 서버 왕복 없이 즉시 안내

한 줄 메시지:

> 정상 환경은 정확도 중심, FPS 저하 상황은 fallback으로 사용 가능성을 확보하는 전략입니다.

### 10. 위험도 Smoothing과 진동 패턴

공식:

risk = centerWeight × distanceWeight × classWeight + sizeBoost

패턴:

- SHORT: risk ≥ 0.35
- DOUBLE: risk ≥ 0.55
- URGENT: risk ≥ 0.75
- 차량 클래스는 risk ≥ 0.55부터 URGENT로 상향

### 11. 생성 결과물

결과물:

- 객체탐지: class_ko, confidence, bbox
- TTS 문장: “정면 약 1.5m에 의자가 있어요.”
- JSON 업로드: POST /detect objects[] + GPS
- 대시보드: 지도 경로, 현재 객체, 위험도, 24시간 이력

### 12. 성능 검증 포인트

확보:

- 테스트 22/22 통과
- 서버 요청 평균 약 26.37ms
- NLG 약 0.015ms

추가 측정 필요:

- 실제 기기 FPS
- mAP50
- 메모리 사용량
- TTS-UI latency
- 저조도 안정성

임의 수치 생성 금지.

### 13. 테스트 환경과 실험 방법

검증 항목:

- 스마트폰 실기: VG_PERF 로그로 FPS, preprocess, infer, total 시간 기록
- 거리 테스트: 1m, 3m, 5m 고정 물체
- 환경 비교: 밝은 실내, 저조도, 복도
- 서버 연동: simulator.py + dashboard

### 14. 수행 경과

타임라인:

- 4/24: FastAPI + Android 뼈대
- 4/29: FPS 10+ 목표, 내장 TTS 전환
- 4/30: GCP Cloud Run 배포
- 5/03: MVP 스코프 확정
- 5/07: yolo11n_320 + fallback 통합
- 5/08: 심각 버그 4건, 개선 11건 수정

### 15. 결과 및 데모 안내

5~10분 데모 흐름:

1. 앱 실행 및 카메라 활성화
2. 객체 탐지 확인
3. 위험 안내: TTS 문장, 진동 패턴
4. GPS와 /detect 업로드
5. dashboard에서 지도 경로, 현재 객체, 24시간 이력 확인
6. 실패 대비: demo-device-02 시뮬레이터 백업

### 16. 자체 평가 의견

잘된 점:

- 모바일 탐지 → TTS/진동 → 서버 기록 → 대시보드까지 MVP 흐름 연결

부족한 점:

- 실기 FPS, mAP50, 메모리, 저조도 성능은 추가 측정 필요

개선 방향:

- YOLO26n fallback 정책 명확화
- 경량 Depth 적용
- NPU/GPU 최적화
- 실제 사용자 UAT

최종 메시지:

> 완벽한 탐지 모델보다 실제 보행 중 끊기지 않는 안내 흐름을 우선했습니다.

---

## Gamma 생성 후 확인 체크리스트

- [ ] 글자가 작지 않은가?
- [ ] 표가 너무 많지 않은가?
- [ ] 박스가 겹치거나 불필요하게 많지 않은가?
- [ ] 큰 원, 장식선, 플레이스홀더가 남아 있지 않은가?
- [ ] 색이 네이비/청록/코랄 중심으로 통일됐는가?
- [ ] 전체 목차 5개가 모두 들어갔는가?
- [ ] 아키텍처와 파이프라인이 모두 들어갔는가?
- [ ] FPS, mAP50, latency 등 성능 지표가 들어갔는가?
- [ ] 아직 없는 수치를 지어내지 않았는가?
- [ ] GitHub 링크가 들어갔는가?
