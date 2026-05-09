"""
데모용 GPS 동선 시뮬레이터.

실제 GPS 대신 미리 짜둔 경로 좌표를 서버에 전송해 대시보드 지도에 이동 경로를 표시합니다.
개인정보(실제 위치) 없이 데모·발표를 진행할 수 있습니다.

사용법:
    python tools/simulator.py

대시보드에서 SESSION_ID 값을 세션 ID에 입력하면 경로가 실시간으로 그려집니다.
"""

import time
import sys
import requests
from datetime import datetime

# ── 설정 (여기만 수정하면 됩니다) ──────────────────────────────────────────────

SERVER_URL = "https://voiceguide-1063164560758.asia-northeast3.run.app"
SESSION_ID = "demo-device-02"   # 대시보드 세션 ID 입력창에 이 값 사용
API_KEY    = ""                  # .env의 API_KEY 값 (없으면 빈 문자열)
INTERVAL   = 2.0                 # 좌표 전송 간격 (초)
LOOP       = False               # True 이면 경로를 반복 순환

# ── 경로 좌표 (위도, 경도, 설명) ───────────────────────────────────────────────
# 실제 건물·경로에 맞게 좌표를 수정하세요.
# 구글 지도에서 원하는 지점 우클릭 → 좌표 복사
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

# ───────────────────────────────────────────────────────────────────────────────

HEADERS = {"X-API-Key": API_KEY} if API_KEY else {}

_collected: list[dict] = []  # 전송 성공한 좌표 누적 (경로 저장용)


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


def run():
    print(f"\nVoiceGuide GPS 시뮬레이터")
    print(f"  서버     : {SERVER_URL}")
    print(f"  세션 ID  : {SESSION_ID}")
    print(f"  전송 간격: {INTERVAL}초")
    print(f"  경로     : {len(ROUTE)}개 좌표")
    print(f"  반복     : {'켜짐' if LOOP else '꺼짐'}")
    print(f"\n대시보드 세션 ID 입력창에 '{SESSION_ID}' 를 입력하세요.\n")

    round_num = 1
    while True:
        if LOOP:
            print(f"── 경로 {round_num}회차 ──────────────────")
        for lat, lng, label in ROUTE:
            if not send_gps(lat, lng, label):
                print("\n서버 오류로 시뮬레이션을 중단합니다.")
                save_route()
                sys.exit(1)
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
