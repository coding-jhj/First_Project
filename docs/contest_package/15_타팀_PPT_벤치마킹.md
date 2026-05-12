# 타팀 PPT 벤치마킹 및 VoiceGuide 보완 방향

분석 대상:

| 구분 | 파일 | 페이지 | 텍스트 추출 상태 |
|---|---:|---:|---|
| 타팀 | `MP TELLAR 최종본.pdf` | 31p | 양호 |
| 타팀 | `6팀_프로젝트1_PPT.pdf` | 33p | 대부분 이미지 기반 |
| 타팀 | `1팀 발표 자료.pdf` | 34p | 양호 |
| 타팀 | `ESTsof_2팀_수어통역기(최종본).pdf` | 24p | 양호 |
| 타팀 | `SchoolBridge.pdf` | 23p | 일부 글자 깨짐 있으나 구조 파악 가능 |
| 우리팀 | `VoiceGuide_미완성.pdf` | 16p | 텍스트 레이어 없음 |

> 주의: 6팀 자료와 우리팀 `VoiceGuide_미완성.pdf`는 PDF 안의 텍스트가 거의 추출되지 않아 세부 문장 분석은 제한적이다. 다만 이 자체도 개선 포인트다. 최종 PPT는 텍스트 레이어가 살아 있어야 검색, 복사, 발표자 검토, 접근성 측면에서 유리하다.

## 1. 전체 결론

우리 VoiceGuide 자료는 현재 기능 자체는 충분히 설명할 수 있는 재료가 있다. 문제는 발표자료에서 그 재료가 `왜 필요한가 -> 어떻게 해결했나 -> 실제로 동작하나 -> 한계와 다음 단계는 무엇인가` 흐름으로 강하게 묶여야 한다는 점이다.

타팀 자료에서 가장 많이 참고할 만한 점은 다음 5가지다.

1. 문제 정의를 숫자와 사용자 상황으로 먼저 설득한다.
2. 고객여정지도 또는 사용 시나리오로 Pain Point를 구체화한다.
3. 기술 스택을 단순 나열하지 않고 문제와 1:1로 연결한다.
4. 시스템 아키텍처와 파이프라인을 실제 구현 기준으로 보여준다.
5. 자체평가에서 잘한 점과 한계를 정직하게 나누고, 개선 계획을 구체적으로 쓴다.

VoiceGuide는 `시각장애인 보행 보조`라는 주제가 명확하므로, 발표 흐름만 다듬으면 설득력이 크게 올라간다.

## 2. 팀별 벤치마킹 포인트

### MP TELLAR

좋았던 점:

- 표지에서 서비스 한 줄 정의가 명확하다: `부모님 목소리로 읽어주는 동화 앱`.
- 목차가 평가 항목과 거의 1:1로 맞다: 프로젝트 개요, 팀 구성, 수행 절차, 수행 경과, 자체평가.
- 문제 배경을 통계, 뉴스, 자체 설문으로 3단 구성했다.
- 팀 역할을 `TTS`, `NLP`, `API`, `UI/UX`, `DevOps`처럼 기능 단위로 나누어 보인다.
- 3주 일정이 `기획 -> 핵심 개발 -> 통합 테스트`로 단순하고 이해하기 쉽다.
- 기능 소개를 번호별로 쪼개 발표자가 설명하기 좋게 만들었다.

VoiceGuide 적용:

- 표지 부제를 `실시간 객체 탐지 기반 시각장애인 보행 보조 앱`으로 고정한다.
- 문제 근거 슬라이드에 국내 시각장애인 수, 보행 중 장애물 인지 문제, 흰 지팡이/GPS의 한계를 숫자와 표로 넣는다.
- 팀 역할은 이름 중심보다 책임 모듈 중심으로 재정리한다.
  - Android 온디바이스 탐지
  - TTS/진동 피드백
  - FastAPI 서버/DB
  - GPS/대시보드
  - 발표자료/시연영상

### 1팀 Voice AI Analyzer

좋았던 점:

