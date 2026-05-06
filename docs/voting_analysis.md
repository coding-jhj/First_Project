# 보팅(Voting) 분석 리포트

> 코드 수정 없이 분석만 한 결과. 수정이 필요한 것들의 우선순위와 이유를 정리함.

---

## 보팅이 두 곳에 구현되어 있음

현재 보팅 로직이 **Android 앱**과 **서버** 각각에 독립적으로 존재함.

### Android — `voteOnly()` ([MainActivity.kt:110](MainActivity.kt#L110))

| 항목 | 값 |
|---|---|
| 윈도우 크기 | 3프레임 |
| 통과 기준 | 3프레임 중 2회 이상 등장 |
| bypass 처리 | `voteBypassKo` 목록(계단, 차량 등)은 보팅 없이 즉시 통과 |

### 서버 — `VotingBuffer` ([tracker.py:39](src/api/tracker.py#L39))

| 항목 | 값 |
|---|---|
| 윈도우 크기 | 10프레임 |
| 통과 기준 | 10프레임 중 60%(6회) 이상 등장 |
| bypass 처리 | 차량(`is_vehicle=True`)은 즉시 통과 |

---

## 새 아키텍처에서의 전체 흐름

```
폰 YOLO 추론
    │
    ▼
voteOnly()           ← 1차 보팅 (WINDOW=3, 2/3 통과)
    │
    ▼
removeDuplicates()
    │
    ├──── TTS 발화 (폰 즉시)
    │
    └──── sendDetectionsJson() → 서버
                                    │
                                    ▼
                              tracker.update()
                                    │
                                    ▼
                              VotingBuffer.filter()  ← 2차 보팅 (WINDOW=10, 6/10 통과)
```

---

## 발견한 문제들

### 🔴 문제 1 — 스레드 안전성 버그 (심각)

**위치**: [MainActivity.kt:102](MainActivity.kt#L102)

`detectionHistory`는 동기화되지 않은 일반 `ArrayDeque`인데,
`MAX_ON_DEVICE_IN_FLIGHT = 3`이라 최대 3개 스레드가 동시에 `voteOnly()`를 실행할 수 있음.

```
스레드 A: detectionHistory.addLast(...)      ← 동시에 실행
스레드 B: detectionHistory.addLast(...)      ← 충돌 가능
스레드 C: for (frame in detectionHistory)    ← 순회 중 수정 → 예외 발생 가능
```

실제로 터지면 앱이 조용히 잘못된 보팅 결과를 내거나
Logcat에 `ConcurrentModificationException`이 찍힘.

**고칠 방법**: `ArrayDeque` → `@Synchronized` 처리 또는 `java.util.Collections.synchronizedList()` 사용

---

### 🔴 문제 2 — 이중 보팅 (심각, 새 아키텍처 한정)

폰에서 이미 1차 보팅을 통과한 결과만 서버로 보냄.
서버 `VotingBuffer`는 이미 걸러진 것들을 또 한 번 거름.

**결과**: 서버 보팅 `WINDOW=10`을 채우려면 10번의 JSON 전송이 쌓여야 확정됨.
→ 최소 `10 × INTERVAL(50ms) = 500ms` 추가 지연 발생.

처음 보내는 9번의 JSON은 서버 보팅을 통과 못 할 수도 있음.

**고칠 방법**: 서버 `VotingBuffer.filter()`를 제거하거나 차량 bypass만 남기고 필터 기능은 비활성화

---

### 🟡 문제 3 — `voteOnly` 실행 순서가 비효율적 (중간)

**현재 순서**:
```
rawDetections → voteOnly() → removeDuplicates() → voted
```

YOLO가 같은 의자를 2개의 bbox로 잡았을 때(`removeDuplicates`로 제거될 중복),
보팅 단계에서는 둘 다 카운트에 포함됨.

결과에는 큰 영향이 없지만 논리적으로 아래 순서가 더 맞음:
```
rawDetections → removeDuplicates() → voteOnly() → voted
```

---

### 🟡 문제 4 — 모드 전환 시 history가 안 지워짐 (중간)

`detectionHistory.clear()`는 `startAnalysis()`([MainActivity.kt:976](MainActivity.kt#L976))에서만 호출됨.

STT로 모드를 "장애물" → "찾기"로 전환할 때 이전 장애물 탐지 history가 그대로 남음.
→ 찾기 모드의 첫 1~2프레임 보팅 결과가 이전 모드의 데이터에 영향을 받음.

**고칠 방법**: 모드 변경 시 `detectionHistory.clear()` 호출 추가

---

### 🟡 문제 5 — 서버 초기 3프레임 무조건 통과 (중간)

**위치**: [tracker.py:61](src/api/tracker.py#L61)

```python
def is_confirmed(self, cls: str) -> bool:
    if len(self._frames) < 3:
        return True  # 초기 3프레임은 필터링 없이 통과
```

서버 재시작 직후 첫 3개의 JSON 요청에서는 보팅 없이 모든 물체가 통과됨.
→ 재시작 후 오탐이 그대로 나갈 수 있음.

의도적인 설계지만, 재시작 직후 오탐 가능성을 인지하고 있어야 함.

---

### ⚪ 문제 6 — 주석 오류 (경미)

**위치**: [MainActivity.kt:100](MainActivity.kt#L100)

```kotlin
// 최근 5프레임 탐지 결과를 기록해 3회 이상 등장한 사물만 안내
```

실제 코드:
```kotlin
private val VOTE_WINDOW    = 3   // 5가 아님
private val VOTE_MIN_COUNT = 2   // 3회가 아님
```

---

## 결론 요약

| 항목 | Android 보팅 | 서버 보팅 |
|---|---|---|
| 로직 자체 | 올바름 | 올바름 (단독 실행 시) |
| 새 아키텍처에서 역할 | ✅ 핵심 (유일한 실질 보팅) | ⚠️ 이중 보팅 — 오히려 방해 |
| 스레드 안전 | ❌ 비동기화 ArrayDeque | ✅ 문제없음 |
| bypass 처리 | ✅ voteBypassKo | ✅ is_vehicle |

**수정 우선순위**:

| 순서 | 항목 | 난이도 |
|---|---|---|
| 1 | Android `detectionHistory` 스레드 안전성 확보 | 낮음 |
| 2 | 서버 `VotingBuffer.filter()` 제거 또는 bypass only로 축소 | 낮음 |
| 3 | `voteOnly` 호출 순서 변경 (removeDuplicates 먼저) | 낮음 |
| 4 | 모드 전환 시 `detectionHistory.clear()` 추가 | 낮음 |
| 5 | 주석 수정 | 매우 낮음 |
