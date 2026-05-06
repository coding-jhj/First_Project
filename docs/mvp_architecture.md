# VoiceGuide MVP 기술 설계 문서

> 시각장애인(보호자 없는 단독 사용자)을 위한 모바일 온디바이스 MVP 아키텍처 정의

---

## 1. MVP 파이프라인 구조

```
YOLO11n 탐지
    ↓
BBox Tracking
    ↓
FastDepth 거리 추정
    ↓
위험도 계산
    ↓
진동패턴 출력
```

YOLO11n + BBox + FastDepth + BBox Tracking + 진동패턴 조합이 모바일 시각장애인용 MVP로 현실적인 구조다.

---

## 2. 설계 원칙 — 보호자 없는 시각장애인 대상

**단순히 "앞에 객체 있음"을 알리는 것 이상이 필요하다.**

| 요구사항 | 설명 |
|---|---|
| 놓치면 안 됨 | 실제 위험 객체를 단 한 번도 놓쳐서는 안 됨 |
| 오경고 최소화 | 오경고가 많으면 사용자가 신뢰를 잃고 앱을 끔 |
| 진동 명확성 | 패턴이 헷갈리면 위험 수준을 구분 못 함 |
| 오프라인 동작 | 네트워크 없이도 긴급 위험 알림이 가능해야 함 |

**MVP 안전 조건 (필수):**

> **서버 없이도 로컬에서 긴급 진동이 즉시 가능해야 한다.**

위험 판단과 진동은 모바일 로컬에서 처리한다. 서버 JSON 전송은 로그/분석/보조 용도로만 사용한다.

---

## 3. 역할 분리 — 모바일 vs 서버

```
모바일 (로컬 처리)
├── 카메라 추론
├── YOLO + Tracking + Depth
├── 위험도 계산
├── 진동 즉시 출력
└── JSON SSOT 생성

서버 (비동기 후처리)
├── 로그 저장
├── 성능 분석
├── 보호자 대시보드
└── 모델 개선용 데이터 수집
```

**핵심 원칙:**

| 역할 | 담당 |
|---|---|
| 긴급 경고 | 모바일 로컬 (네트워크 무관) |
| 기록 / 분석 / 모니터링 | 서버 전송 |

서버를 "실시간 경고 판단" 경로에 끼우면 네트워크 지연이 생명 안전에 직결되는 위험이 생긴다.

---

## 4. 진동 패턴 규칙

핵심: **진동을 너무 자주 울리면 사용자가 피로해져 앱을 끈다.**

| 위험도 | 거리 / 조건 | 진동 패턴 |
|---|---|---|
| 낮음 | 2.5~4m 전방 객체 | 짧게 1번 |
| 중간 | 1.5~2.5m, 중앙 근처 | 짧게 2번 |
| 높음 | 1~1.5m, 접근 중 | 빠르게 3번 |
| 긴급 | 1m 이하 | 길고 강하게 반복 |

### 현재 구현 (`MvpPipeline.kt` 기준)

```kotlin
enum class VibrationPattern { NONE, SHORT, DOUBLE, URGENT }

// 위험도 → 패턴 매핑
risk >= 0.75f → URGENT   // 길고 강하게
risk >= 0.55f → DOUBLE   // 짧게 2번
risk >= 0.35f → SHORT    // 짧게 1번
else          → NONE
```

차량 클래스(`vehicleKo`)는 risk >= 0.55f부터 즉시 URGENT로 상향된다.

---

## 5. 위험도 계산 로직

```kotlin
risk = centerWeight × distanceWeight × classWeight + sizeBoost
```

| 요소 | 설명 |
|---|---|
| `centerWeight` | 화면 중앙에 가까울수록 높음 (cx 기준) |
| `distanceWeight` | 거리가 가까울수록 높음 (0.8m 이하 = 1.0) |
| `classWeight` | 차량·위험 클래스 가중치 높음 (차량 = 1.0) |
| `sizeBoost` | bbox 면적이 클수록 추가 가산 |

거리는 bbox 면적 기반으로 추정한다:

```kotlin
distanceM = sqrt(BBOX_CALIB_AREA / area)   // BBOX_CALIB_AREA = 0.06f
```

---

## 6. BBox Tracking (MvpPipeline)

프레임 간 동일 객체를 추적해 위험도를 EMA로 안정화한다.

| 파라미터 | 값 | 설명 |
|---|---|---|
| `IOU_MATCH_THRESHOLD` | 0.25 | 동일 트랙으로 판정하는 최소 IoU |
| `MAX_MISSED_FRAMES` | 12 | 이 프레임 수 이상 미탐지 시 트랙 삭제 |
| `EMA_ALPHA` | 0.55 | 현재 55% + 이전 45% — 흔들림 vs 반응 균형 |

EMA 적용 대상: `cx`, `cy`, `w`, `h`, `distanceM`, `riskScore`

---

## 7. 오탐 방지 — 보팅(Voting)

Android 온디바이스에서 1차 보팅 후 서버 전송. 서버는 필터링 없이 EMA만 적용한다.

```
rawDetections
    → removeDuplicates()   // IoU 0.3 이상 중복 bbox 제거
    → voteOnly()           // WINDOW=3 중 2회 이상 = 확정
    → MvpPipeline.update() // 트래킹 + EMA + 위험도 계산
```

`voteBypassKo` 목록(계단, 차량 등)은 보팅 없이 즉시 통과한다.

---

## 8. 구현 현황

| 항목 | 상태 | 파일 |
|---|---|---|
| YOLO11n 온디바이스 추론 | ✅ 완료 | `YoloDetector.kt` |
| BBox Tracking + EMA | ✅ 완료 | `MvpPipeline.kt` |
| 위험도 계산 | ✅ 완료 | `MvpPipeline.kt` |
| 진동 패턴 정의 | ✅ 완료 | `MvpPipeline.kt` |
| 보팅 스레드 안전성 | ✅ 완료 | `MainActivity.kt` |
| JSON SSOT 서버 전송 | ✅ 완료 | `routes.py /detect_json` |
| 서버 추론 비활성화 | ✅ 완료 | `/detect` → 410 반환 |
| FastDepth 교체 | ⬜ 미완료 | 현재 bbox 면적 기반 추정 사용 중 |
| 진동 실제 출력 연동 | ⬜ 미완료 | VibrationPattern 계산만, HW 출력 미구현 |
