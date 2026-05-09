# VoiceGuide MVP 기술 설계 문서

> 시각장애인(보호자 없는 단독 사용자)을 위한 모바일 온디바이스 MVP 아키텍처 정의  
> 최종 업데이트: 2026-05-08 (실제 코드 기준)

---

## 1. MVP 파이프라인 구조

```
YOLO11n 탐지
    ↓
보팅 필터 (오탐 억제)
    ↓
BBox Tracking (IoU 매칭)
    ↓
EMA 평활화 (흔들림 제거)
    ↓
위험도 계산
    ↓
EventType 판단 (SUDDEN / GRADUAL)
    ↓
shouldSpeak 결정
    ↓
VibrationPattern 출력
```

YOLO11n + BBox Tracking + EMA + EventType 기반 발화 제어 + 진동 패턴 조합이 현재 구현된 MVP 구조다.

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

위험 판단과 진동은 모바일 로컬에서 처리한다. 서버 전송은 NLG 문장 수신·로그·대시보드 용도로 사용한다.

---

## 3. 역할 분리 — 모바일 vs 서버

```
모바일 (로컬 처리)
├── 카메라 추론 (YOLO11n)
├── 보팅 필터
├── BBox Tracking + EMA
├── 위험도 계산
├── EventType 판단
├── 진동 즉시 출력        ← 긴급 경고 경로 (오프라인 가능)
└── POST /detect (JSON 전송)

서버 (동기 후처리)
├── Tracker EMA 평활화 (서버 측)
├── NLG 안내 문장 생성 → Android TTS 발화
├── DB 저장
├── 대시보드 SSE 배포
└── 보호자 모니터링용 데이터 수집
```

**핵심 원칙:**

| 역할 | 담당 |
|---|---|
| 긴급 경고 (진동) | 모바일 로컬 (네트워크 무관) |
| NLG 문장 생성 | 서버 (응답 받아 Android TTS 발화) |
| 기록 / 분석 / 모니터링 | 서버 |

서버를 거치면 네트워크 지연이 생기므로 진동은 모바일에서 먼저 출력하고, 음성 안내는 서버 응답을 받아 TTS로 발화한다.

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

차량 클래스(`vehicleKo`)는 `risk >= 0.55f`부터 즉시 URGENT로 상향된다.

---

## 5. EventType — 발화 제어

`SUDDEN` / `GRADUAL` 두 가지 이벤트 타입으로 발화 여부를 결정한다.

| EventType | 조건 | 동작 |
|---|---|---|
| SUDDEN | 측면 등장 (cx < 0.33 or cx > 0.67) | 진동만, 발화 없음 |
| SUDDEN | 신규 트랙이 2m 이내로 등장 | 진동만, 발화 없음 |
| SUDDEN | 이전 프레임 대비 0.8m 이상 급접근 | 진동만, 발화 없음 |
| GRADUAL | 그 외 일반 전방 물체 | 5초 쿨다운 후 발화 |

**shouldSpeak 최종 규칙:**

```kotlin
if (pattern == VibrationPattern.URGENT) → 항상 발화 (쿨다운 무시)
if (eventType == SUDDEN)               → 진동만, 발화 없음
if (eventType == GRADUAL)              → 마지막 발화로부터 5초 경과 시 발화
```

파라미터:

| 상수 | 값 |
|---|---|
| `SIDE_LEFT_THRESHOLD` | 0.33 |
| `SIDE_RIGHT_THRESHOLD` | 0.67 |
| `NEW_TRACK_SUDDEN_DIST_M` | 2.0m |
| `FAST_APPROACH_DELTA_M` | 0.8m/frame |
| `SPEAK_COOLDOWN_MS` | 5000ms |

---

## 6. 위험도 계산 로직

```kotlin
risk = centerWeight × distanceWeight × classWeight + sizeBoost
```

| 요소 | 설명 |
|---|---|
| `centerWeight` | `1 - min(0.6, abs(cx - 0.5) × 1.2)` — 중앙에 가까울수록 높음 |
| `distanceWeight` | 거리 구간별 고정값 (아래 표) |
| `classWeight` | 클래스 위험도별 가중치 (아래 표) |
| `sizeBoost` | `min(0.25, area × 1.8)` — bbox 면적 클수록 가산 |

