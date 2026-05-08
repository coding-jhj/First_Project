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

# ── 설정 (여기만 수정하면 됩니다) ──────────────────────────────────────────────

SERVER_URL = "https://voiceguide-1063164560758.asia-northeast3.run.app"
SESSION_ID = "demo-device-01"   # 대시보드 세션 ID 입력창에 이 값 사용
API_KEY    = ""                  # .env의 API_KEY 값 (없으면 빈 문자열)
INTERVAL   = 2.0                 # 좌표 전송 간격 (초)
LOOP       = False               # True 이면 경로를 반복 순환

# ── 경로 좌표 (위도, 경도, 설명) ───────────────────────────────────────────────
# 실제 건물·경로에 맞게 좌표를 수정하세요.
# 구글 지도에서 원하는 지점 우클릭 → 좌표 복사
ROUTE = [
    (37.496880, 127.028490, "출발: 건물 입구"),
    (37.496920, 127.028510, "1층 복도 시작"),
    (37.496960, 127.028530, "복도 중간"),
    (37.497000, 127.028550, "복도 끝"),
    (37.497040, 127.028560, "계단 앞"),
    (37.497080, 127.028570, "계단 오르는 중"),
    (37.497120, 127.028580, "2층 도착"),
    (37.497160, 127.028590, "2층 복도"),
    (37.497200, 127.028600, "목적지 도착"),
]

# ───────────────────────────────────────────────────────────────────────────────

HEADERS = {"X-Api-Key": API_KEY} if API_KEY else {}


def send_gps(lat: float, lng: float, label: str) -> bool:
    try:
        resp = requests.post(
            f"{SERVER_URL}/gps",
            data={"device_id": SESSION_ID, "lat": lat, "lng": lng},
            headers=HEADERS,
            timeout=5,
        )
        status = "✅" if resp.status_code == 200 else f"❌ {resp.status_code}"
        print(f"  {status}  {label}  ({lat:.6f}, {lng:.6f})")
        return resp.status_code == 200
    except requests.exceptions.ConnectionError:
        print(f"  ❌ 서버 연결 실패 — {SERVER_URL} 확인")
        return False
    except Exception as e:
        print(f"  ❌ 오류: {e}")
        return False


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
