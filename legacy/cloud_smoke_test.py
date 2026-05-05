import io
import requests
import time

BASE_URL = "https://voiceguide-135456731041.asia-northeast3.run.app"
WIFI_SSID = "test_session_dummy"

def test_health():
    r = requests.get(f"{BASE_URL}/health", timeout=10)
    assert r.status_code == 200
    data = r.json()
    print(f"[health] status={data.get('status')}, db={data.get('db_mode')}")

def make_dummy_jpeg():
    # 최소 유효한 1x1 JPEG (Pillow 없이)
    from PIL import Image
    img = Image.new("RGB", (320, 240), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf

def test_detect():
    img_buf = make_dummy_jpeg()
    r = requests.post(
        f"{BASE_URL}/detect",
        files={"image": ("test.jpg", img_buf, "image/jpeg")},
        data={
            "wifi_ssid": WIFI_SSID,
            "camera_orientation": "front",
            "mode": "장애물",
            "query_text": "",
        },
        timeout=30,  # YOLO+Depth 추론 시간 고려
    )
    assert r.status_code == 200
    data = r.json()
    assert "sentence" in data
    assert "objects" in data
    print(f"[detect] sentence={data['sentence'][:40]}")

def test_tts():
    r = requests.post(
        f"{BASE_URL}/tts",
        json={"text": "연결 테스트입니다."},
        timeout=15,
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/")
    print(f"[tts] audio bytes={len(r.content)}")

def test_locations():
    # 저장
    r = requests.post(
        f"{BASE_URL}/locations/save",
        json={"wifi_ssid": WIFI_SSID, "label": "테스트장소"},
        timeout=10,
    )
    assert r.status_code == 200

    # 조회
    r = requests.get(f"{BASE_URL}/locations", params={"wifi_ssid": WIFI_SSID}, timeout=10)
    assert r.status_code == 200
    data = r.json()
    print(f"[locations] count={len(data.get('locations', []))}")

if __name__ == "__main__":
    tests = [test_health, test_tts, test_detect, test_locations]
    for t in tests:
        try:
            
            t()
            print(f"  PASS: {t.__name__}")
            # print(f'{t.request.method} {t.request.url} → {t.request.status_code}')
        except Exception as e:
            print(f"  FAIL: {t.__name__} → {e}")
            # print(f'{t.request.post.status_code}')