- 피해액, 피해 건수, 연령대 비율처럼 문제의 심각성을 숫자로 바로 보여준다.
- 기존 대응 수단의 한계를 표로 정리해 “왜 우리 솔루션이 필요한가”가 선명하다.
- 고객여정지도를 통해 사용자가 피해를 입는 과정을 단계별로 보여준다.
- 솔루션 설명이 `문맥 분석`, `딥페이크 탐지`, `위험도 표시`로 분리되어 이해하기 쉽다.
- `문제 상황 -> Vaia의 대응 -> 적합한 이유` 표가 매우 좋다.
- 기술 설명에서 STT, NLU, RawNet2 등 선택 이유를 따로 설명한다.

VoiceGuide 적용:

- `현재 보행 보조 수단의 한계` 표를 추가한다.

| 기존 수단 | 장점 | 한계 | VoiceGuide 보완점 |
|---|---|---|---|
| 흰 지팡이 | 즉각적, 저비용 | 근거리 접촉 전까지 인지 어려움 | 카메라로 전방 객체를 사전 감지 |
| GPS 길 안내 | 경로 안내 가능 | 눈앞 장애물 인식 불가 | 방향, 거리, 객체를 음성/진동으로 안내 |
| 보호자 동행 | 안전성 높음 | 항상 가능하지 않음 | 혼자 이동할 때 보조 안전 레이어 제공 |
| 일반 카메라 앱 | 화면 확인 가능 | 시각장애인은 화면 확인 어려움 | TTS와 진동 중심 피드백 |

- `문제 상황 -> VoiceGuide 대응 -> 적합한 이유` 표를 넣는다.

| 문제 상황 | VoiceGuide 대응 | 적합한 이유 |
|---|---|---|
| 정면 장애물을 늦게 인지 | TFLite YOLO로 객체 탐지 | 스마트폰 카메라만으로 즉시 분석 |
| 화면을 보기 어려움 | TTS + 진동 안내 | 시각 정보 없이도 위험 인지 가능 |
| 네트워크가 불안정 | 온디바이스 우선 처리 | 서버 응답 지연과 무관하게 안내 가능 |
| 기록과 검증 필요 | 서버에 JSON/GPS 저장 | 대시보드에서 탐지 이력 확인 가능 |

### 2팀 수어통역기

좋았던 점:

- 주제 선정 배경이 법/현장/사용자 불편으로 연결된다.
- 고객여정지도에 `행동`, `접점`, `감정`, `Pain Point`, `Our Solution`이 모두 있다.
- 적용 대상과 개발 범위를 명확히 썼다.
- 시스템 아키텍처가 `사용자 -> 프론트엔드 -> 실시간 서버 -> 백엔드 API -> 외부 API` 계층으로 정리되어 있다.
- 모델 결과를 정확도, 손실, 처리 시간 등 수치로 제시했다.
- 자체평가에서 성과와 한계가 구분되어 있고, 향후 개선 방향이 실제 기술 과제로 이어진다.

VoiceGuide 적용:

- 고객여정지도를 반드시 넣는 것이 좋다.

| 단계 | 사용자 행동 | 불편/위험 | VoiceGuide 대응 |
|---|---|---|---|
| 출발 | 스마트폰 앱 실행 | 주변 상황을 빠르게 파악하기 어려움 | 카메라 분석 시작, TTS 준비 |
| 보행 | 전방 이동 | 의자, 사람, 차량, 계단 등 인지 지연 | YOLO 객체 탐지 |
| 위험 접근 | 장애물이 가까워짐 | 충돌 전까지 위험 판단 어려움 | 거리/방향/위험도 계산 |
| 안내 수신 | 화면 확인 없이 이동 | 화면 중심 UI는 사용하기 어려움 | 음성 문장 + 진동 패턴 |
| 기록 확인 | 보호자/관리자가 상황 확인 | 이동 중 위험 기록이 남지 않음 | 서버 DB, GPS, 대시보드 |

- 시스템 아키텍처는 실제 구현 기준으로 써야 한다.
  - Android: `CameraX -> TFLite YOLO -> Risk Matching -> TTS/진동`
  - Server: `POST /detect`, `POST /gps`, `GET /status`, `GET /routes`
  - DB/Dashboard: 탐지 이벤트, GPS track, 최근 상태 표시
  - 핵심 문장: `서버가 이미지를 받아 YOLO를 돌리는 구조가 아니라, Android가 온디바이스로 탐지한 JSON을 서버에 보낸다.`

