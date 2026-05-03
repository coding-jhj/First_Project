"""
VoiceGuide 한국어 문장 생성 모듈
==================================
탐지된 물체 정보를 받아 시각장애인이 바로 이해할 수 있는
한국어 음성 안내 문장을 만듭니다.

설계 원칙:
  1. 짧고 명확하게 — TTS 재생 시간을 최소화해야 즉각 반응 가능
  2. 행동 중심 — "의자가 있어요" 가 아니라 "피해가세요" 까지 포함
  3. 긴박도 차등 — 가까울수록 짧고 강하게, 멀수록 부드럽게
  4. 물체 특성 반영 — 차량·동물은 이동 물체라 별도 처리
  5. 상대 표현 — 카메라로 정확한 거리 측정 불가, 수치 대신 "가까이" 등 사용

routes.py에서 호출되는 공개 함수:
  build_sentence()         — 장애물/확인 모드
  build_hazard_sentence()  — 계단·낙차 최우선 안내
  build_find_sentence()    — 찾기 모드
"""

from src.nlg.templates import (
    CLOCK_ACTION, CLOCK_TO_DIRECTION, get_absolute_clock
)

# 이동 차량: 같은 거리라도 정적 의자보다 훨씬 위험 → 8m 이내부터 긴급 경고
_VEHICLE_KO = {"자동차", "오토바이", "트럭", "기차", "자전거"}

# 동물: 돌발 행동 가능 → 일반 장애물보다 주의 어조
_ANIMAL_KO  = {"개", "말", "고양이"}

# 긴급(critical) 물체 — 빨간 바운딩박스와 동일 기준
_CRITICAL_KO = {"자동차", "오토바이", "트럭", "기차", "자전거",
                "곰", "코끼리", "계단"}

# 주의(caution) 물체 — 노란 바운딩박스와 동일 기준
_CAUTION_KO = {"칼", "가위", "유리잔", "야구 방망이",
               "배낭", "핸드백", "여행가방", "공"}

# 생활 물체: 크게 보여도(거리 가까워도) "위험!" 금지
# 이유: "위험! 바로 앞에 키보드가 있어요!"는 진짜 위험(자동차·계단)과 혼동돼
#       경고 피로(alert fatigue)를 높이고 신뢰도를 낮춤.
# SentenceBuilder.kt의 EVERYDAY_CLASSES와 동일 목록을 유지해야
# 서버↔온디바이스 전환 시 표현 정책이 일관됨.
_EVERYDAY_KO = {
    # 가구·침구
    "의자", "소파", "침대", "테이블", "벤치", "화분",
    # IT기기·가전
    "키보드", "마우스", "노트북", "TV", "리모컨",
    # 소품
    "책", "시계", "꽃병", "인형", "우산", "넥타이",
    # 식기
    "숟가락", "포크", "그릇", "컵", "병", "유리잔",
    # 음식
    "바나나", "사과", "샌드위치", "오렌지", "핫도그", "피자", "도넛", "케이크",
    # 주방·욕실 가전
    "전자레인지", "오븐", "토스터기", "세면대", "냉장고", "칫솔", "드라이기",
}


# ── 경고 피로(alert fatigue) 방지 ─────────────────────────────────────────────
# 매 프레임마다 TTS를 읽어주면 사용자가 경고에 둔감해지는 문제가 있었음.
# critical/beep/silent 3단계로 나눠 불필요한 음성 안내를 줄인다.

def get_alert_mode(obj: dict, is_hazard: bool = False) -> str:
    """탐지 객체 하나의 알림 모드 반환.

    Returns:
        "critical" — 즉각 TTS 음성 경고
        "beep"     — 비프음만, 음성 없음
        "silent"   — 무음 (사용자가 명시적으로 물어볼 때만 안내)
    """
    dist_m     = obj.get("distance_m", 99.0)
    is_vehicle = obj.get("is_vehicle", False)
    is_animal  = obj.get("is_animal",  False)

    if is_hazard:                          # 계단·낙차 — 낙상 위험이므로 거리 무관 경고
        return "critical"
    if is_vehicle and dist_m < 8.0:        # 차량 — 이동 속도 때문에 여유 거리 넉넉히
        return "critical"
    if is_animal and dist_m < 3.0:         # 동물 — 돌발 행동 위험
        return "critical"
    if dist_m < 2.5:                       # 2.5m 이내 — 음성 안내
        return "critical"
    if dist_m < 7.0:                       # 2.5~7m — 비프음만 (존재 인지, 음성 피로 방지)
        return "beep"
    return "silent"


