"""
VoiceGuide FastAPI 라우터
===========================
Android 앱과 Gradio 데모가 호출하는 API 엔드포인트를 정의합니다.

주요 엔드포인트:
  POST /detect           — 온디바이스 탐지 결과 JSON 수신/배포/저장
  POST /locations/save   — 장소 저장
  GET  /locations        — 저장 장소 목록
  GET  /locations/find/{label} — 장소 검색
  DELETE /locations/{label}   — 장소 삭제
  POST /stt              — PC 마이크 음성 인식 (Gradio 데모용)

설계 원칙:
  - 모든 엔드포인트는 반드시 sentence 필드를 반환 → TTS로 바로 읽을 수 있음
  - 오류가 나도 음성 안내가 나오도록 전역 예외 핸들러 적용 (main.py)
  - 서버는 YOLO 추론이나 이미지 분석을 하지 않고, 앱이 보낸 JSON만 처리
"""

import os
import uuid
import hashlib
import json
import asyncio
from collections import defaultdict

from fastapi import APIRouter, Depends, Body, Form, Header, HTTPException, Response
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

# ── API Key 인증 ────────────────────────────────────────────────────────────
_API_KEY = os.getenv("API_KEY", "")

def _verify_api_key(
    authorization: str = Header(default=""),
    x_api_key: str = Header(default=""),
) -> None:
    if not _API_KEY:
        return
    if authorization == f"Bearer {_API_KEY}" or x_api_key == _API_KEY:
        return
    raise HTTPException(status_code=401, detail="Invalid or missing API key")

from src.nlg.sentence import (
    build_sentence, build_find_sentence,
    build_question_sentence, build_held_sentence,
    get_alert_mode, _i_ga,
)
from src.api import db
from src.api import events
from src.api.tracker import get_tracker

router = APIRouter()

@router.get("/api/policy")
async def get_voice_policy(
    response: Response,
    if_none_match: str = Header(default=None),
    x_app_client: str = Header(default=None)
):
    """SSOT 정책 JSON — Android 온디바이스 NLG와 동기화 (ETag 트래픽 최적화)"""
    # 하위 호환성 유지: 헤더가 없는 구버전은 통과, 이상한 값을 보내면 차단
    if x_app_client is not None and x_app_client != "voiceguide-android-v1":
        raise HTTPException(status_code=403, detail="Forbidden Client")

    from src.config.policy import get_policy
    policy_dict = get_policy()

    # ETag(데이터 지문) 캐싱 처리
    policy_str = json.dumps(policy_dict, sort_keys=True)
    etag = hashlib.md5(policy_str.encode("utf-8")).hexdigest()
    client_etag = if_none_match.strip('"') if if_none_match else None

    if client_etag == etag:
        return Response(status_code=304)

    response.headers["ETag"] = f'"{etag}"'
    return policy_dict

# ── 세션별 마지막 문장 캐시 (TTS 중복 방지) ────────────────────────────────────
import time as _time
_last_sentence: dict[str, tuple[str, float]] = {}
_DEDUP_SECS = 2.5
_SAVE_EVERY_N_FRAMES = max(1, int(os.getenv("DETECT_SAVE_EVERY_N_FRAMES", "5")))
_SNAPSHOT_MIN_INTERVAL_S = float(os.getenv("SNAPSHOT_MIN_INTERVAL_S", "1.0"))
_last_snapshot: dict[str, tuple[str, float]] = {}
_frame_counts: dict[str, int] = defaultdict(int)


def _object_signature(objects: list[dict]) -> str:
    parts = []
    for obj in objects[:8]:
        bbox = obj.get("bbox_norm_xywh") or [0, 0, 0, 0]
        area = round(float(bbox[2]) * float(bbox[3]), 3) if len(bbox) >= 4 else 0
        parts.append(f"{obj.get('class_ko')}:{obj.get('direction')}:{area}")
    return "|".join(parts)


def _should_persist_frame(session_id: str, objects: list[dict], mode: str) -> bool:
    _frame_counts[session_id] += 1
    if mode in {"질문", "찾기", "들고있는것"}:
        return True
    if _frame_counts[session_id] % _SAVE_EVERY_N_FRAMES == 0:
        return True
    signature = _object_signature(objects)
    prev_signature, prev_ts = _last_snapshot.get(session_id, ("", 0.0))
    return signature != prev_signature and (_time.monotonic() - prev_ts) >= _SNAPSHOT_MIN_INTERVAL_S