### SchoolBridge

좋았던 점:

- “우리가 아직 부족한 부분”을 숨기지 않고 정직하게 인정한다.
- 대신 핵심 정보 보존, 도메인 글로사리, 슬롯 보호처럼 자신들이 잘한 좁은 범위를 강하게 설명한다.
- 데이터 규모와 모델 지표를 숫자로 보여준다.
- 3주 개발 일정과 역할이 구체적이다.
- 자체평가를 `완성도 6/10`처럼 솔직하게 쓰되, 개선 방향을 바로 붙인다.

VoiceGuide 적용:

- 완성도 표현은 과장하지 않는 것이 좋다.
  - 나쁜 표현: `시각장애인 보행 문제를 해결한다.`
  - 좋은 표현: `흰 지팡이와 GPS를 대체하지 않고, 지금 앞의 위험을 한 번 더 알려주는 보조 안전 레이어다.`

- 한계도 발표자료에 넣어야 한다.

| 한계 | 왜 중요한가 | 다음 개선 방향 |
|---|---|---|
| 실제 시각장애인 사용자 테스트 부족 | 안전 서비스는 실제 사용성 검증이 중요 | 사용자 테스트와 피드백 수집 |
| 거리 추정 정확도 제한 | 잘못된 거리 안내는 위험할 수 있음 | Depth/센서 융합 또는 보수적 거리 표현 |
| TTS-UI latency 정량 측정 부족 | 안내 지연은 체감 안전성과 직결 | 지연 시간 측정표 추가 |
| 복잡한 환경에서 오탐/누락 가능 | 야외, 역광, 혼잡 환경 대응 필요 | 다양한 환경 테스트셋 구축 |

### 6팀 자료

분석 한계:

- 33페이지로 구성은 충분히 길지만 PDF 텍스트가 거의 이미지로 저장되어 세부 내용 추출이 어렵다.
- 일부 추출된 내용상 TTS, 안내방송, 상황별 안내 흐름이 포함된 것으로 보인다.

VoiceGuide 적용:

- 이미지 기반 PPT를 만들더라도 최종 제출 PDF는 텍스트가 살아 있게 내보내는 것이 좋다.
- 이미지 위주의 슬라이드는 발표자가 말로 보완해야 하므로, 핵심 문장 1개와 단계 번호를 꼭 넣어야 한다.

## 3. VoiceGuide 현재 자료에서 부족해 보이는 부분

`VoiceGuide_미완성.pdf`는 16페이지이고 텍스트 추출이 되지 않았다. 내용 자체를 직접 읽어 비교하기 어렵지만, 현재 repo 문서와 타팀 자료 기준으로 보면 보완해야 할 가능성이 높은 항목은 다음과 같다.

1. 문제 정의가 약하면 기술 설명이 설득력을 잃는다.
2. “시각장애인에게 왜 필요한가”가 통계와 실제 보행 상황으로 먼저 제시되어야 한다.
3. 기술 스택보다 `사용자 위험 -> 시스템 판단 -> 음성/진동 안내` 흐름이 먼저 보여야 한다.
4. 온디바이스 구조의 장점이 강조되어야 한다.
5. 서버 역할을 정확히 설명해야 한다. 서버는 YOLO 추론 서버가 아니라 기록/대시보드/이력 조회 서버다.
6. 테스트 결과가 없으면 “구현했다”에서 끝나 보인다. FPS, TTS 지연, 탐지 예시, 서버 업로드 확인 같은 작은 수치라도 넣어야 한다.
7. 자체평가는 잘한 점만 쓰지 말고 한계와 개선 방향을 같이 넣어야 한다.

## 4. 추천 PPT 구조

현재 `docs/contest_package/07_PPT_16장_최종구성.md`의 16장 구조를 유지하되, 타팀 자료의 장점을 반영해 아래처럼 강화하는 것을 추천한다.

