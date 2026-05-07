# 핸드폰·책·마우스 탐지 안 되는 문제 해결 방법

코드에서 직접 수정할 수 있는 것들만 정리합니다.  
수정 순서대로 하나씩 해보고 결과를 확인하는 걸 권장합니다.

---

## 수정 1 — confThreshold 낮추기 (가장 효과 큼)

**파일:** `android/app/src/main/java/com/voiceguide/TfliteYoloDetector.kt` **25번째 줄**

```kotlin
// 현재
private val confThreshold = 0.40f

// 수정
private val confThreshold = 0.25f
```

**왜:** 0.40 미만이면 탐지 결과를 전부 버립니다. nano 모델은 작은 물체(마우스, 책, 핸드폰)를  
0.40 이상으로 확신하기 어렵습니다. 0.25로 낮추면 더 많이 잡힙니다.

**부작용:** 없는 물체를 있다고 할 수 있습니다(오탐지 증가). 0.25가 너무 많으면 0.30으로 조정하세요.

---

## 수정 2 — 노트북(63번) COCO_KO에 추가

**파일:** `android/app/src/main/java/com/voiceguide/VoiceGuideConstants.kt` **21~22번째 줄**

```kotlin
// 현재
   60 to "테이블",   61 to "변기",   62 to "티비",
   64 to "마우스",   65 to "리모컨", 66 to "키보드",  67 to "휴대폰",

// 수정 (63 추가)
   60 to "테이블",   61 to "변기",   62 to "티비",   63 to "노트북",
   64 to "마우스",   65 to "리모컨", 66 to "키보드",  67 to "휴대폰",
```

그리고 **4번째 줄 주석도 수정:**

```kotlin
// 현재
// 제외: 63(노트북 — 이미 포함), 72(냉장고), 77(인형 — 휴대폰 오인식 빈번), 80(계단 — 인식률 낮음)

// 수정
// 제외: 72(냉장고), 77(인형 — 휴대폰 오인식 빈번)
```

**왜:** 63번(노트북)은 주석에 "이미 포함"이라고 적혀 있지만 실제로는 맵에 없습니다.  
모델이 노트북을 탐지해도 코드에서 null로 처리되어 버려지고 있었습니다.

---

## 수정 3 — 최대 탐지 개수 늘리기

**파일:** `android/app/src/main/java/com/voiceguide/TfliteYoloDetector.kt` **388번째 줄**

```kotlin
// 현재 (postProcessRaw 함수 끝)
return nms(candidates.sortedByDescending { it.confidence }).take(8)

// 수정
return nms(candidates.sortedByDescending { it.confidence }).take(15)
```

**같은 파일 420번째 줄** (postProcessEndToEnd 함수 끝도 동일하게):

```kotlin
// 현재
return nms(candidates.sortedByDescending { it.confidence }).take(8)

// 수정
return nms(candidates.sortedByDescending { it.confidence }).take(15)
```

**왜:** 현재 신뢰도 상위 8개만 남깁니다. 사람·자동차 등이 먼저 8개를 채우면  
마우스·책은 목록에서 잘립니다. 15개로 늘리면 더 많은 물체가 포함됩니다.

---

## 수정 순서 권장

```
1단계: 수정 2(노트북 추가) → 빌드 → 노트북 탐지 확인
2단계: 수정 1(threshold 0.25) → 빌드 → 핸드폰·마우스 탐지 확인
3단계: 오탐지가 많으면 0.25 → 0.30으로 조정
4단계: 수정 3(take 15) → 빌드 → 여러 물체 동시 탐지 확인
```

---

## 수정 후 Logcat 확인 방법

Android Studio Logcat에서 `VG_DETECT` 태그 필터:

```
VG_DETECT: [0] 휴대폰 | conf=0.31 | cx=0.52 ...
VG_DETECT: [1] 마우스 | conf=0.27 | cx=0.38 ...
```

conf 값이 이전에 0.40 이하라 잘렸던 것들이 나오면 성공입니다.
