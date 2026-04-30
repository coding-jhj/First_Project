import speech_recognition as sr

# ── 모드별 키워드 정제 (중복 제거 및 명확화) ──────────────────────────────────
KEYWORDS: dict[str, list[str]] = {
    # 찾기 모드: 목적어가 명확한 경우 우선 순위
    "찾기": [
        "찾아줘", "어디있어", "어디 있어", "위치 알려줘", "찾아", "어디야"
    ],
    # 확인 모드: 정면 물체 물어보기
    "확인": [
        "이거 뭐야", "이게 뭐야", "뭔지 알려줘", "이거 뭐지"
    ],
    # 저장/위치목록
    "저장": ["여기 저장", "저장해줘", "위치 등록"],
    "위치목록": ["저장된 곳", "장소 목록", "등록된 곳"],
    
    # 장애물 모드: 분석 명령어가 명확할 때만 실행
    "장애물": [
        "앞에 뭐 있어", "주변 알려줘", "분석해줘", "살펴봐줘", "길 어때"
    ],
}

# 기본값을 unknown으로 변경하여 비명령어 발화 시 분석 방지
_DEFAULT_MODE = "unknown"

def _classify(text: str) -> str:
    """
    텍스트 분석 후 모드 결정. 
    사용자의 발화가 어떤 키워드와도 매칭되지 않으면 unknown 반환.
    """
    if not text.strip():
        return "unknown"

    # 우선순위: 찾기 -> 확인 -> 저장 -> 위치목록 -> 장애물
    for mode in ["찾기", "확인", "저장", "위치목록", "장애물"]:
        if any(kw in text for kw in KEYWORDS[mode]):
            return mode
            
    return _DEFAULT_MODE


def listen_and_classify() -> tuple[str, str]:
    r = sr.Recognizer()
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=5)
            text = r.recognize_google(audio, language="ko-KR")
            
            # 짧은 발화 (2자 미만)은 명령어로 간주하지 않음
            if len(text.replace(" ", "")) < 2:
                return text, "unknown"
                
            mode = _classify(text)
            return text, mode
            
        except (sr.UnknownValueError, sr.WaitTimeoutError):
            # 미인식 시 "다시 말씀해 주세요" 유도 (또는 무음)
            return "", "unknown"
        except sr.RequestError:
            return "", "network_error"