| 장 | 제목 | 벤치마킹 반영 포인트 |
|---:|---|---|
| 1 | 표지 | 한 줄 정의를 크게: `실시간 객체 탐지 기반 시각장애인 보행 보조 앱` |
| 2 | 목차 | 평가 항목과 동일하게 구성 |
| 3 | 프로젝트 개요 | 대상 사용자, 문제, 해결 방식 3줄 요약 |
| 4 | 문제 정의 | 시각장애인 수, 보행 위험, 기존 수단 한계 |
| 5 | 고객여정지도 | 보행 전/중/위험 접근/안내/기록 단계 |
| 6 | 솔루션 컨셉 | CameraX, YOLO, TTS, 진동, 서버 기록 |
| 7 | 팀 구성 및 역할 | 사람보다 책임 모듈 중심 |
| 8 | 개발 일정 | 3주 일정: 기획, 핵심 개발, 통합/검증 |
| 9 | 시스템 아키텍처 | Android 온디바이스 + 서버 기록 구조 |
| 10 | 탐지 파이프라인 | CameraX -> TFLite YOLO -> 후처리 -> 위험도 |
| 11 | 안내 로직 | 객체/방향/거리/위험도 -> TTS/진동 매칭 |
| 12 | 서버/대시보드 | POST /detect, GPS, DB, dashboard |
| 13 | 시연 시나리오 | 앱 실행 -> bbox -> TTS/진동 -> 서버 업로드 -> 대시보드 |
| 14 | 검증 결과 | FPS, TTS 지연, 탐지 예시, 로그/대시보드 캡처 |
| 15 | 자체평가 | 성과, 한계, 개선 방향 |
| 16 | Q&A | 핵심 메시지 재강조 |

## 5. 바로 추가하면 좋은 슬라이드 4개

### 1. 기존 수단의 한계

1팀 자료처럼 표로 보여주면 좋다.

핵심 문장:

> 기존 보행 보조 수단은 경로 안내나 근거리 접촉에는 강하지만, 스마트폰 전방 카메라로 지금 앞의 객체를 즉시 해석해 음성·진동으로 알려주는 부분은 부족합니다.

### 2. 고객여정지도

2팀 자료처럼 사용자의 행동과 감정을 넣으면 주제가 사람 중심으로 보인다.

핵심 문장:

> VoiceGuide는 사용자가 화면을 보지 않아도 위험을 인지할 수 있도록, 보행 중 판단 결과를 음성과 진동으로 변환합니다.

### 3. 문제-기술 적합성 표

1팀의 `문제 상황 -> 대응 -> 적합한 이유` 구조를 그대로 응용한다.

핵심 문장:

> 기술을 많이 붙인 프로젝트가 아니라, 보행 중 즉시성이 필요한 문제에 맞춰 온디바이스 탐지와 로컬 피드백을 우선했습니다.

### 4. 정직한 자체평가

SchoolBridge처럼 솔직한 한계가 오히려 신뢰를 준다.

핵심 문장:

> 현재 VoiceGuide는 보행 안전을 완전히 해결하는 제품이 아니라, 실제 사용자 테스트와 환경 다양성 검증을 통해 고도화해야 하는 MVP입니다.

## 6. 발표에서 강조할 문장

아래 문장들은 PPT 본문이나 발표자 노트에 그대로 써도 좋다.

- VoiceGuide는 스마트폰 카메라로 지금 앞의 위험을 감지하고, 음성·진동으로 즉시 알려주는 시각장애인 보행 보조 MVP입니다.
- 서버 응답을 기다려야만 안내되는 구조가 아니라, Android에서 온디바이스로 먼저 판단하고 즉시 피드백합니다.
- 서버는 영상 분석 서버가 아니라, 탐지 JSON과 GPS를 저장하고 대시보드에서 확인하게 해주는 기록/관제 역할입니다.
- 흰 지팡이와 GPS를 대체하려는 것이 아니라, 전방 위험을 한 번 더 알려주는 보조 안전 레이어입니다.
- 이번 단계에서는 실제 동작하는 MVP를 만들고, 한계는 테스트 지표와 개선 계획으로 정리했습니다.