def _mark_persisted(session_id: str, objects: list[dict]) -> None:
    _last_snapshot[session_id] = (_object_signature(objects), _time.monotonic())


def _publish_dashboard_event(session_id: str, payload: dict, gps: dict | None = None, track: list[dict] | None = None) -> None:
    events.publish(session_id, {
        "session_id": session_id,
        "objects": payload.get("objects", []),
        "gps": gps,
        "track": track or [],
        "latest_event": {
            "event_id": payload.get("event_id"),
            "request_id": payload.get("request_id"),
            "objects": payload.get("objects", []),
            "hazards": payload.get("hazards", []),
            "scene": payload.get("scene", {}),
        },
    })

def _normalize_session_id(wifi_ssid: str = "", device_id: str = "") -> str:
    """기기별 대시보드 세션 ID 정규화."""
    preferred = device_id or wifi_ssid
    value = (preferred or "").strip().strip('"')
    if not value or value.lower() in {"<unknown ssid>", "unknown ssid", "0x"}:
        # 버그 수정: 익명 유저 간 세션 꼬임 방지 (일회용 UUID 부여)
        return f"anonymous_{uuid.uuid4().hex[:8]}"
    return value

def _with_perf(payload: dict, t0: float, request_id: str, detect_ms: int = 0, tracker_ms: int = 0) -> dict:
    process_ms = int((_time.monotonic() - t0) * 1000)
    nlg_ms = max(0, process_ms - detect_ms - tracker_ms)
    payload.update({
        "request_id": request_id,
        "process_ms": process_ms,
        "perf": {
            "detect_ms": detect_ms,
            "tracker_ms": tracker_ms,
            "nlg_ms": nlg_ms,
            "total_ms": process_ms,
        },
    })
    return payload

def _should_suppress(session_id: str, sentence: str, alert_mode: str) -> bool:
    if alert_mode == "critical":
        _last_sentence[session_id] = (sentence, _time.monotonic())
        return False
    prev_sentence, prev_ts = _last_sentence.get(session_id, ("", 0.0))
    if sentence == prev_sentence and (_time.monotonic() - prev_ts) < _DEDUP_SECS:
        return True
    _last_sentence[session_id] = (sentence, _time.monotonic())
    return False

def _space_changes(current: list[dict], previous: list[dict]) -> list[str]:
    prev_set = {o["class_ko"] for o in previous}
    curr_set = {o["class_ko"] for o in current}
    changes = []
    for name in curr_set - prev_set:
        changes.append(f"{name}{_i_ga(name)} 생겼어요")
    for name in prev_set - curr_set:
        changes.append(f"{name}{_i_ga(name)} 없어졌어요")
    return changes


_ZONE_BOUNDARIES = [
    (0.11, "8시"), (0.22, "9시"), (0.33, "10시"),
    (0.44, "11시"), (0.56, "12시"), (0.67, "1시"),
    (0.78, "2시"), (0.89, "3시"), (1.01, "4시"),
]


def _direction_from_bbox(obj: dict) -> str:
    if obj.get("direction"):
        return str(obj["direction"])
    bbox = obj.get("bbox_norm_xywh") or []
    if len(bbox) >= 4:
        cx = float(bbox[0]) + float(bbox[2]) / 2
    else:
        cx = float(obj.get("cx", 0.5))
    for boundary, label in _ZONE_BOUNDARIES:
        if cx < boundary:
            return label
    return "4시"


def _distance_from_bbox(obj: dict) -> float:
    if obj.get("distance_m") is not None:
        return round(float(obj["distance_m"]), 1)
    bbox = obj.get("bbox_norm_xywh") or []
    if len(bbox) >= 4:
        area = max(0.0001, float(bbox[2]) * float(bbox[3]))
    else:
        area = max(0.0001, float(obj.get("w", 0.1)) * float(obj.get("h", 0.1)))
    try:
        from src.config.policy import get_policy
        calib = float(get_policy().get("on_device", {}).get("bbox_calib_area", 0.12))
    except Exception:
        calib = 0.12
    return round(min(15.0, max(0.1, (calib / area) ** 0.5)), 1)


