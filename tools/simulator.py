"""
데모용 GPS 동선 시뮬레이터.

실제 GPS 대신 미리 짜둔 경로 좌표를 서버에 전송해 대시보드 지도에 이동 경로를 표시합니다.
DETECT_ENABLED = True 이면 경로 중 지정된 좌표에서 YOLO 추론을 실행해
탐지 결과도 함께 서버에 전송, 대시보드 물체 카드에 실시간 반영됩니다.

사용법:
    python tools/simulator.py

대시보드에서 SESSION_ID 값을 세션 ID에 입력하면 경로와 탐지 내역이 실시간으로 표시됩니다.
"""

import sys
import time
import requests
from datetime import datetime
from pathlib import Path

# tools/ 디렉터리에서 프로젝트 루트 경로를 찾아 임포트 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

# ── 설정 (여기만 수정하면 됩니다) ──────────────────────────────────────────────

SERVER_URL = "https://voiceguide-1063164560758.asia-northeast3.run.app"
SESSION_ID = "demo-device-02"   # 대시보드 세션 ID 입력창에 이 값 사용
API_KEY    = ""                  # .env의 API_KEY 값 (없으면 빈 문자열)
INTERVAL   = 2.0                 # 좌표 전송 간격 (초)
LOOP       = False               # True 이면 경로를 반복 순환

# ── 더미 장면 탐지 설정 ─────────────────────────────────────────────────────────
DETECT_ENABLED = True            # False 로 바꾸면 GPS만 전송 (기존 동작)
TFLITE_MODEL   = "android/app/src/main/assets/yolo11n_320.tflite"

# ── 경로 좌표 (위도, 경도, 설명) ───────────────────────────────────────────────
ROUTE = [
    (37.653404, 127.043607, "출발: 아파트 입구"),
    (37.653331, 127.044015, "아파트내1"),
    (37.653539, 127.044069, "아파트내2"),
    (37.653692, 127.043404, "아파트밖 골목길"),
    (37.653371, 127.043303, "아파트밖 골목길2"),
    (37.653091, 127.043114, "골목길1"),
    (37.652998, 127.043355, "골목길2"),
    (37.652929, 127.043605, "골목길3"),
    (37.652859, 127.043738, "골목길4"),
    (37.652768, 127.043840, "골목길5"),
    (37.652573, 127.043941, "골목길6"),
    (37.652442, 127.043966, "큰길"),
    (37.652703, 127.045057, "큰길2"),
    (37.652849, 127.045720, "상가 앞"),
    (37.653078, 127.046838, "창동역 도착"),
]

# ── 경로별 더미 장면 매핑 ────────────────────────────────────────────────────────
# ultralytics 패키지에 내장된 테스트 이미지 사용 (설치만 되면 항상 존재)
# bus.jpg    : 버스 + 사람이 포함된 도로 장면
# zidane.jpg : 사람이 포함된 장면
try:
    import ultralytics as _ul
    _A      = Path(_ul.__file__).parent / "assets"
    _BUS    = str(_A / "bus.jpg")
    _PERSON = str(_A / "zidane.jpg")
    _ASSETS_OK = _A.exists()
except Exception:
    _BUS = _PERSON = ""
    _ASSETS_OK = False

# key = ROUTE 인덱스, value = 테스트 이미지 경로 (None = 탐지 없음)
WAYPOINT_SCENES: dict[int, str | None] = {
    0:  None,      # 출발: 아파트 입구 — 탐지 없음
    1:  _PERSON,   # 아파트내1 — 사람 탐지
    2:  None,
    3:  None,
    4:  _PERSON,   # 아파트밖 골목길2 — 사람/가방 탐지
    5:  _BUS,      # 골목길1 — 다중 물체 (버스·사람)
    6:  None,
    7:  _PERSON,   # 골목길3 — 사람 가까이
    8:  None,
    9:  None,
    10: None,
    11: _BUS,      # 큰길 — 차도 장면 (버스·자동차)
    12: None,
    13: _PERSON,   # 상가 앞 — 사람
    14: _BUS,      # 창동역 도착 — 버스 + 사람
}

# ───────────────────────────────────────────────────────────────────────────────

HEADERS = {"X-API-Key": API_KEY} if API_KEY else {}

_collected: list[dict] = []   # 전송 성공한 좌표 누적 (경로 저장용)
_detect_ready = False          # YOLO 모델 로드 성공 여부


# ── YOLO 모델 초기화 ──────────────────────────────────────────────────────────