## 7. 최종 PPT 체크리스트

- [ ] 표지에서 서비스 정의가 3초 안에 이해되는가?
- [ ] 문제 정의에 숫자와 출처가 있는가?
- [ ] 기존 수단의 한계와 VoiceGuide의 차별점이 표로 정리되어 있는가?
- [ ] 고객여정지도가 있는가?
- [ ] Android 온디바이스 탐지 구조가 명확한가?
- [ ] 서버가 YOLO를 돌린다고 오해할 여지가 없는가?
- [ ] 실제 앱 화면 또는 YOLO bbox 캡처가 있는가?
- [ ] TTS/진동 안내 예시 문장이 있는가?
- [ ] 시연 흐름이 슬라이드만 봐도 이해되는가?
- [ ] FPS, latency, API 로그, 대시보드 등 검증 근거가 최소 1개 이상 있는가?
- [ ] 한계와 개선 방향이 정직하게 들어가 있는가?
- [ ] 최종 PDF에서 텍스트 선택/검색이 가능한가?

## 8. 우선순위

시간이 부족하면 아래 순서대로 고치면 된다.

1. 표지와 프로젝트 한 줄 정의 수정
2. 문제 정의 + 기존 수단 한계 표 추가
3. 고객여정지도 추가
4. 시스템 아키텍처를 실제 구현 기준으로 수정
5. 시연 시나리오와 검증 결과 추가
6. 자체평가를 성과/한계/개선 방향으로 재작성

이 6가지만 반영해도 VoiceGuide 발표자료는 “기능 나열”에서 “문제 해결형 프로젝트 발표”로 훨씬 단단해진다.

## 9. 코드/그래프 기반 기술 보완 방향

앞의 내용은 발표 흐름 중심이었다. 그런데 타팀 자료를 보면 단순히 “이런 기능을 만들었다”가 아니라, 코드 일부와 성능 그래프를 넣어서 실제 구현 근거를 보여준다. VoiceGuide도 기술 설명이 부족해 보이지 않으려면 아래 내용을 반드시 보강해야 한다.

VoiceGuide는 코드 기준으로 보여줄 재료가 충분하다. 핵심은 `Android 온디바이스 추론 -> 안정화 -> 위험도 계산 -> TTS/진동 -> 서버 기록/대시보드` 흐름을 실제 코드와 수치로 보여주는 것이다.

### 9-1. PPT에 넣을 실제 코드 근거

| 슬라이드 주제 | 넣을 코드/근거 | 파일 |
|---|---|---|
| 온디바이스 YOLO 추론 | TFLite 모델 선택, GPU delegate/XNNPACK fallback, `preprocessMs`, `inferMs`, `postprocessMs` 분리 측정 | `android/app/src/main/java/com/voiceguide/TfliteYoloDetector.kt` |
| YOLO 후처리 | confidence threshold 0.30, NMS IoU 0.45, bbox/class/confidence 추출 | `TfliteYoloDetector.kt` |
| 오탐/중복 안내 방지 | 최근 프레임 vote, 동일 객체 IoU dedup, 서버 업로드 signature 비교 | `MainActivity.kt` |
| 객체 추적/안정화 | IoU 0.25로 track 연결, EMA alpha 0.55로 bbox/거리/risk smoothing | `MvpPipeline.kt` |
| 위험도 계산 | `centerWeight * distanceWeight * classWeight + sizeBoost` 산식 | `MvpPipeline.kt` |
| 진동 패턴 | risk 0.35/0.55/0.75 기준으로 SHORT/DOUBLE/URGENT | `MvpPipeline.kt`, `MainActivity.kt` |
| TTS 문장 생성 | 객체 종류, 방향, 거리, 위험도 순으로 한국어 안내 문장 생성 | `SentenceBuilder.kt`, `src/nlg/sentence.py` |
| 서버 기록 | Android가 만든 객체 JSON, risk_score, track_id, client_perf 업로드 | `MainActivity.kt`, `src/api/routes.py` |
| 성능 DB | fps, infer_ms, preprocess_ms, postprocess_ms, process_ms, nlg_ms 저장 구조 | `src/api/db.py` |
| 대시보드/히트맵 | `/status`, `/events`, `/history`, `/heatmap` API | `src/api/routes.py`, `src/api/db.py` |