def _risk_from_object(obj: dict) -> float:
    if obj.get("risk_score") is not None:
        return float(obj["risk_score"])
    dist = float(obj.get("distance_m", 15.0))
    bbox = obj.get("bbox_norm_xywh") or [0, 0, 0.1, 0.1]
    area = float(bbox[2]) * float(bbox[3]) if len(bbox) >= 4 else 0.01
    distance_score = max(0.0, min(1.0, (7.0 - dist) / 7.0))
    area_score = max(0.0, min(1.0, area / 0.12))
    return round(max(distance_score, area_score), 2)


def _normalize_objects(raw_objects: list[dict]) -> list[dict]:
    from src.config.policy import get_policy
    classes = get_policy().get("classes", {})
    vehicle_ko = set(classes.get("vehicle_ko", []))
    animal_ko = set(classes.get("animal_ko", []))
    critical_ko = set(classes.get("critical_ko", []))

    objects = []
    for raw in raw_objects:
        if not isinstance(raw, dict):
            continue
        class_ko = str(raw.get("class_ko") or raw.get("classKo") or raw.get("label") or "").strip()
        if not class_ko:
            continue
        bbox = raw.get("bbox_norm_xywh")
        if not bbox:
            cx = float(raw.get("cx", 0.5))
            cy = float(raw.get("cy", 0.5))
            w = float(raw.get("w", 0.1))
            h = float(raw.get("h", 0.1))
            bbox = [round(cx - w / 2, 6), round(cy - h / 2, 6), round(w, 6), round(h, 6)]
        bbox = [round(float(v), 6) for v in bbox[:4]]
        obj = {
            "class": str(raw.get("class") or raw.get("class_name") or class_ko),
            "class_ko": class_ko,
            "confidence": round(float(raw.get("confidence", 0.0)), 4),
            "bbox_norm_xywh": bbox,
            "direction": _direction_from_bbox({**raw, "bbox_norm_xywh": bbox}),
            "depth_source": str(raw.get("depth_source", "on_device_bbox")),
            "is_vehicle": bool(raw.get("is_vehicle", class_ko in vehicle_ko)),
            "is_animal": bool(raw.get("is_animal", class_ko in animal_ko)),
            "is_dangerous": bool(raw.get("is_dangerous", class_ko in critical_ko)),
        }
        obj["distance_m"] = _distance_from_bbox({**raw, "bbox_norm_xywh": bbox})
        obj["risk_score"] = _risk_from_object(obj)
        objects.append(obj)
    return sorted(objects, key=lambda x: x.get("risk_score", 0), reverse=True)[:8]