# ── 한국어 조사 자동화 ────────────────────────────────────────────────────────

# 영문 알파벳 발음 기준 받침 없는 글자 (B=비, C=씨, D=디, E=이, T=티, V=브이 등)
_ENG_NO_BATCHIM = set('BCDEGHIJKOPQTUVWYZbcdeghijkopqtuvwyz')

def _josa(word: str, 받침있음: str, 받침없음: str) -> str:
    """
    한국어 받침 유무에 따라 올바른 조사를 반환하는 핵심 함수.

    원리:
      한국어: (글자코드 - 0xAC00) % 28 == 0 이면 받침 없음
      영문자: 발음 기준 — B(비)/C(씨)/D(디)/T(티)/V(브이) 등은 받침 없음
                         F(에프)/L(엘)/M(엠)/N(엔)/S(에스)/X(엑스) 등은 받침 있음
    예시:
      "TV"  → 마지막 V → 받침없음 → "TV가"
      "PC"  → 마지막 C → 받침없음 → "PC가"
      "USB" → 마지막 B → 받침없음 → "USB가"
    """
    if not word:
        return 받침있음
    last = word[-1]
    if '가' <= last <= '힣':
        return 받침있음 if (ord(last) - 0xAC00) % 28 != 0 else 받침없음
    if last in _ENG_NO_BATCHIM:
        return 받침없음
    return 받침있음  # F, L, M, N, R, S, X 및 숫자 등 → 받침 있는 쪽


def _i_ga(word: str) -> str:
    """주어 조사: "의자가", "책이" """
    return _josa(word, "이", "가")


def _un_neun(word: str) -> str:
    """보조사: "의자는", "책은" """
    return _josa(word, "은", "는")


# ── 거리 표현 ─────────────────────────────────────────────────────────────────

def _format_dist(dist_m: float) -> str:
    """
    거리(미터)를 "약 Xm 앞" 형식으로 변환 (사용자 인터뷰 Q10 반영).

    인터뷰 피드백: "약 5m 앞에 장애물이 있음 같은 대략적인 설명이 필요함"
    → Depth V2 추정값(오차 있지만 대략적 정보)을 그대로 활용.
    0.5m 미만은 즉각 위험이므로 "바로 코앞"으로 유지.
    3m 미만: 0.5m 단위 반올림 / 3m 이상: 1m 단위 반올림
    """
    dist_m = max(0.1, min(dist_m, 15.0))
    if dist_m < 0.5:
        return "코앞"
    if dist_m < 3.0:
        r = round(dist_m * 2) / 2          # 0.5m 단위
        r_str = f"{r:.1f}".rstrip("0").rstrip(".")
        return f"약 {r_str}미터"
    r = round(dist_m)                      # 1m 단위
    return f"약 {r}미터"


# ── 주요 물체 문장 생성 (위험도 1순위) ────────────────────────────────────────

def _primary(obj: dict, abs_clock: str) -> str:
    """가장 위험한 물체 1개에 대한 안내 문장 생성.

    색상 체계와 동일한 기준으로 문장 형식 결정:
      빨강(critical) → "위험! 방향 물체! 조심!"
      노랑(caution) → "방향 거리에 물체가 있어요. 액션"
      초록(info) → "방향 거리에 물체가 있어요."

    생활 물체(_EVERYDAY_KO)는 아무리 가까워도 긴급 표현 금지.
    SentenceBuilder.kt의 EVERYDAY_CLASSES 예외 처리와 동일 정책.
    """
    dist_m     = obj.get("distance_m", 0.0)
    name       = obj["class_ko"]
    ig         = _i_ga(name)
    direction  = CLOCK_TO_DIRECTION.get(abs_clock, abs_clock)
    dist_str   = _format_dist(dist_m)
    # "바로 앞" + "코앞" 중복 방지: "바로 앞 코앞에" → "바로 코앞에"
    loc_str    = "바로 코앞" if dist_str == "코앞" and direction == "바로 앞" else f"{direction} {dist_str}"
    is_vehicle = obj.get("is_vehicle", name in _VEHICLE_KO)
    is_animal  = obj.get("is_animal",  name in _ANIMAL_KO)
    is_hazard  = obj.get("is_hazard", False)
    action     = CLOCK_ACTION.get(abs_clock, "조심하세요").rstrip(".")

    # 생활 물체는 거리·크기 무관하게 긴급 표현 금지 (이중 방어)
    is_critical = (
        (name in _CRITICAL_KO or is_vehicle or (is_animal and dist_m < 3.0) or is_hazard)
        and name not in _EVERYDAY_KO
    )

    if is_critical:
        return f"위험! {direction} {name}! 조심!"

    # 생활 물체: 액션 없이 위치만 안내
    if name in _EVERYDAY_KO:
        return f"{loc_str}에 {name}{ig} 있어요."

    return f"{loc_str}에 {name}{ig} 있어요. {action}"