### 9-2. 기술 슬라이드로 꼭 넣어야 할 6장

기존 16장 구성에서 기술 설명이 약하면 아래 6장을 강화해야 한다.

| 권장 장 | 제목 | 핵심 메시지 | 시각 자료 |
|---:|---|---|---|
| 9 | 시스템 아키텍처 | 서버가 영상을 분석하지 않고 Android가 먼저 판단한다 | Android/Server 분리 다이어그램 |
| 10 | 온디바이스 YOLO 추론 | CameraX 프레임을 TFLite YOLO로 실시간 분석한다 | 코드 스니펫 + 모델 파일 표 |
| 11 | 탐지 안정화 파이프라인 | 단일 프레임 결과를 바로 말하지 않고 vote/dedup/tracking으로 안정화한다 | 파이프라인 노드 그래프 |
| 12 | Risk Score & Feedback | 객체 종류, 거리, 화면 중심성을 점수화해 TTS/진동 강도를 결정한다 | risk 산식 + 막대그래프 |
| 13 | 서버/대시보드 | 탐지 결과와 GPS를 저장해 상태, 이력, 히트맵으로 보여준다 | API 흐름도 + DB 컬럼 일부 |
| 14 | 검증 결과 | 확보된 수치와 미측정 항목을 분리한다 | 성능 막대그래프 + 테스트 표 |

### 9-3. 코드 스니펫 후보

PPT에는 긴 코드를 넣으면 읽기 어렵다. 아래처럼 6~12줄 정도만 넣고, 나머지는 발표자 노트로 빼는 것이 좋다.

#### 온디바이스 추론

```kotlin
// TfliteYoloDetector.kt
val tInfer = System.nanoTime()
interpreter.run(inputBuffer, outputBuffer)
val inferMs = elapsedMs(tInfer)

val detections = if (isRawOutput)
    postProcessRaw(outputBuffer[0], padX, padY, scaledW, scaledH)
else
    postProcessEndToEnd(outputBuffer[0], padX, padY, scaledW, scaledH)
```

발표 포인트:

- Android에서 직접 YOLO를 실행한다.
- 추론 시간과 후처리 시간을 분리해서 로그로 남긴다.
- GPU delegate 실패 시 XNNPACK으로 fallback한다.

#### 오탐 방지와 객체 안정화

```kotlin
// MainActivity.kt + MvpPipeline.kt
val mvpFrame = mvpPipeline.update(
    removeDuplicates(voteOnly(rawDetections))
)

track.cx = EMA_ALPHA * det.cx + (1f - EMA_ALPHA) * track.cx
track.distanceM = EMA_ALPHA * rawDistance + (1f - EMA_ALPHA) * track.distanceM
track.risk = EMA_ALPHA * rawRisk + (1f - EMA_ALPHA) * track.risk
```

발표 포인트:

- 단일 프레임 탐지 결과를 바로 안내하지 않는다.
- vote로 순간 오탐을 줄이고, IoU/EMA로 같은 물체의 흔들림을 줄인다.
- 시각장애인 대상 앱이라 “많이 말하기”보다 “필요한 것만 안정적으로 말하기”가 중요하다.

#### 위험도 계산

```kotlin
// MvpPipeline.kt
val centerWeight = 1f - min(0.6f, abs(det.cx - 0.5f) * 1.2f)
val distanceWeight = when {
    distanceM <= 0.8f -> 1.0f
    distanceM <= 1.5f -> 0.85f
    distanceM <= 2.5f -> 0.65f
    distanceM <= 4.0f -> 0.35f
    else -> 0.15f
}
return (centerWeight * distanceWeight * classWeight + sizeBoost).coerceIn(0f, 1f)
```

발표 포인트:

- 가까운 물체, 화면 중앙 물체, 차량/위험물에 더 높은 점수를 준다.
- 단순 confidence가 아니라 사용자에게 실제로 위험한 정도를 계산한다.

#### 진동 패턴

