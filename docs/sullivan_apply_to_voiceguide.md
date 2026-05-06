# 설리번 플러스에서 VoiceGuide에 적용할 수 있는 것들

> 설리번 플러스의 "사진 찍어서 분석" 기능과 UI를 VoiceGuide 관점에서 정리한 문서.  
> "이 기능을 어떻게 만들면 되는가"까지 구체적으로 설명함.

---

## 설리번 플러스가 사진을 어떻게 분석하는가

### 기본 흐름

```
사용자가 카메라를 들고 버튼을 탭
    ↓
AI가 사진을 분석 (클라우드로 전송)
    ↓
문자인식 / 얼굴인식 / 이미지묘사 중 가장 적합한 결과 선택
    ↓
음성으로 읽어줌
```

핵심은 사용자가 **모드를 고르지 않아도** AI가 알아서 적합한 분석을 선택한다는 점이다.
이것을 앱에서는 **"AI 모드"** 라고 부른다.

### 이미지 캡셔닝 방식

설리번은 사진에서 주요 키워드를 추출한 뒤 자연어 문장으로 조합한다.

```
사진 속 객체: [탁자, 펜]
위치 관계:   [탁자 위에 펜이 있음]
                ↓
출력 문장:   "탁자 위에 펜이 있습니다."
```

단순히 "탁자, 펜" 목록을 읽는 게 아니라 **위치 관계까지 포함한 문장**을 만들어준다.

### 개별 기능 목록

| 기능 | 동작 방식 |
|---|---|
| AI 모드 | 촬영 시 문자/얼굴/이미지 중 최적 자동 선택 |
| 문자 인식 | 카메라를 글자에 가져다 대면 진동 알림 후 읽어줌 |
| 이미지 묘사 | 전체 장면을 자연어 문장으로 설명 |
| 얼굴 인식 | 나이·성별·표정 추정, 등록 얼굴 찾기 |
| 색상 인식 | 중앙 색상 or 전체 화면 주요 색상 안내 |
| 빛 밝기 | 밝으면 높은 음, 어두우면 낮은 음으로 안내 |
| 물체 찾기 | 목록에서 찾을 물체 선택 → 방향 안내 |
| 돋보기 | 줌 + 색상 반전 |

---

## VoiceGuide와 비교 — 뭐가 다른가

| 항목 | 설리번 플러스 | VoiceGuide 현재 |
|---|---|---|
| 사진 분석 방식 | AI가 모드 자동 선택 | STT 음성으로 모드 선택 |
| 결과 문장 | "탁자 위에 펜이 있습니다" | "앞에 의자 있어요" (클래스 목록 기반) |
| 빛 밝기 안내 | 음 높낮이로 실시간 | 텍스트로만 |
| 문자 인식 | ✅ (메인 기능) | ❌ |
| 음성 명령 | "아리아, 문자 읽어줘" | "문자 찾아줘" (STT) |
| 진동 피드백 | 문자 감지 시 진동 | VibrationPattern 정의됨, HW 미연결 |
| UI | 기능별 큰 버튼 탭 선택 | 음성 명령 위주 |

---

## 적용할 수 있는 것들

---

### 1. AI 모드 컨셉 — 모드를 안 골라도 되는 "한 번 탭"

**설리번이 하는 것:**
버튼 하나로 AI가 상황에 맞는 분석을 알아서 선택한다.

**VoiceGuide에 적용하면:**

현재 VoiceGuide는 "장애물", "찾기", "질문", "신호등" 등 모드를 음성으로 먼저 말해야 한다.
설리번처럼 **화면을 한 번 탭하면 = 현재 상황에 가장 맞는 분석을 자동 실행**하도록 만들 수 있다.

```
화면 탭
    ↓
앞에 텍스트 많음  →  OCR 모드로 자동 전환
앞에 사람 있음    →  "앞에 사람이 있습니다" 안내
앞에 장애물 있음  →  거리 + 위험도 안내
```

**구현 방법:**
- 현재 `captureAndProcess()` 함수에 장면 분류 로직 추가
- YOLO 결과 기반으로 "텍스트 많음 / 사람 / 장애물" 구분
- 각 케이스에 맞는 안내 함수 호출

---

### 2. 이미지 묘사 — 클래스 목록 → 자연어 문장

**설리번이 하는 것:**
"탁자, 펜" → "탁자 위에 펜이 있습니다"

**VoiceGuide 현재:**
`SentenceBuilder`가 탐지 결과를 받아 문장을 만드는데, 현재는 위치 관계 없이 클래스 나열에 가깝다.

**VoiceGuide에 적용하면:**