**distanceWeight:**

| 거리 | 가중치 |
|---|---|
| ≤ 0.8m | 1.0 |
| ≤ 1.5m | 0.85 |
| ≤ 2.5m | 0.65 |
| ≤ 4.0m | 0.35 |
| > 4.0m | 0.15 |

**classWeight:**

| 클래스 그룹 | 가중치 |
|---|---|
| `vehicleKo` (차량) | 1.0 |
| `criticalKo` (위험) | 0.9 |
| `animalKo` (동물) | 0.85 |
| `cautionKo` (주의) | 0.65 |
| 그 외 | 0.45 |

---

## 7. 거리 추정

거리는 bbox 면적 + 클래스별 보정 계수(`policy.json`)로 추정한다.

```kotlin
distanceM = sqrt(bboxCalibAreaByClass[classKo] ?: bboxCalibArea) / area
```

- `bboxCalibArea`: 기본 보정 계수 (`policy.json → on_device.bbox_calib_area`)
- `bboxCalibAreaByClass`: 클래스별 개별 보정 계수 (`policy.json → on_device.bbox_calib_area_by_class`)
- 클래스별 계수가 있으면 우선 적용, 없으면 기본값 사용

FastDepth 교체는 미완료 상태이며, 현재 이 bbox 면적 기반 추정을 사용한다.

---

## 8. BBox Tracking (MvpPipeline)

프레임 간 동일 객체를 추적해 위험도를 EMA로 안정화한다.

| 파라미터 | 값 | 설명 |
|---|---|---|
| `IOU_MATCH_THRESHOLD` | 0.25 | 동일 트랙으로 판정하는 최소 IoU |
| `MAX_MISSED_FRAMES` | 12 | 이 프레임 수 이상 미탐지 시 트랙 삭제 |
| `EMA_ALPHA` | 0.55 | 현재 55% + 이전 45% — 흔들림 vs 반응 균형 |

EMA 적용 대상: `cx`, `cy`, `w`, `h`, `distanceM`, `riskScore`

---

## 9. 오탐 방지 — 보팅(Voting)

Android 온디바이스에서 1차 보팅 후 서버 전송.

```
rawDetections
    → removeDuplicates()   // IoU 0.3 이상 중복 bbox 제거
    → voteOnly()           // WINDOW=3 중 2회 이상 = 확정
    → MvpPipeline.update() // 트래킹 + EMA + 위험도 계산
```

`voteBypassKo` 목록(계단, 차량 등)은 보팅 없이 즉시 통과한다.

---

## 10. 구현 현황

| 항목 | 상태 | 파일 |
|---|---|---|
| YOLO11n 온디바이스 추론 | ✅ 완료 | `YoloDetector.kt` |
| BBox Tracking + EMA | ✅ 완료 | `MvpPipeline.kt` |
| 위험도 계산 (4단계 classWeight) | ✅ 완료 | `MvpPipeline.kt` |
| 진동 패턴 정의 | ✅ 완료 | `MvpPipeline.kt` |
| EventType (SUDDEN/GRADUAL) | ✅ 완료 | `MvpPipeline.kt` |
| 발화 쿨다운 (5초, URGENT 예외) | ✅ 완료 | `MvpPipeline.kt` |
| 클래스별 거리 보정 (bboxCalibAreaByClass) | ✅ 완료 | `VoicePolicy.kt` |
| 보팅 스레드 안전성 | ✅ 완료 | `MainActivity.kt` |
| JSON 서버 전송 (`/detect`) | ✅ 완료 | `routes.py` |
| 서버 EMA + NLG 문장 반환 | ✅ 완료 | `routes.py`, `tracker.py` |
| FastDepth 교체 | ⬜ 미완료 | 현재 bbox 면적 기반 추정 사용 중 |
| 진동 실제 출력 연동 | ⬜ 미완료 | VibrationPattern 계산만, HW 출력 미구현 |