```kotlin
// MvpPipeline.kt
return when {
    risk >= 0.75f -> VibrationPattern.URGENT
    risk >= 0.55f -> VibrationPattern.DOUBLE
    risk >= 0.35f -> VibrationPattern.SHORT
    else -> VibrationPattern.NONE
}
```

발표 포인트:

- 화면을 보지 않아도 위험 강도를 느낄 수 있게 설계했다.
- 차량은 risk 0.55 이상부터 URGENT로 올리는 예외 처리가 있다.

#### 서버 업로드 JSON

```kotlin
// MainActivity.kt
objects.put(JSONObject()
    .put("class_ko", d.classKo)
    .put("confidence", d.confidence.toDouble())
    .put("bbox_norm_xywh", JSONArray(listOf(x, y, w, h)))
    .put("distance_m", d.distanceM.toDouble())
    .put("risk_score", d.riskScore.toDouble())
    .put("track_id", d.trackId)
    .put("vibration_pattern", d.vibrationPattern))
```

발표 포인트:

- 서버에는 영상이 아니라 정제된 탐지 JSON만 보낸다.
- 개인정보/대역폭/지연 측면에서 서버 추론형보다 가볍다.

#### 서버 성능 기록

```python
# db.py
performance_metrics(
    model_name, provider, fps,
    infer_ms, preprocess_ms, postprocess_ms,
    process_ms, tracker_ms, nlg_ms,
    object_count, tts_latency_ms, memory_mb
)
```

발표 포인트:

- 성능을 말로만 주장하지 않고 저장할 수 있는 테이블 구조가 있다.
- 다만 Android FPS, mAP50, TTS latency는 실기 측정값을 추가 확보해야 한다.

### 9-4. 그래프로 만들 내용

타팀처럼 그래프나 표를 넣으려면 아래 5개가 가장 좋다.

#### 그래프 1. Risk Score 거리별 변화

PPT 막대그래프 데이터:

| 거리 | distanceWeight | 차량 risk 기준값 | 일반 물체 risk 기준값 |
|---|---:|---:|---:|
| 0.8m 이하 | 1.00 | 1.00 | 0.45 |
| 1.5m 이하 | 0.85 | 0.85 | 0.38 |
| 2.5m 이하 | 0.65 | 0.65 | 0.29 |
| 4.0m 이하 | 0.35 | 0.35 | 0.16 |
| 4.0m 초과 | 0.15 | 0.15 | 0.07 |

설명:

- `centerWeight=1.0`, `sizeBoost 제외` 기준의 단순화 그래프다.
- 차량과 일반 물체의 위험도 차이를 한눈에 보여줄 수 있다.

#### 그래프 2. 진동 패턴 임계값

PPT 게이지 데이터:

| risk_score | 상태 | 진동 |
|---:|---|---|
| 0.00~0.34 | 안전/낮음 | NONE |
| 0.35~0.54 | 주의 | SHORT |
| 0.55~0.74 | 경고 | DOUBLE |
| 0.75~1.00 | 위험 | URGENT |

설명:

- “위험도 점수가 실제 사용자 피드백으로 어떻게 바뀌는가”를 보여준다.

#### 그래프 3. 성능 수치 막대그래프

현재 문서에 확보된 수치:

| 항목 | 수치 |
|---|---:|
| 자동 테스트 | 22/22 passed 또는 최신 기준 재측정 필요 |
| 서버 요청 평균 | 26.37ms |
| NLG 문장 생성 | 0.015ms |
| YOLO 단독 속도 | 29ms, 문서 기준 |

주의:

- 이 수치는 문서 기준이다. 최종 발표 전 `pytest`와 실제 기기 Logcat 기준으로 최신값을 다시 확인해야 한다.
- Android 실기 FPS, mAP50, TTS-UI latency는 “측정 필요”로 분리해야 한다. 없는 수치를 만들면 안 된다.

#### 그래프 4. 파이프라인 처리 시간 분해

PPT에 넣을 항목:

| 단계 | 측정 필드 |
|---|---|
| 전처리 | `preprocess_ms` |
| YOLO 추론 | `infer_ms` |
| 후처리/MVP | `dedup_ms`, `postprocess_ms` |
| 서버 처리 | `process_ms`, `tracker_ms`, `nlg_ms` |
| 전체 | `total_ms` |

