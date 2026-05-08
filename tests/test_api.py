import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"  # Windows OpenMP 라이브러리 충돌 방지

from fastapi.testclient import TestClient
from src.api.main import app
from src.api import db
from src.api import routes

db.init_db()

# TestClient: uvicorn 서버 없이 FastAPI 앱을 직접 테스트 (httpx 기반)
client = TestClient(app)


def test_policy_endpoint():
    r = client.get("/api/policy")
    assert r.status_code == 200
    body = r.json()
    assert body.get("version", 0) >= 1
    assert "classes" in body
    assert "vehicle_ko" in body["classes"]


def test_detect_endpoint_exists():
    # /detect는 온디바이스 탐지 결과 JSON을 받는다.
    response = client.post("/detect", json={"device_id": "test_device", "objects": []})
    assert response.status_code == 200


def test_detect_response_schema():
    # 정상 탐지 JSON 전송 시 응답 필드 구조가 Android 앱 기대 스키마와 일치하는지 확인
    payload = {
        "event_id": "evt-test-1",
        "request_id": "req-test-1",
        "device_id": "test_device",
        "wifi_ssid": "test_wifi",
        "mode": "장애물",
        "camera_orientation": "front",
        "objects": [
            {
                "class_ko": "의자",
                "confidence": 0.91,
                "bbox_norm_xywh": [0.4, 0.45, 0.2, 0.25],
            }
        ],
        "client_perf": {"infer_ms": 12},
    }
    response = client.post(
        "/detect",
        json=payload,
    )
    assert response.status_code == 200
    body = response.json()
    assert "sentence"     in body   # TTS로 바로 읽을 한국어 문장
    assert "objects"      in body   # YOLO 탐지 물체 목록
    assert "hazards"      in body   # 바닥 위험 감지 필드 추가됨
    assert "changes"      in body   # 공간 기억 변화 목록
    assert "depth_source" in body   # on-device bbox 기반 거리 추정 방법
    assert "event_id"     in body
    assert "session_id"   in body
    assert isinstance(body["sentence"], str)
    assert isinstance(body["objects"],  list)
    assert isinstance(body["hazards"],  list)
    assert isinstance(body["changes"],  list)
    assert len(body["sentence"]) > 0  # 빈 문장 반환 금지
    assert body["objects"][0]["depth_source"] == "on_device_bbox"


def test_detect_json_persists_recent_detections():
    payload = {
        "device_id": "test_detect_json_device",
        "wifi_ssid": "test_detect_json_wifi",
        "request_id": "req-detect-json-1",
        "mode": "장애물",
        "camera_orientation": "front",
        "lat": 37.5665,
        "lng": 126.9780,
        "detections": [
            {
                "class_ko": "의자",
                "confidence": 0.91,
                "cx": 0.5,
                "cy": 0.55,
                "w": 0.2,
                "h": 0.25,
                "zone": "12시",
                "dist_m": 1.5,
            }
        ],
    }
    response = client.post("/detect_json", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["sentence"]
    assert body["objects"][0]["class_ko"] == "의자"

    recent = db.get_recent_detections("test_detect_json_device", max_age_s=60)
    assert recent
    assert recent[0]["class_ko"] == "의자"


def test_spaces_snapshot_endpoint():
    # 공간 스냅샷 수동 저장 엔드포인트 — 디버깅/테스트 전용
    payload = {"space_id": "test_ssid", "objects": []}
    response = client.post("/spaces/snapshot", json=payload)
    assert response.status_code == 200
    assert response.json() == {"saved": True}


def test_protected_status_requires_api_key(monkeypatch):
    # API_KEY 설정 시 X-API-Key 헤더 없이 접근하면 401 반환, 헤더 포함 시 200 반환
    monkeypatch.setattr(routes, "_API_KEY", "test-secret")
    response = client.get("/status/test_ssid")
    assert response.status_code == 401  # 인증 없이 거부

    ok = client.get("/status/test_ssid", headers={"X-API-Key": "test-secret"})
    assert ok.status_code == 200  # 올바른 키로 통과