@router.post("/detect", dependencies=[Depends(_verify_api_key)])
async def detect(
    payload: dict = Body(...),
):
    _t0 = _time.monotonic()
    wifi_ssid = str(payload.get("wifi_ssid", ""))
    device_id = str(payload.get("device_id", ""))
    camera_orientation = str(payload.get("camera_orientation", "front"))
    mode = str(payload.get("mode", "장애물"))
    query_text = str(payload.get("query_text", ""))
    lat = float(payload.get("lat") or 0.0)
    lng = float(payload.get("lng") or 0.0)
    request_id = str(payload.get("request_id") or "")
    request_id = request_id or f"srv-{int(_t0 * 1000)}"
    event_id = str(payload.get("event_id") or request_id or uuid.uuid4().hex)
    session_id = _normalize_session_id(wifi_ssid, device_id)

    if lat != 0.0 or lng != 0.0:
        db.save_gps(session_id, lat, lng)

    objects = _normalize_objects(payload.get("objects", []))
    hazards = payload.get("hazards", [])
    if not isinstance(hazards, list):
        hazards = []
    scene = payload.get("scene", {})
    if not isinstance(scene, dict):
        scene = {}
    _detect_ms = int(payload.get("client_perf", {}).get("infer_ms", 0) or 0)

    _t_tracker = _time.monotonic()
    tracker = get_tracker(session_id)
    objects, motion_changes = tracker.update(objects)
    _tracker_ms = int((_time.monotonic() - _t_tracker) * 1000)

    should_persist = _should_persist_frame(session_id, objects, mode)
    previous = db.get_snapshot(wifi_ssid) if should_persist and wifi_ssid else None
    space_changes = _space_changes(objects, previous) if previous and objects else []
    if objects and should_persist:
        db.save_snapshot(wifi_ssid, objects)
        db.save_snapshot(session_id, objects)
        _mark_persisted(session_id, objects)

    all_changes = motion_changes + space_changes
    db_enqueued = False
    if should_persist:
        db_enqueued = db.enqueue_detection_event(
            event_id=event_id,
            request_id=request_id,
            session_id=session_id,
            device_id=device_id,
            wifi_ssid=wifi_ssid,
            mode=mode,
            objects=objects,
            hazards=hazards,
            scene=scene,
            raw_payload=payload,
            lat=lat if lat != 0.0 or lng != 0.0 else None,
            lng=lng if lat != 0.0 or lng != 0.0 else None,
        )

    if mode == "들고있는것":
        sentence = build_held_sentence(objects)
        response_payload = _with_perf({
            "mode": mode, "event_id": event_id, "session_id": session_id,
            "sentence": sentence, "alert_mode": "critical",
            "objects": objects, "hazards": hazards, "changes": motion_changes,
            "db_queued": db_enqueued,
            "depth_source": objects[0].get("depth_source", "bbox") if objects else "bbox",
        }, _t0, request_id, _detect_ms, _tracker_ms)
        _publish_dashboard_event(session_id, response_payload, db.get_last_gps(session_id), db.get_gps_track(session_id, limit=100))
        return response_payload

    if mode == "질문":
        tracked = tracker.get_current_state(max_age_s=3.0)
        sentence = build_question_sentence(objects, hazards, scene, tracked, camera_orientation)
        alert_mode = get_alert_mode(objects[0], is_hazard=bool(hazards)) if objects else ("critical" if hazards else "silent")
        response_payload = _with_perf({
            "mode": mode, "event_id": event_id, "session_id": session_id,
            "sentence": sentence, "alert_mode": alert_mode,
            "objects": objects, "hazards": hazards, "changes": motion_changes,
            "scene": scene, "tracked": tracked,
            "db_queued": db_enqueued,
            "depth_source": objects[0].get("depth_source", "bbox") if objects else "bbox",
        }, _t0, request_id, _detect_ms, _tracker_ms)
        _publish_dashboard_event(session_id, response_payload, db.get_last_gps(session_id), db.get_gps_track(session_id, limit=100))
        return response_payload

    if mode == "찾기":
        target = _extract_find_target(query_text)
        sentence = build_find_sentence(target, objects, camera_orientation)
        response_payload = _with_perf({
            "mode": mode, "event_id": event_id, "session_id": session_id,
            "sentence": sentence, "alert_mode": "critical",
            "objects": objects, "hazards": hazards, "changes": all_changes,
            "db_queued": db_enqueued,
            "depth_source": objects[0].get("depth_source", "bbox") if objects else "bbox",
        }, _t0, request_id, _detect_ms, _tracker_ms)
        _publish_dashboard_event(session_id, response_payload, db.get_last_gps(session_id), db.get_gps_track(session_id, limit=100))
        return response_payload

    sentence = build_sentence(objects, all_changes, camera_orientation=camera_orientation)
    alert_mode = get_alert_mode(objects[0]) if objects else "silent"

    extras = [v for v in [
        scene.get("danger_warning"), scene.get("slippery_warning"),
        scene.get("tactile_block_warning"), scene.get("crowd_warning"),
        scene.get("safe_direction"), scene.get("traffic_light_msg"),
    ] if v]
    if extras:
        sentence = sentence + " " + " ".join(extras)

    if _should_suppress(session_id, sentence, alert_mode):
        alert_mode = "silent"

    response_payload = _with_perf({
        "mode": mode, "event_id": event_id, "session_id": session_id,
        "sentence": sentence, "alert_mode": alert_mode,
        "objects": objects, "hazards": hazards, "changes": all_changes, "scene": scene,
        "db_queued": db_enqueued,
        "depth_source": objects[0].get("depth_source", "bbox") if objects else "bbox",
    }, _t0, request_id, _detect_ms, _tracker_ms)
    _publish_dashboard_event(session_id, response_payload, db.get_last_gps(session_id), db.get_gps_track(session_id, limit=100))
    return response_payload

