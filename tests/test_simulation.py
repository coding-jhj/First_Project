#!/usr/bin/env python
"""
VoiceGuide 현재 API 스키마 기준 시뮬레이션.

실제 서버를 띄우지 않고 FastAPI TestClient로 다음 흐름을 확인한다.
Android가 온디바이스 추론을 끝낸 뒤 /detect로 JSON을 보내고, 서버가
tracker/DB/SSE/대시보드 상태를 갱신하는 구조를 검증한다.
"""

from __future__ import annotations

import os
import tempfile
import time
import uuid

# 로컬 시뮬레이션은 외부 DB/API key 영향을 받지 않도록 격리한다.
os.environ.setdefault("API_KEY", "")
os.environ.pop("DATABASE_URL", None)

from fastapi.testclient import TestClient

from src.api import db
from src.api.main import app


def ok(status_code: int) -> str:
    return "OK" if 200 <= status_code < 300 else "FAIL"


def require_ok(response, label: str) -> dict:
    if not 200 <= response.status_code < 300:
        raise RuntimeError(f"{label} failed: HTTP {response.status_code} {response.text[:200]}")
    return response.json()


def print_step(title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))


def summarize_objects(objects: list[dict]) -> str:
    if not objects:
        return "없음"
    return ", ".join(
        f"{o.get('class_ko')}({o.get('direction')}, {o.get('distance_m')}m, risk={o.get('risk_score')})"
        for o in objects[:3]
    )


def main() -> int:
    session_id = f"sim-{uuid.uuid4().hex[:8]}"
    request_id = f"req-{session_id}"

    with tempfile.TemporaryDirectory(prefix="voiceguide-sim-") as tmpdir:
        db.DB_PATH = os.path.join(tmpdir, "voiceguide_sim.db")

        with TestClient(app) as client:
            print("=== VoiceGuide API 시뮬레이션 ===")
            print(f"session_id: {session_id}")
            print(f"db_path: {db.DB_PATH}")

            print_step("1. GET /health")
            r = client.get("/health")
            health = require_ok(r, "/health")
            print(f"Status: {r.status_code} {ok(r.status_code)}")
            print(f"role={health.get('role')}, inference={health.get('inference')}, db={health.get('db')}")
            print(f"db_writer={health.get('db_writer')}")

            print_step("2. GET /api/policy")
            r = client.get("/api/policy")
            policy = require_ok(r, "/api/policy")
            print(f"Status: {r.status_code} {ok(r.status_code)}")
            print(f"version={policy.get('version')}, class_groups={len(policy.get('classes', {}))}")

            print_step("3. POST /detect - Android 주 업로드 경로")
            detect_payload = {
                "event_id": request_id,
                "request_id": request_id,
                "device_id": session_id,
                "wifi_ssid": "SimWifi",
                "mode": "장애물",
                "camera_orientation": "front",
                "lat": 37.5665,
                "lng": 126.9780,
                "objects": [
                    {
                        "class_ko": "의자",
                        "confidence": 0.91,
                        "bbox_norm_xywh": [0.42, 0.43, 0.20, 0.25],
                    },
                    {
                        "class_ko": "자동차",
                        "confidence": 0.95,
                        "bbox_norm_xywh": [0.35, 0.35, 0.30, 0.32],
                        "is_vehicle": True,
                    },
                ],
                "client_perf": {
                    "decode_ms": 4,
                    "infer_ms": 28,
                    "dedup_ms": 3,
                    "total_ms": 35,
                },
            }
            r = client.post("/detect", json=detect_payload)
            body = require_ok(r, "/detect")
            print(f"Status: {r.status_code} {ok(r.status_code)}")
            print(f"sentence: {body.get('sentence')}")
            print(f"alert_mode: {body.get('alert_mode')}")
            print(f"objects: {summarize_objects(body.get('objects', []))}")
            print(f"perf: {body.get('perf')}")
            print(f"db_queued: {body.get('db_queued')}")

            # /detect는 비동기 writer를 쓰므로 짧게 대기해 latest_event 조회를 안정화한다.
            time.sleep(0.4)

            print_step("4. GET /status/{session_id}")
            r = client.get(f"/status/{session_id}")
            status = require_ok(r, "/status")
            print(f"Status: {r.status_code} {ok(r.status_code)}")
            print(f"objects: {summarize_objects(status.get('objects', []))}")
            print(f"gps: {status.get('gps')}")
            latest = status.get("latest_event") or {}
            print(f"latest_event_id: {latest.get('event_id')}")
            print(f"track_points: {len(status.get('track', []))}")

            print_step("5. POST /question - tracker 기반 질문 응답")
            r = client.post(
                "/question",
                json={
                    "device_id": session_id,
                    "wifi_ssid": "SimWifi",
                    "request_id": f"q-{session_id}",
                    "camera_orientation": "front",
                },
            )
            question = require_ok(r, "/question")
            print(f"Status: {r.status_code} {ok(r.status_code)}")
            print(f"sentence: {question.get('sentence')}")
            print(f"tracked: {summarize_objects(question.get('tracked', []))}")

            print_step("6. POST /detect_json - 구형 호환 경로")
            r = client.post(
                "/detect_json",
                json={
                    "device_id": session_id,
                    "wifi_ssid": "SimWifi",
                    "request_id": f"legacy-{session_id}",
                    "mode": "장애물",
                    "camera_orientation": "front",
                    "detections": [
                        {
                            "class_ko": "가방",
                            "confidence": 0.88,
                            "cx": 0.52,
                            "cy": 0.60,
                            "w": 0.18,
                            "h": 0.22,
                            "zone": "12시",
                            "dist_m": 1.7,
                            "risk_score": 0.62,
                        }
                    ],
                },
            )
            legacy = require_ok(r, "/detect_json")
            print(f"Status: {r.status_code} {ok(r.status_code)}")
            print(f"sentence: {legacy.get('sentence')}")
            print(f"objects: {summarize_objects(legacy.get('objects', []))}")

            recent = db.get_recent_detections(session_id, max_age_s=60)
            print(f"recent_detections_rows: {len(recent)}")

            print_step("7. POST /gps 및 GET /team-locations")
            for idx, (lat, lng) in enumerate([(37.5665, 126.9780), (37.5667, 126.9782)], start=1):
                r = client.post(
                    "/gps",
                    data={
                        "device_id": session_id,
                        "wifi_ssid": "SimWifi",
                        "lat": str(lat),
                        "lng": str(lng),
                        "request_id": f"gps-{idx}",
                    },
                )
                require_ok(r, f"/gps #{idx}")
                print(f"/gps #{idx}: {r.status_code} {ok(r.status_code)}")

            r = client.get("/team-locations")
            team_locations = require_ok(r, "/team-locations")
            print(f"/team-locations: {r.status_code} {ok(r.status_code)}")
            print(f"locations: {len(team_locations.get('locations', []))}")

            print_step("8. GET /sessions 및 /dashboard")
            r = client.get("/sessions")
            sessions = require_ok(r, "/sessions")
            print(f"Status: {r.status_code} {ok(r.status_code)}")
            print(f"sessions: {sessions.get('sessions')}")

            r = client.get("/dashboard")
            if not 200 <= r.status_code < 300 or "VoiceGuide" not in r.text:
                raise RuntimeError(f"/dashboard failed: HTTP {r.status_code}")
            print(f"/dashboard: {r.status_code} {ok(r.status_code)}")

            print("\n=== 시뮬레이션 완료 ===")
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
