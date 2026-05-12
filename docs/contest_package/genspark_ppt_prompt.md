# VoiceGuide PPT 젠스파크 프롬프트

> **사용법**: genspark.ai → Spark Slides → 아래 [전체 프롬프트] 전체 복사·붙여넣기

---

## 전체 프롬프트

```
Create a professional Korean presentation for an AI mobile app called "VoiceGuide".
Total slides: 16

---

[Design Direction]
Background: crisp white (#FFFFFF) or very light gray (#F8F9FB)
Primary color: deep navy (#0F2B4C)
Accent color: amber/orange (#F5A623) for key stats and highlights
Card background: light steel blue (#E8EEF6)
Decorative elements: subtle geometric arcs and circles in navy tones at slide corners — elegant, not overwhelming
Layout: card-based with soft shadows, generous whitespace
Typography: bold large headlines in navy, clean body text in dark gray
Numbers/stats: very large, amber-colored
Overall feel: clean, trustworthy, tech-forward — Samsung / Kakao level polish

---

[SLIDE 1 — Cover]
Large title: "VoiceGuide"
Team: "3팀"
Subtitle: "실시간 객체 탐지 기반 시각장애인 보행 보조 앱"
Core sentence: "스마트폰 카메라 하나로 전방 객체를 감지하고, 음성·진동으로 즉시 안내합니다."
Bottom right: Demo Day · 2026.05.13
Visual: smartphone showing camera view with YOLO bbox overlay (chair/person/door labels shown)
NO futuristic or AI stock image — use realistic phone camera scene with bounding boxes

---

[SLIDE 2 — Table of Contents]
Title: 목차
Core sentence: "제출 필수 목차에 맞춰 프로젝트 개요부터 자체 평가까지 설명합니다."

5 main items in cards:
1. 프로젝트 개요
2. 프로젝트 팀 구성 및 역할
3. 프로젝트 수행 절차 및 방법
4. 프로젝트 수행 경과
5. 자체 평가 의견

Small sub-items below:
· 고객여정지도  · 전체 아키텍처  · 파이프라인 노드 설명  · 데모 영상 흐름

---

[SLIDE 3 — 프로젝트 개요]
Title: 프로젝트 개요
Core sentence (large, navy): "길 안내가 아니라, 지금 앞의 위험."

Center: smartphone icon
3 surrounding feature cards:
① 온디바이스 추론 | 서버 없이 Android에서 즉시 탐지
② 음성·진동 안내 | 화면 없이도 위험 즉시 인지
③ 서버 기록·대시보드 | 이동 경로와 탐지 이력 모니터링

---

[SLIDE 4 — 국내 니즈와 문제 규모]
Title: 국내 니즈와 문제 규모
Core sentence: "보행 중 전방 위험 인지는 반복되는 실제 문제입니다."

3 large stat cards (numbers very large, amber):
Card 1: 2,627,761명 | 국내 등록장애인 수
Card 2: 245,361명 | 이 중 시각장애인 수
Card 3: 44,083명 | 심한 시각장애인 수 (일상 보행 시 전방 위험 노출)

Small footnote: 출처: 보건복지부 등록장애인 현황

---

[SLIDE 5 — 문제 정의]
Title: 문제 정의
Core sentence (large): "목적지보다 먼저 필요한 것은 지금 앞의 위험입니다."

4-panel grid (problem cards):
① 흰 지팡이 | 근거리 촉각 중심 — 멀리 있는 위험 감지 불가
② GPS 안내 | 경로 중심 — 지금 앞의 장애물 인식 안 함
③ 보행 인프라 | 모든 장소에 구축 불가, 사각지대 존재
④ 서버 추론형 앱 | 네트워크 지연, 오프라인 취약

---

[SLIDE 6 — 고객여정지도와 Pain Point]
Title: 고객여정지도와 Pain Point
Core sentence: "상황은 달라도 필요한 것은 즉시 인지 가능한 피드백입니다."

3-row journey map table:
Row 1 | 횡단보도 | 차량·자전거 접근 | 소리 단서 없으면 방향·거리 파악 어려움 | VoiceGuide: 접근 객체 방향·거리 즉시 안내
Row 2 | 실내/보도 | 의자·문·계단 등 장애물 | 갑작스러운 충돌 위험 | VoiceGuide: 전방 장애물 사전 안내
Row 3 | 혼잡한 장소 | 다수 객체 동시 탐지 | 과다 알림으로 오히려 혼란 | VoiceGuide: 위험도 기반 필터링으로 핵심만 안내

Label this slide as satisfying submission requirement: 고객여정지도(pain point 정리)

---

[SLIDE 7 — 해결 방향]
Title: 해결 방향
Core sentence (large): "위험 판단은 Android에서 즉시, 기록은 서버에서 분리합니다."

3 principle cards:
① 즉시 판단 | 온디바이스 추론 — 서버 응답 대기 없음
② 즉시 피드백 | TTS 음성 + 4단계 진동 — 화면 없이도 인지
③ 비동기 기록 | JSON → 서버 → DB → 대시보드

Flow diagram below:
카메라 입력 → Android 판단 → 음성·진동 안내
                    ↓ (비동기)
              서버 기록 · 대시보드

---

[SLIDE 8 — 팀 구성 및 역할]
Title: 팀 구성 및 역할
Core sentence: "역할을 나누어 MVP 흐름을 완성했습니다."

Clean table (5 rows):
정환주 | 팀장 | Android 앱 · 온디바이스 탐지 · TTS·진동 · 최종 통합
김재현 | 아키텍처 | 시스템 구조 정리 · 서버 구조 보완 · 문서화
임명광 | 백엔드 | 대시보드 · GPS·탐지 이력 표시 · 데모 시뮬레이션
문수찬 | UI | 대시보드 UI · 위험도 패널 · 시각화 개선
신유득 | 조사 | 초기 자료 조사 및 개발 환경 검토

---

[SLIDE 9 — 전체 아키텍처]
Title: 전체 아키텍처
Core sentence: "Android는 즉시 안내, 서버는 기록과 모니터링을 담당합니다."

Left panel (navy) — Android:
CameraX → TFLite YOLO → Risk Matching → TTS·진동

Right panel (steel blue) — Server:
POST /detect, /gps → FastAPI → DB(SQLite/PostgreSQL) / SSE → Dashboard

Important note on diagram: 서버로는 영상이 아니라 JSON이 전달됨 (이미지/YOLO 추론 없음)

Label: 전체 파이프라인 구조도(아키텍처) 제출 요구 충족

---

[SLIDE 10 — Android 파이프라인]
Title: Android 파이프라인
Core sentence: "탐지 결과를 안정화한 뒤 안내합니다."

6-node horizontal flow:
① CameraX | 카메라 프레임 입력
→ ② TFLite YOLO | GPU/XNNPACK 추론 (bbox·class·confidence)
→ ③ Vote + Dedup | 최근 3프레임 투표, IoU 중복 제거
→ ④ IoU Tracking | 동일 객체 연결, 트랙 유지
→ ⑤ EMA Smoothing | 위치·위험도 흔들림 평활화
→ ⑥ Feedback | TTS 문장 · 진동 패턴 · 서버 업로드

Add actual app screenshot or YOLO detection screen capture if available

Label: 파이프라인 구성 캡처 및 노드 설명 제출 요구 충족

---

[SLIDE 11 — 핵심 매칭 알고리즘]
Title: 핵심 매칭 알고리즘
Subtitle: "객체·방향·거리·위험도를 조합해 안내 시나리오를 결정합니다."

Left side — 4 input cards:
Object Class | chair / person / car / door / stairs
Direction | 정면 / 왼쪽 / 오른쪽
Distance | bbox 크기 기반 추정 (약 Xm)
Risk Score | 0.35 / 0.55 / 0.75

Center: arrow → Matching Engine →

Right side — 4 output cards:
TTS 문장 | "정면 약 1.5m에 의자가 있어요."
진동 패턴 | SHORT / DOUBLE / URGENT
UI 표시 | bbox · class · confidence
서버 기록 | POST /detect JSON

Matching table below (3 rows):
의자·문 | 정면 | SHORT | 짧은 진동 + TTS
사람·자전거 | 좌우 | DOUBLE | 두 번 진동 + TTS
차량·오토바이 | 전방 | URGENT | 긴급 진동 + 강한 TTS

Example line at bottom:
chair + 정면 + 가까움 + SHORT → "정면 약 1.5m에 의자가 있어요." + 짧은 진동

---

[SLIDE 12 — 기술 선정 이유]
Title: 기술 선정 이유
Core sentence: "실사용 가능한 속도와 안정성을 위해 온디바이스 구조를 선택했습니다."

5 tech cards:
yolo11n_320.tflite | 기본 탐지 모델 (320×320 입력)
yolo26n_float32.tflite | fallback 후보 모델
TFLite GPU / XNNPACK | 모바일 온디바이스 실행
IoU Tracking + EMA | 중복 알림 완화 · 흔들림 평활화
로컬 TTS | 네트워크 없이 즉시 음성 안내

Small note: yolo26n은 fallback 후보 — 자동 전환 기준은 실기 FPS 측정으로 확정 예정

---

[SLIDE 13 — 위험도 계산과 진동 패턴]
Title: 위험도 계산과 진동 패턴
Core sentence: "모든 객체를 똑같이 알리지 않고 위험도에 따라 다르게 안내합니다."

Formula card:
risk = centerWeight × distanceWeight × classWeight + sizeBoost

Risk level gauge (3 levels, visual):
SHORT  (≥0.35) | 짧은 1회 진동 | 일반 장애물
DOUBLE (≥0.55) | 짧은 2회 진동 | 이동 객체·주의
URGENT (≥0.75) | 긴급 반복 진동 | 차량·높은 위험

Distance weight table:
≤0.8m: 1.0 | ≤1.5m: 0.85 | ≤2.5m: 0.65 | ≤4.0m: 0.35 | >4.0m: 0.15

---

[SLIDE 14 — 구현 결과와 서버/API]
Title: 구현 결과와 서버/API
Core sentence: "탐지 결과는 안내 문장과 서버 기록으로 변환됩니다."

4-panel layout:
Panel 1 | YOLO 탐지 화면 | bbox · class · confidence 실시간 표시
Panel 2 | TTS 문장 | "정면 약 1.5m에 의자가 있어요."
Panel 3 | 서버 업로드 | POST /detect (JSON) · POST /gps (위치)
Panel 4 | 대시보드 | Leaflet 지도 · 실시간 탐지 이력

Key APIs (small card):
POST /detect | POST /gps | GET /status/{id} | GET /events/{id} | GET /history/{id} | GET /dashboard

---

[SLIDE 15 — 수행 경과: 검증 및 데모]
Title: 수행 경과: 검증 및 데모
Core sentence: "확보된 검증과 추가 측정 항목을 분리했습니다."

Left — 확보된 수치 (green checkmark):
✓ 자동 테스트: 23 passed, 9 deselected
✓ 서버 요청 평균: 26.37ms
✓ NLG 생성: 0.015ms

Right — 추가 측정 필요 (gray, honest):
△ Android 실기 FPS
△ mAP50 (모델 정확도)
△ 메모리 사용량
△ TTS-UI latency
△ 저조도 성능

Demo flow below (horizontal):
앱 실행 → bbox 확인 → TTS/진동 → POST 업로드 → 대시보드 확인

Note: 데모 영상 5~10분 이내 별도 제출

Label: 프로젝트 수행 경과 + 데모 영상 제출 요구 충족

---

[SLIDE 16 — 자체 평가 의견]
Title: 자체 평가 의견
Core sentence (large, navy): "완벽한 탐지 모델보다 실제 보행 중 끊기지 않는 안내 흐름을 우선했습니다."

3-column layout:
Column 1 — 잘된 점 ✓
· 온디바이스 탐지로 지연 없는 즉시 안내
· TTS·진동 이중 안내 구현
· 서버·Android 역할 분리 완성
· 오탐 제거(Vote·Tracking·EMA) 적용
· 오프라인 모드 동작

Column 2 — 부족한 점 △
· 실기 FPS·메모리 측정 미완료
· 저조도·야간 환경 미검증
· 거리 추정 정밀도 한계
· 실제 사용자 테스트 미완료

Column 3 — 개선 방향 →
· 성능 로그 DB화
· 거리 캘리브레이션·Depth 모델 검토
· 야간·혼잡 환경 검증
· 시각장애인 직접 사용자 테스트

Final closing line (bottom, emphasized):
"VoiceGuide는 보행 인프라를 대체하는 것이 아니라, 지금 앞의 위험을 한 번 더 알려주는 보조 안전 레이어입니다."
```

---

## 생성 후 직접 교체할 것

| 항목 | 방법 |
|---|---|
| 슬라이드 1 스마트폰 이미지 | 앱 실행 후 bbox 탐지 화면 스크린샷 |
| 슬라이드 10 앱 화면 | 실제 파이프라인 동작 화면 캡처 |
| 슬라이드 14 대시보드 | voiceguide-1063164560758.asia-northeast3.run.app/dashboard 캡처 |

---

## 발표 시간 계산

| 슬라이드 | 예상 시간 |
|---|---|
| 1~2 (표지·목차) | 1.5분 |
| 3~7 (개요·문제·해결) | 7분 |
| 8 (팀 구성) | 1.5분 |
| 9~13 (수행 절차·기술) | 7분 |
| 14~15 (수행 경과) | 2분 |
| 16 (자체 평가) | 1분 |
| **합계** | **약 20분** |