# ── 보조 물체 문장 생성 (위험도 2순위) ────────────────────────────────────────

def _secondary(obj: dict, abs_clock: str) -> str:
    """
    두 번째 물체에 대한 간략한 안내 문장.
    "~도 있어요" 형태로 첫 번째 물체와 구분됩니다.

    _primary보다 짧게 — 두 문장 합쳐도 TTS가 너무 길지 않아야 함
    """
    dist_m     = obj.get("distance_m", 0.0)
    name       = obj["class_ko"]
    direction  = CLOCK_TO_DIRECTION.get(abs_clock, abs_clock)
    dist_str   = _format_dist(dist_m)
    loc_str    = "바로 코앞" if dist_str == "코앞" and direction == "바로 앞" else f"{direction} {dist_str}"
    is_vehicle = obj.get("is_vehicle", name in _VEHICLE_KO)

    if is_vehicle and dist_m < 8.0:
        return f"{loc_str}에 {name}도 있어요!"
    return f"{loc_str}에 {name}도 있어요."


# ── 공개 함수들 ───────────────────────────────────────────────────────────────

def build_sentence(
    objects: list[dict],
    changes: list[str],
    camera_orientation: str = "front",
) -> str:
    """
    장애물/확인 모드의 메인 안내 문장 생성.

    Args:
        objects: detect_and_depth()가 반환한 탐지 물체 (위험도 순 정렬됨)
        changes: tracker가 감지한 변화 메시지 ["가방이 가까워지고 있어요"]
        camera_orientation: 폰 방향 (front/back/left/right)

    Returns:
        TTS로 바로 읽을 수 있는 한국어 문장
    """
    if not objects:
        # 물체 없어도 변화(공간 기억 차이)가 있으면 그걸 먼저 안내
        if changes:
            return changes[0]
        return "주변에 장애물이 없어요."

    parts = []
    for i, obj in enumerate(objects[:2]):  # 최대 2개만 안내 (더 많으면 혼란)
        # 카메라 방향 보정: 이미지 기준 방향 → 실제 방향
        abs_clock = get_absolute_clock(obj["direction"], camera_orientation)
        if i == 0:
            parts.append(_primary(obj, abs_clock))    # 첫 번째: 완전한 안내
        else:
            parts.append(_secondary(obj, abs_clock))  # 두 번째: "~도 있어요"

    result = " ".join(parts)
    # 공간 변화(새로 생긴/사라진 물체)가 있으면 맨 앞에 붙임
    if changes:
        return f"{changes[0]} {result}".strip()
    return result


def build_hazard_sentence(
    hazard: dict,
    objects: list[dict],
    changes: list[str],
    camera_orientation: str = "front",
) -> str:
    """
    계단·낙차·턱 등 바닥 위험을 최우선으로 안내.

    hazard.risk >= 0.7이면 다른 물체 안내 없이 위험만 말함.
    이유: 계단 앞에서 "의자도 있어요"까지 들을 시간이 없음.

    Args:
        hazard: detect_floor_hazards()가 반환한 hazard dict
        objects: YOLO 탐지 물체 (위험도 보조 참고용)
    """
    h_msg  = hazard.get("message", "앞에 위험해요.") # 문장간소화
    h_risk = hazard.get("risk", 0.5)

    # 고위험(0.7+) 또는 주변 물체 없으면 계단 경고만
    if h_risk >= 0.7 or not objects:
        return h_msg

    # 저위험 계단 + 주변 물체 있으면 둘 다 안내
    obj_sentence = build_sentence(objects[:1], [], camera_orientation)
    return f"{h_msg} 그리고 {obj_sentence}"