탐지된 객체들의 방향(`direction`)과 거리(`distanceM`)를 조합해 더 자연스러운 문장을 만든다.

```kotlin
// 현재
"앞에 의자, 가방 있어요."

// 개선 후
"정면 1.5m에 의자가 있고, 오른쪽에 가방이 있어요."
```

`MvpPipeline`이 이미 `direction`과 `distanceM`을 계산하고 있으므로, `SentenceBuilder`에서 이 두 값을 활용해 위치 관계를 문장에 넣으면 된다.

**구현 포인트:**
```kotlin
// SentenceBuilder.kt 에서 활용할 수 있는 정보
detection.direction  // "12시", "3시", "9시" 등 클럭 방향
detection.distanceM  // 추정 거리 (미터)
detection.riskScore  // 위험도
```

---

### 3. 빛 밝기 — 소리 높낮이로 실시간 안내

**설리번이 하는 것:**
밝으면 높은 음, 어두우면 낮은 음을 지속 출력한다.
사용자가 카메라를 돌리기만 해도 어디가 밝은지 바로 알 수 있다.

**VoiceGuide 현재:**
"어두움 감지" 기능이 있지만 텍스트 기반으로만 안내한다.

**VoiceGuide에 적용하면:**
- 카메라 프레임의 평균 밝기(픽셀 luminance)를 실시간 계산
- 밝기에 따라 ToneGenerator 주파수를 바꿔서 비프음 출력

```kotlin
// 구현 개념
val brightness = calculateAverageBrightness(imageProxy)
val freq = (300 + brightness * 3).toInt()  // 300Hz(어둠) ~ 1070Hz(밝음)
toneGenerator.startTone(ToneGenerator.TONE_CDMA_PIP, 50)
```

이렇게 하면 사용자가 TTS를 기다리지 않고 **카메라를 돌리는 순간** 밝기를 인식할 수 있다.

---

### 4. 진동 피드백 — VibrationPattern을 실제로 연결

**설리번이 하는 것:**
- 글자 인식됨 → 짧은 진동
- 물체 찾기 성공 → 진동 패턴으로 알림

**VoiceGuide 현재:**
`MvpPipeline.kt`에 `VibrationPattern(NONE / SHORT / DOUBLE / URGENT)`이 정의되어 있지만 실제 Android 진동 출력이 연결되지 않은 상태다.

**연결 방법:**

```kotlin
// MainActivity.kt에 추가
private fun triggerVibration(pattern: VibrationPattern) {
    val vibrator = getSystemService(VIBRATOR_SERVICE) as Vibrator
    when (pattern) {
        VibrationPattern.SHORT  -> vibrator.vibrate(VibrationEffect.createOneShot(80, 180))
        VibrationPattern.DOUBLE -> vibrator.vibrate(VibrationEffect.createWaveform(
            longArrayOf(0, 80, 100, 80), -1))
        VibrationPattern.URGENT -> vibrator.vibrate(VibrationEffect.createWaveform(
            longArrayOf(0, 200, 100, 200, 100, 200), -1))
        VibrationPattern.NONE   -> {}
    }
}

// captureAndProcess() 결과 처리 부분에서 호출
val mvpFrame = mvpPipeline.update(voteOnly(removeDuplicates(rawDetections)))
triggerVibration(mvpFrame.vibrationPattern)  // ← 이 한 줄 추가
```

이 작업이 현재 VoiceGuide에서 **가장 빠르게 적용 가능하고 효과가 큰** 개선이다.

---

### 5. 색상 인식 — 모델 없이 픽셀만으로 구현

**설리번이 하는 것:**
화면 중앙 픽셀의 색상을 읽어 "파란색", "회녹색" 등으로 안내한다.

**VoiceGuide에 적용하면:**
"옷 매칭" 예정 기능과 연결 가능하다.

```kotlin
// 구현 개념 (YOLO 불필요, 순수 픽셀 분석)
fun getColorName(bitmap: Bitmap): String {
    val pixel = bitmap.getPixel(bitmap.width / 2, bitmap.height / 2)
    val r = Color.red(pixel)
    val g = Color.green(pixel)
    val b = Color.blue(pixel)
    // HSV 변환 후 색상 이름 매핑
    val hsv = FloatArray(3)
    Color.RGBToHSV(r, g, b, hsv)
    return when {
        hsv[1] < 0.15f -> if (hsv[2] > 0.8f) "흰색" else if (hsv[2] < 0.2f) "검정" else "회색"
        hsv[0] < 30f   -> "빨간색"
        hsv[0] < 60f   -> "주황색"
        hsv[0] < 90f   -> "노란색"
        hsv[0] < 150f  -> "초록색"
        hsv[0] < 210f  -> "청록색"
        hsv[0] < 270f  -> "파란색"
        hsv[0] < 330f  -> "보라색"
        else           -> "분홍색"
    }
}
```