def _init_detect() -> bool:
    """
    YOLO 모델을 로드한다 (TFLite → PT → 더미 순서로 시도).
    실패해도 GPS 전송은 정상 동작 — 데모 중 모델 오류로 발표 중단 방지.
    """
    global _detect_ready
    if not DETECT_ENABLED:
        print("  YOLO 탐지: 꺼짐 (DETECT_ENABLED=False)")
        return False
    if not _ASSETS_OK:
        print("  YOLO 탐지: 꺼짐 (ultralytics 미설치 또는 assets 없음)")
        return False
    try:
        import dummy_scenes
        dummy_scenes.load_model(TFLITE_MODEL)
        _detect_ready = True
        mode = "더미" if dummy_scenes._dummy_mode else TFLITE_MODEL
        print(f"  YOLO 탐지: 켜짐 ({mode})")
        return True
    except Exception as e:
        print(f"  YOLO 탐지: 로드 실패 — {e}")
        print("  └─ GPS만 전송합니다.")
        return False


# ── GPS 전송 ──────────────────────────────────────────────────────────────────

def send_gps(lat: float, lng: float, label: str) -> bool:
    try:
        resp = requests.post(
            f"{SERVER_URL}/gps",
            data={"device_id": SESSION_ID, "lat": lat, "lng": lng},
            headers=HEADERS,
            timeout=5,
        )
        ok = resp.status_code == 200
        status = "✅" if ok else f"❌ {resp.status_code}"
        print(f"  {status}  {label}  ({lat:.6f}, {lng:.6f})")
        if ok:
            _collected.append({"lat": lat, "lng": lng})
        return ok
    except requests.exceptions.ConnectionError:
        print(f"  ❌ 서버 연결 실패 — {SERVER_URL} 확인")
        return False
    except Exception as e:
        print(f"  ❌ 오류: {e}")
        return False


# ── 탐지 결과 전송 ────────────────────────────────────────────────────────────

def send_detect(lat: float, lng: float, objects: list[dict]) -> None:
    """
    YOLO 추론 결과를 /detect 에 전송한다.
    서버가 NLG 문장 생성 + SSE 브로드캐스트까지 처리한다.
    실패해도 시뮬레이션은 계속 진행.
    """
    if not objects:
        return
    try:
        resp = requests.post(
            f"{SERVER_URL}/detect",
            json={
                "device_id": SESSION_ID,
                "mode":      "장애물",
                "lat":       lat,
                "lng":       lng,
                "objects":   objects,
            },
            headers=HEADERS,
            timeout=5,
        )
        names  = ", ".join(o["class_ko"] for o in objects[:3])
        extra  = f" 외 {len(objects) - 3}개" if len(objects) > 3 else ""
        status = "✅" if resp.status_code == 200 else f"❌ {resp.status_code}"
        print(f"    └─ 탐지 {status}: {names}{extra} ({len(objects)}개)")
    except Exception as e:
        print(f"    └─ 탐지 전송 실패: {e}")


# ── 경로 저장 ─────────────────────────────────────────────────────────────────

def save_route():
    if not _collected:
        return
    name = f"데모 {datetime.now():%m/%d %H:%M}"
    try:
        resp = requests.post(
            f"{SERVER_URL}/gps/route/save",
            json={"device_id": SESSION_ID, "name": name},
            headers=HEADERS,
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("saved"):
                print(f"\n경로 저장 완료 — '{name}' ({data.get('point_count', 0)}개 포인트)")
            else:
                print(f"\n경로 저장 건너뜀: {data.get('reason', '')}")
        else:
            print(f"\n경로 저장 실패 ({resp.status_code})")
    except Exception as e:
        print(f"\n경로 저장 오류: {e}")


# ── 메인 실행 ─────────────────────────────────────────────────────────────────

def run():
    print(f"\nVoiceGuide GPS 시뮬레이터")
    print(f"  서버     : {SERVER_URL}")
    print(f"  세션 ID  : {SESSION_ID}")
    print(f"  전송 간격: {INTERVAL}초")
    print(f"  경로     : {len(ROUTE)}개 좌표")
    print(f"  반복     : {'켜짐' if LOOP else '꺼짐'}")
    _init_detect()
    print(f"\n대시보드 세션 ID 입력창에 '{SESSION_ID}' 를 입력하세요.\n")

    round_num = 1
    while True:
        if LOOP:
            print(f"── 경로 {round_num}회차 ──────────────────")
        for idx, (lat, lng, label) in enumerate(ROUTE):
            if not send_gps(lat, lng, label):
                print("\n서버 오류로 시뮬레이션을 중단합니다.")
                save_route()
                sys.exit(1)

            # 탐지가 설정된 좌표에서만 YOLO 추론 + 전송
            if _detect_ready:
                scene = WAYPOINT_SCENES.get(idx)
                if scene:
                    try:
                        import dummy_scenes
                        objects = dummy_scenes.run_scene(scene)
                        send_detect(lat, lng, objects)
                    except Exception as e:
                        print(f"    └─ 탐지 추론 실패 (GPS는 계속 전송): {e}")

            time.sleep(INTERVAL)

        if not LOOP:
            print("\n시뮬레이션 완료.")
            break
        round_num += 1
        print()


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n\n사용자가 중단했습니다.")
    finally:
        save_route()