def _extract_find_target(text: str) -> str:
    """
    찾기 명령어에서 대상 물체 이름 추출.
    "의자 찾아줘" → "의자", "이거 뭐야" → "" (확인 의도 → 빈 target)

    명령 동사/확인 패턴을 순서대로 제거하고 남은 것이 대상 물체.
    """
    verbs = [
        "찾아줘", "찾아", "어디있어", "어디 있어", "어디야",
        "어딘지", "어디에 있어", "어디에 있나", "있는지 알려줘",
        "뭔지 알려줘", "뭐야", "뭐지", "뭔지", "뭔데", "이거", "이게", "이건",
    ]
    label = text
    for v in sorted(verbs, key=len, reverse=True):  # 긴 패턴부터 제거 (부분 겹침 방지)
        label = label.replace(v, "")
    return label.strip()

@router.post("/tts", dependencies=[Depends(_verify_api_key)])
async def tts_endpoint(text: str = Form("")):
    from src.voice.tts import _cache_path, _generate
    import os
    if not text: return JSONResponse({"error": "text is empty"}, status_code=400)
    path = _cache_path(text)
    if not os.path.exists(path):
        if not _generate(text, path): return JSONResponse({"error": "TTS generation failed"}, status_code=500)
    return FileResponse(path, media_type="audio/wav")

@router.post("/gps", dependencies=[Depends(_verify_api_key)])
async def save_gps_ping(
    wifi_ssid: str = Form(""), device_id: str = Form(""),
    lat: float = Form(0.0), lng: float = Form(0.0), request_id: str = Form("")
):
    session_id = _normalize_session_id(wifi_ssid, device_id)
    if lat == 0.0 and lng == 0.0: return {"saved": False, "session_id": session_id, "reason": "empty_location"}
    db.save_gps(session_id, lat, lng)
    return {"saved": True, "session_id": session_id, "lat": lat, "lng": lng}

@router.get("/status/{session_id}", dependencies=[Depends(_verify_api_key)])
async def get_session_status(session_id: str):
    req_session_id = _normalize_session_id(session_id)
    gps = db.get_last_gps(req_session_id)
    tracker = get_tracker(req_session_id)
    current = tracker.get_current_state(max_age_s=5.0)
    if not current: current = db.get_snapshot(req_session_id, max_age_s=8.0) or []
    latest = db.get_latest_detection_event(req_session_id)
    return {
        "session_id": req_session_id,
        "objects": current,
        "gps": gps,
        "track": db.get_gps_track(req_session_id, limit=100),
        "latest_event": latest,
    }

@router.get("/events/{session_id}", dependencies=[Depends(_verify_api_key)])
async def stream_session_events(session_id: str):
    req_session_id = _normalize_session_id(session_id)

    async def event_stream():
        initial = await get_session_status(req_session_id)
        yield "event: status\n"
        yield f"data: {json.dumps(initial, ensure_ascii=False)}\n\n"
        async with events.subscribe(req_session_id) as queue:
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15)
                    yield "event: status\n"
                    yield f"data: {payload}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@router.get("/sessions", dependencies=[Depends(_verify_api_key)])
async def list_sessions():
    return {"sessions": db.get_recent_sessions()}

@router.get("/team-locations", dependencies=[Depends(_verify_api_key)])
async def get_team_locations():
    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(minutes=30)).isoformat()
    locations = []
    for s in db.get_recent_sessions(limit=20):
        gps = db.get_last_gps(s)
        if gps and gps.get("timestamp", "") >= cutoff:
            locations.append({"session_id": s, "lat": gps["lat"], "lng": gps["lng"]})
    return {"locations": locations}

@router.get("/dashboard", dependencies=[Depends(_verify_api_key)])
async def dashboard():
    from fastapi.responses import HTMLResponse
    tpl_path = os.path.join(os.path.dirname(__file__), "../../templates/dashboard.html")
    if os.path.exists(tpl_path):
        with open(tpl_path, encoding="utf-8") as f: return HTMLResponse(f.read())
    return HTMLResponse("<h1>dashboard.html not found</h1>", status_code=404)

@router.post("/spaces/snapshot", dependencies=[Depends(_verify_api_key)])
async def save_space_snapshot(body: dict):
    db.save_snapshot(body.get("space_id", ""), body.get("objects", []))
    return {"saved": True}

@router.post("/stt")
async def stt_listen():
    try:
        from src.voice.stt import listen_and_classify
        text, mode = listen_and_classify()
        return {"text": text, "mode": mode, "success": bool(text)}
    except Exception as e:
        return {"text": "", "mode": "unknown", "success": False, "error": str(e)}