def build_find_sentence(
    target: str,
    objects: list[dict],
    camera_orientation: str = "front",
) -> str:
    """
    찾기 모드: "의자 찾아줘" → 의자 위치 안내.

    target이 비어있으면 일반 장애물 안내로 fallback.
    찾는 물체가 없으면 "보이지 않아요 + 카메라 돌려보세요" 안내.

    부분 일치 검색: "가방"으로 검색 시 "핸드백"도 매칭 (contains 사용)
    """
    if not target:
        return build_sentence(objects, [], camera_orientation)

    # ig·un을 if 블록 바깥에서 미리 계산
    # 수정 전: ig가 found 블록 안에서만 정의되어 물체를 못 찾으면 NameError 크래시
    # 수정 후: 항상 정의되므로 found 유무와 무관하게 안전하게 사용 가능
    ig = _i_ga(target)
    un = _un_neun(target)

    found = [o for o in objects if target in o.get("class_ko", "")]
    if found:
        obj       = found[0]
        abs_clock = get_absolute_clock(obj["direction"], camera_orientation)
        direction = CLOCK_TO_DIRECTION.get(abs_clock, abs_clock)
        dist_str  = _format_dist(obj.get("distance_m", 0.0))
        return f"{target}{un} {direction} {dist_str}에 있어요."

    return f"{target}{ig} 없어요. 다른 곳을 보여주세요."


def build_question_sentence(
    objects: list[dict],
    hazards: list[dict],
    scene: dict,
    tracked_state: list[dict],
    camera_orientation: str = "front",
) -> str:
    """
    사용자가 직접 질문했을 때 포괄적 현재 상황 안내.

    "지금 뭐가 있어?", "앞에 뭐 있어?" 같은 질문에 응답.
    현재 프레임 탐지 결과 + tracker에 누적된 최근 상태를 모두 활용.

    Args:
        objects:       현재 프레임 YOLO 탐지 결과
        hazards:       현재 프레임 바닥 위험 감지 결과
        scene:         신호등·군중·위험물 등 장면 정보
        tracked_state: tracker.get_current_state() — 최근 3초 누적 정보
        camera_orientation: 폰 방향
    """
    parts = []

    # 1. 계단·낙차 최우선 (낙상 위험)
    if hazards:
        top = max(hazards, key=lambda h: h.get("risk", 0))
        parts.append(top.get("message", "앞에 위험해요.")) # 문장 간소화

    # 2. 위험물 긴급 경고
    if scene.get("danger_warning"):
        parts.append(scene["danger_warning"])

    # 3. 현재 프레임 탐지 물체 (가장 신선한 정보)
    if objects:
        for i, obj in enumerate(objects[:2]):
            abs_clock = get_absolute_clock(obj["direction"], camera_orientation)
            parts.append(_primary(obj, abs_clock) if i == 0 else _secondary(obj, abs_clock))
    elif tracked_state:
        # 현재 프레임에 탐지 없으면 최근 tracker 상태로 대답
        for i, obj in enumerate(tracked_state[:2]):
            abs_clock = get_absolute_clock(obj.get("direction", "12시"), camera_orientation)
            name = obj["class_ko"]
            dist_str = _format_dist(obj["distance_m"])
            direction = CLOCK_TO_DIRECTION.get(abs_clock, abs_clock)
            ig = _i_ga(name)
            if i == 0:
                parts.append(f"최근에 {direction} {dist_str}에서 {name}{ig} 보였어요.")
            else:
                parts.append(f"{direction} {dist_str}에 {name}도 있었어요.")

    # 4. 신호등 정보
    if scene.get("traffic_light_msg"):
        parts.append(scene["traffic_light_msg"])

    # 5. 안전 경로
    if scene.get("safe_direction"):
        parts.append(scene["safe_direction"])

    if not parts:
        return "현재 주변에 장애물이 없어 안전해 보여요."

    return " ".join(parts)


