"""
VoiceGuide FastAPI 라우터
===========================
Android 앱과 Gradio 데모가 호출하는 API 엔드포인트를 정의합니다.

주요 엔드포인트:
  POST /detect           — 이미지 분석 (장애물/찾기/확인/저장/위치목록 5가지 모드)
  POST /locations/save   — 장소 저장
  GET  /locations        — 저장 장소 목록
  GET  /locations/find/{label} — 장소 검색
  DELETE /locations/{label}   — 장소 삭제
  POST /stt              — PC 마이크 음성 인식 (Gradio 데모용)

설계 원칙:
  - 모든 엔드포인트는 반드시 sentence 필드를 반환 → TTS로 바로 읽을 수 있음
  - 오류가 나도 음성 안내가 나오도록 전역 예외 핸들러 적용 (main.py)
  - 이미지가 필요 없는 모드(저장/위치목록)는 빠르게 처리하고 반환
"""

import asyncio
import os
import uuid
import hashlib
import json
from datetime import datetime

from fastapi import APIRouter, Depends, UploadFile, Form, Header, HTTPException, Response
from fastapi.responses import FileResponse, JSONResponse

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

from src.depth.depth import detect_and_depth
from src.nlg.sentence import (
    build_sentence, build_find_sentence,
    build_question_sentence, build_held_sentence,
    get_alert_mode, _i_ga, _un_neun,
)
from src.api import db
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
_DEDUP_SECS = 5.0

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

@router.post("/detect", dependencies=[Depends(_verify_api_key)])
async def detect(
    image:              UploadFile,
    wifi_ssid:          str   = Form(""),
    device_id:          str   = Form(""),
    camera_orientation: str   = Form("front"),
    mode:               str   = Form("장애물"),
    query_text:         str   = Form(""),
    lat:                float = Form(0.0),
    lng:                float = Form(0.0),
    request_id:         str   = Form(""),
):
    _t0 = _time.monotonic()
    request_id = request_id or f"srv-{int(_t0 * 1000)}"
    session_id = _normalize_session_id(wifi_ssid, device_id)
    
    image_bytes = await image.read()

    if lat != 0.0 or lng != 0.0:
        db.save_gps(session_id, lat, lng)

    _t_detect = _time.monotonic()
    loop = asyncio.get_event_loop()
    objects, hazards, scene = await loop.run_in_executor(None, detect_and_depth, image_bytes)
    _detect_ms = int((_time.monotonic() - _t_detect) * 1000)

    _t_tracker = _time.monotonic()
    tracker = get_tracker(session_id)
    objects, motion_changes = tracker.update(objects)
    _tracker_ms = int((_time.monotonic() - _t_tracker) * 1000)

    previous = db.get_snapshot(wifi_ssid)
    space_changes = _space_changes(objects, previous) if previous and objects else []
    if objects:
        db.save_snapshot(wifi_ssid, objects)
        db.save_snapshot(session_id, objects)

    all_changes = motion_changes + space_changes

    if mode == "들고있는것":
        sentence = build_held_sentence(objects)
        return _with_perf({
            "mode": mode, "sentence": sentence, "alert_mode": "critical",
            "objects": objects, "hazards": hazards, "changes": motion_changes,
            "depth_source": objects[0].get("depth_source", "bbox") if objects else "bbox",
        }, _t0, request_id, _detect_ms, _tracker_ms)

    if mode == "질문":
        tracked = tracker.get_current_state(max_age_s=3.0)
        sentence = build_question_sentence(objects, hazards, scene, tracked, camera_orientation)
        alert_mode = get_alert_mode(objects[0], is_hazard=bool(hazards)) if objects else ("critical" if hazards else "silent")
        return _with_perf({
            "mode": mode, "sentence": sentence, "alert_mode": alert_mode,
            "objects": objects, "hazards": hazards, "changes": motion_changes,
            "scene": scene, "tracked": tracked,
            "depth_source": objects[0].get("depth_source", "bbox") if objects else "bbox",
        }, _t0, request_id, _detect_ms, _tracker_ms)

    if mode == "찾기":
        target = _extract_find_target(query_text)
        sentence = build_find_sentence(target, objects, camera_orientation)
        return _with_perf({
            "mode": mode, "sentence": sentence, "alert_mode": "critical",
            "objects": objects, "hazards": hazards, "changes": all_changes,
            "depth_source": objects[0].get("depth_source", "bbox") if objects else "bbox",
        }, _t0, request_id, _detect_ms, _tracker_ms)

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

    return _with_perf({
        "mode": mode, "sentence": sentence, "alert_mode": alert_mode,
        "objects": objects, "hazards": hazards, "changes": all_changes, "scene": scene,
        "depth_source": objects[0].get("depth_source", "bbox") if objects else "bbox",
    }, _t0, request_id, _detect_ms, _tracker_ms)

def _extract_find_target(text: str) -> str:
    verbs = ["찾아줘", "찾아", "어디있어", "어디 있어", "어디야", "어딘지", "어디에 있어", "어디에 있나", "있는지 알려줘"]
    label = text
    for v in verbs: label = label.replace(v, "")
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
    return {"session_id": req_session_id, "objects": current, "gps": gps, "track": db.get_gps_track(req_session_id, limit=100)}

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