설명:

- `VG_PERF` Logcat과 `performance_metrics` DB 구조를 근거로 한다.
- 실제 측정 로그를 캡처하면 타팀의 모델 성능 그래프처럼 강한 근거가 된다.

#### 그래프 5. 대시보드 히트맵/이력

코드 근거:

- `/history/{session_id}`: 최근 24시간 탐지 이력
- `/heatmap/{session_id}`: GPS 좌표 + 최대 risk_score 기반 히트맵
- `/events/{session_id}`: SSE 실시간 상태 스트림

PPT 구성:

- 왼쪽: 지도/히트맵 스크린샷
- 오른쪽: API 흐름 `POST /detect -> DB -> /events SSE -> Dashboard`
- 하단: `risk_score`가 높을수록 heatmap intensity가 커진다는 설명

### 9-5. VoiceGuide 기술 설명의 핵심 문장

아래 문장들은 기술 슬라이드에 꼭 들어가야 한다.

- VoiceGuide는 서버에 영상을 보내 분석하는 구조가 아니라, Android에서 TFLite YOLO를 실행해 즉시 판단합니다.
- YOLO의 단일 프레임 결과는 흔들릴 수 있으므로, vote, IoU dedup, tracking, EMA smoothing을 거쳐 안내합니다.
- confidence를 그대로 말하지 않고, 거리, 화면 중앙성, 객체 종류를 조합한 `risk_score`로 사용자 피드백 강도를 결정합니다.
- 위험도는 TTS 문장뿐 아니라 SHORT, DOUBLE, URGENT 진동 패턴으로도 변환됩니다.
- 서버는 실시간 추론 서버가 아니라 탐지 JSON, GPS, 성능 로그를 저장하고 대시보드/SSE/히트맵으로 보여주는 기록 서버입니다.

### 9-6. 기술적으로 부족해 보이는 부분과 보완 방법

아래 항목은 “없는 걸 숨기기”보다 “측정 계획과 현재 코드 근거를 분리해서 보여주기”가 좋다.

| 부족해 보이는 부분 | 현재 코드 근거 | PPT 보완 방법 |
|---|---|---|
| 모델 정확도 그래프 없음 | YOLO 추론/후처리 코드는 있음 | mAP50은 미측정으로 두고, 실제 탐지 캡처 + 추후 평가 계획 표시 |
| Android 실기 FPS 수치 부족 | `VG_PERF` 로그, `calcFps()`, fps sparkline 있음 | 발표 전 1분 Logcat 측정 후 평균/최소/최대 표 추가 |
| TTS latency 미측정 | TTS/진동 호출 구조 있음 | `tts_latency_ms` 컬럼이 있으므로 측정 예정 항목으로 제시 |
| 거리 정확도 한계 | bbox 기반 `distanceM`, `depth_source=on_device_bbox` | “정확 거리”가 아니라 “보수적 근접도 추정”으로 설명 |
| 대시보드 성능 그래프 부족 | `performance_metrics`, `/history`, `/heatmap` 있음 | 서버 로그/DB 캡처를 막대그래프와 히트맵으로 시각화 |

### 9-7. 최종 PPT에 넣으면 좋은 기술 자료 체크리스트

- [ ] 앱 화면: bbox, class, FPS 표시가 보이는 캡처
- [ ] Logcat: `VG_PERF` 한 줄 캡처
- [ ] 코드: `TfliteYoloDetector.kt` 추론/후처리 8줄
- [ ] 코드: `MvpPipeline.kt` risk score 계산 10줄
- [ ] 표: risk_score -> 진동 패턴 매핑
- [ ] 그래프: 거리별 차량/일반 물체 risk 변화
- [ ] 그래프: 서버 요청 평균, NLG 생성 시간, 테스트 통과 개수
- [ ] 대시보드: 실시간 상태/SSE 또는 히트맵 캡처
- [ ] 주석: Android FPS, mAP50, TTS latency는 실측 전까지 “추가 측정 필요”로 표기