별도 모델 없이 픽셀 분석만으로 즉시 구현 가능하다.

---

## UI에서 참고할 것들

---

### UI 원칙 1 — 전체 화면이 탭 영역

설리번 플러스는 화면 어디를 눌러도 분석이 시작된다.
시각장애인은 버튼의 정확한 위치를 찾기 어렵기 때문에 **화면 전체가 하나의 큰 버튼**처럼 동작하는 게 맞다.

**VoiceGuide 적용:**

```kotlin
// MainActivity.kt — 카메라 프리뷰 뷰에 터치 리스너 추가
previewView.setOnClickListener {
    if (isAnalyzing.get()) captureAndProcess()
}
```

---

### UI 원칙 2 — 결과 텍스트를 크게

설리번은 분석 결과를 화면에 크게 표시한다. 저시력자(완전 실명이 아닌 사용자)를 위해서다.
VoiceGuide의 `tvStatus`가 이 역할을 할 수 있지만 현재 폰트 크기가 작다.

**적용 방향:**
- 결과 문장을 `tvStatus`에 표시할 때 폰트 크기 24sp 이상
- 텍스트 색상: 흰색 + 반투명 검정 배경 (카메라 프리뷰 위에 오버레이)
- 화면 하단이 아닌 중앙 or 상단에 배치 (손으로 가려지지 않게)

---

### UI 원칙 3 — 길게 누르면 이전 결과 다시 읽기

설리번은 결과 화면에 "다시 읽기" 버튼이 있다.
VoiceGuide에는 "다시읽기" STT 명령이 있지만, 음성을 인식하기 전에 소리를 못 들은 경우에는 쓰기 어렵다.

**적용 방향:**
- 화면을 **길게 누르면** = `speak(lastSentence)` 호출

```kotlin
previewView.setOnLongClickListener {
    if (lastSentence.isNotEmpty()) speak(lastSentence)
    true
}
```

---

### UI 원칙 4 — 기능 진입을 스와이프로

설리번은 화면을 좌우로 스와이프해 모드를 전환한다.
STT가 안 되는 조용한 환경(도서관, 병원)에서도 조작 가능하다.

**VoiceGuide 적용:**

```kotlin
// GestureDetector로 스와이프 감지
val gestureDetector = GestureDetectorCompat(this, object : GestureDetector.SimpleOnGestureListener() {
    override fun onFling(e1: MotionEvent?, e2: MotionEvent, vX: Float, vY: Float): Boolean {
        if (e1 == null) return false
        val diffX = e2.x - e1.x
        if (diffX > 200) handleCommand("다시읽기", "")        // 오른쪽 스와이프
        if (diffX < -200) handleCommand("찾기", "")           // 왼쪽 스와이프
        return true
    }
})
```

---

## 우선순위 정리

| 순위 | 항목 | 설리번 어느 기능 참고 | 난이도 | 예상 작업량 |
|---|---|---|---|---|
| ★★★ | 진동 실제 연결 | 진동 피드백 | 낮음 | 20줄 이내 |
| ★★★ | 화면 탭 → 즉시 분석 | 전체 화면 탭 원칙 | 낮음 | 5줄 |
| ★★★ | 길게 누르면 다시 읽기 | 다시 읽기 버튼 | 낮음 | 5줄 |
| ★★ | 문장에 위치 관계 추가 | 이미지 묘사 방식 | 보통 | SentenceBuilder 수정 |
| ★★ | 색상 인식 | 색상인식 기능 | 보통 | 픽셀 분석 함수 작성 |
| ★ | 빛 밝기 소리 안내 | 빛 밝기 기능 | 보통 | ToneGenerator 연동 |
| ★ | 스와이프 모드 전환 | 스와이프 네비게이션 | 보통 | GestureDetector 추가 |
| ★ | 결과 텍스트 크게 | 결과 표시 UI | 낮음 | XML 수정 |

---

## 핵심 요약

설리번 플러스에서 VoiceGuide가 바로 가져올 수 있는 핵심은 두 가지다.

1. **"모드 안 골라도 되는 한 번 탭"** — AI가 알아서 상황에 맞는 분석을 선택
2. **"소리와 진동으로 텍스트 없이도 상태 전달"** — TTS 기다리지 않아도 진동·음 높낮이로 즉시 피드백

이 두 가지 원칙이 설리번이 실제 시각장애인에게 유용하게 쓰이는 가장 큰 이유다.
