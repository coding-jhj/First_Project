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
from datetime import datetime

from fastapi import APIRouter, Depends, UploadFile, Form, Header, HTTPException
from fastapi.responses import FileResponse

# ── API Key 인증 ────────────────────────────────────────────────────────────
# .env에 API_KEY=비밀값 설정 시 민감 API 요청에 Authorization: Bearer <키> 또는 X-API-Key 필요
# API_KEY 미설정 시 인증 없음 (로컬 개발 모드)
_API_KEY = os.getenv("API_KEY", "")

def _verify_api_key(
    authorization: str = Header(default=""),
    x_api_key: str = Header(default=""),
) -> None:
    if not _API_KEY:
        return  # 키 미설정 = 개발 모드, 인증 건너뜀
    if authorization == f"Bearer {_API_KEY}" or x_api_key == _API_KEY:
        return
    raise HTTPException(status_code=401, detail="Invalid or missing API key")
from src.depth.depth import detect_and_depth
from src.nlg.sentence import (
    build_sentence, build_hazard_sentence, build_find_sentence,
    build_question_sentence, build_held_sentence,
    get_alert_mode, _i_ga, _un_neun,
)
from src.api import db
from src.api.tracker import get_tracker

router = APIRouter()

# ── 세션별 마지막 문장 캐시 (TTS 중복 방지) ────────────────────────────────────
# 같은 세션에서 동일 문장이 5초 이내에 반복되면 alert_mode를 "silent"로 내려보냄
# → Android에서 TTS를 새로 재생하지 않음 (UI 업데이트만)
# "critical" 수준 (차량·계단)은 항상 통과
import time as _time
_last_sentence: dict[str, tuple[str, float]] = {}  # session_id → (sentence, timestamp)
_DEDUP_SECS = 5.0   # 같은 문장 억제 시간


def _normalize_session_id(wifi_ssid: str = "", device_id: str = "") -> str:
    """기기별 대시보드 세션 ID 정규화. device_id가 있으면 WiFi보다 우선한다."""
    preferred = device_id or wifi_ssid
    value = (preferred or "").strip().strip('"')
    if not value or value.lower() in {"<unknown ssid>", "unknown ssid", "0x"}:
        return "__default__"
    return value


def _with_perf(
    payload: dict,
    t0: float,
    request_id: str,
    detect_ms: int = 0,
    tracker_ms: int = 0,
) -> dict:
    """Android/더미 클라이언트가 서버 연동을 검증할 수 있게 공통 성능 필드 추가."""
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
    print(
        f"[LINK] request_id={request_id} mode={payload.get('mode', '')} "
        f"sentence={payload.get('sentence', '')[:40]!r}"
    )
    print(
        f"[PERF] request_id={request_id} detect={detect_ms}ms | "
        f"tracker={tracker_ms}ms | nlg+rest={nlg_ms}ms | "
        f"TOTAL={process_ms}ms | objs={len(payload.get('objects', []))}"
    )
    return payload

def _should_suppress(session_id: str, sentence: str, alert_mode: str) -> bool:
    """같은 문장이 최근 N초 내에 이미 전달됐으면 억제 여부 반환."""
    if alert_mode == "critical":  # 위험 경고는 항상 발화
        _last_sentence[session_id] = (sentence, _time.monotonic())
        return False
    prev_sentence, prev_ts = _last_sentence.get(session_id, ("", 0.0))
    if sentence == prev_sentence and (_time.monotonic() - prev_ts) < _DEDUP_SECS:
        return True  # 억제
    _last_sentence[session_id] = (sentence, _time.monotonic())
    return False


def _space_changes(current: list[dict], previous: list[dict]) -> list[str]:
    """
    이번 프레임과 이전 스냅샷을 비교해서 달라진 물체를 찾는 함수.

    새로 생긴 물체: curr에 있고 prev에 없는 것 → "의자가 생겼어요"
    사라진 물체:   prev에 있고 curr에 없는 것 → "사람이 없어졌어요"

    공간 기억 기능의 핵심: 재방문 시 매번 같은 설명을 반복하지 않기 위함.
    WiFi SSID가 공간 ID 역할 → 같은 공간에 다시 왔을 때만 비교 가능.
    """
    prev_set = {o["class_ko"] for o in previous}  # 이전 방문 물체 집합
    curr_set = {o["class_ko"] for o in current}   # 현재 물체 집합

    changes = []
    for name in curr_set - prev_set:  # 새로 생긴 것
        changes.append(f"{name}{_i_ga(name)} 생겼어요")
    for name in prev_set - curr_set:  # 사라진 것
        changes.append(f"{name}{_i_ga(name)} 없어졌어요")
    return changes


@router.post("/detect", dependencies=[Depends(_verify_api_key)])
async def detect(
    image:              UploadFile,
    wifi_ssid:          str   = Form(""),        # 공간 기억 + 장소 저장에 사용
    device_id:          str   = Form(""),        # 앱 설치별 고유 세션 ID (대시보드 위치 분리)
    camera_orientation: str   = Form("front"),   # 방향 보정: front/back/left/right
    mode:               str   = Form("장애물"),  # STT가 결정한 모드
    query_text:         str   = Form(""),        # STT 원문 (찾기/저장 모드에서 추출에 사용)
    lat:                float = Form(0.0),       # GPS 위도 (대시보드 지도용)
    lng:                float = Form(0.0),       # GPS 경도 (대시보드 지도용)
    request_id:         str   = Form(""),        # 클라이언트-서버 로그 상관관계 확인용
):
    """
    VoiceGuide 메인 분석 API.

    mode에 따라 처리 경로가 달라집니다:
      "저장"     → 이미지 불필요, 즉시 장소 저장 후 반환
      "위치목록" → 이미지 불필요, DB에서 장소 목록 반환
      나머지     → 이미지 분석 (YOLO + Depth V2 + 문장 생성)
    """

    _t0 = _time.monotonic()
    request_id = request_id or f"srv-{int(_t0 * 1000)}"
    session_id = _normalize_session_id(wifi_ssid, device_id)
    print(
        f"[LINK] request_id={request_id} START mode={mode} "
        f"session={session_id} lat={lat} lng={lng}"
    )

    # 저장/위치목록 모드는 실험 기능으로 제거됨 (개인 네비게이팅 기능 비활성화)

    # ── 이미지 분석 공통 흐름 (장애물/찾기/확인/질문 모드) ───────────────────
    image_bytes = await image.read()  # multipart form에서 이미지 바이트 추출

    # GPS 위치 기록 (대시보드 지도 표시용) — 좌표가 있을 때만 저장
    if lat != 0.0 or lng != 0.0:
        db.save_gps(session_id, lat, lng)

    # YOLO 탐지 + Depth V2 거리 추정 + 바닥 위험 감지
    # run_in_executor: CPU-bound 작업을 별도 스레드에서 실행 → FastAPI 이벤트 루프 차단 방지
    # 동시 요청이 들어와도 다른 요청을 처리할 수 있음 (Phase 8 - STUDENT_DEVELOPMENT_GUIDELINE)
    _t_detect = _time.monotonic()
    loop = asyncio.get_event_loop()
    objects, hazards, scene = await loop.run_in_executor(None, detect_and_depth, image_bytes)
    _detect_ms = int((_time.monotonic() - _t_detect) * 1000)

    # EMA 추적기: 프레임 간 거리 흔들림 제거 + 접근 감지
    _t_tracker = _time.monotonic()
    tracker = get_tracker(session_id)
    objects, motion_changes = tracker.update(objects)
    _tracker_ms = int((_time.monotonic() - _t_tracker) * 1000)

    # 공간 기억: 이전 방문과 비교해서 달라진 것 감지
    previous = db.get_snapshot(wifi_ssid)
    # 빈 프레임을 이전 공간 스냅샷과 비교하면 앱 시작 직후
    # "마우스가 사라졌어요" 같은 stale 안내가 나올 수 있다.
    space_changes = _space_changes(objects, previous) if previous and objects else []
    if objects:
        db.save_snapshot(wifi_ssid, objects)  # 현재 상태를 다음 방문을 위해 저장
    if objects:  # 빈 결과로 유효 스냅샷 덮어쓰지 않도록
        db.save_snapshot(session_id, objects)

    all_changes = motion_changes + space_changes

    # ── 들고있는것 모드: 손에 든 / 바로 앞 물건 식별 ─────────────────────────
    if mode == "들고있는것":
        sentence = build_held_sentence(objects)
        alert_mode = "critical"
        return _with_perf({
            "mode": mode,
            "sentence":    sentence,
            "alert_mode":  alert_mode,
            "objects":     objects,
            "hazards":     hazards,
            "changes":     motion_changes,
            "depth_source": objects[0].get("depth_source", "bbox") if objects else "bbox",
        }, _t0, request_id, _detect_ms, _tracker_ms)

    # ── 질문 모드: 사용자가 직접 "지금 뭐가 있어?" 물었을 때 즉시 응답 ──────
    # 핵심 버그 수정: 기존엔 질문해도 periodic capture를 기다렸음.
    # 이제 tracker에 누적된 최근 상태 + 현재 프레임을 합쳐 즉시 응답.
    if mode == "질문":
        tracked = tracker.get_current_state(max_age_s=3.0)
        sentence = build_question_sentence(objects, hazards, scene, tracked, camera_orientation)
        alert_mode = get_alert_mode(objects[0], is_hazard=bool(hazards)) if objects else (
            "critical" if hazards else "silent"
        )
        return _with_perf({
            "mode": mode,
            "sentence":    sentence,
            "alert_mode":  alert_mode,
            "objects":     objects,
            "hazards":     hazards,
            "changes":     motion_changes,
            "scene":       scene,
            "tracked":     tracked,
            "depth_source": objects[0].get("depth_source", "bbox") if objects else "bbox",
        }, _t0, request_id, _detect_ms, _tracker_ms)

    # ── 찾기 모드: 특정 물체를 타깃으로 탐색 ────────────────────────────────
    if mode == "찾기":
        target = _extract_find_target(query_text)  # "의자 찾아줘" → "의자"
        sentence = build_find_sentence(target, objects, camera_orientation)
        return _with_perf({
            "mode": mode,
            "sentence":    sentence,
            "alert_mode":  "critical",  # 사용자가 명시적으로 요청한 것 → 항상 즉각 안내
            "objects":     objects,
            "hazards":     hazards,
            "changes":     all_changes,
            "depth_source": objects[0].get("depth_source", "bbox") if objects else "bbox",
        }, _t0, request_id, _detect_ms, _tracker_ms)

    # ── 장애물/확인 모드: 위험도 기반 문장 생성 ──────────────────────────────
    if hazards:
        # 계단·낙차·턱이 감지되면 최우선 안내 (YOLO 결과보다 우선)
        top_hazard = max(hazards, key=lambda h: h.get("risk", 0))
        sentence   = build_hazard_sentence(top_hazard, objects, all_changes, camera_orientation)
        alert_mode = get_alert_mode(objects[0], is_hazard=True) if objects else "critical"
    else:
        sentence   = build_sentence(objects, all_changes, camera_orientation=camera_orientation)
        # risk_score 1위 객체 기준으로 알림 모드 결정
        # "silent"이면 프론트엔드는 TTS 호출 안 함, "beep"이면 비프음만 재생
        alert_mode = get_alert_mode(objects[0]) if objects else "silent"

    # 부가 경고 추가: 위험 물체·점자블록·군중·신호등·안전경로
    # 메인 문장 뒤에 붙임 (있을 때만)
    extras = [v for v in [
        scene.get("danger_warning"),        # 칼·가위 3m 이내 즉시 경고
        scene.get("slippery_warning"),      # 바닥 음식류 미끄럼 위험
        scene.get("tactile_block_warning"), # 점자 블록 위 장애물
        scene.get("crowd_warning"),         # 군중 밀집 경고
        scene.get("safe_direction"),        # 안전 경로 제안
        scene.get("traffic_light_msg"),     # 신호등 빨강/초록
    ] if v]
    if extras:
        sentence = sentence + " " + " ".join(extras)

    # 같은 문장이 5초 이내에 이미 전달됐으면 alert_mode를 "silent"로 낮춤 (TTS 겹침 방지)
    if _should_suppress(session_id, sentence, alert_mode):
        alert_mode = "silent"

    return _with_perf({
        "mode": mode,
        "sentence":      sentence,
        "alert_mode":    alert_mode,
        "objects":       objects,
        "hazards":       hazards,
        "changes":       all_changes,
        "scene":         scene,
        "depth_source":  objects[0].get("depth_source", "bbox") if objects else "bbox",
    }, _t0, request_id, _detect_ms, _tracker_ms)


def _extract_find_target(text: str) -> str:
    """
    찾기 명령어에서 대상 물체 이름 추출.
    "의자 찾아줘" → "의자"
    "가방 어디있어" → "가방"

    명령 동사 패턴을 순서대로 제거하고 남은 것이 대상 물체.
    """
    verbs = ["찾아줘", "찾아", "어디있어", "어디 있어", "어디야",
             "어딘지", "어디에 있어", "어디에 있나", "있는지 알려줘"]
    label = text
    for v in verbs:
        label = label.replace(v, "")
    return label.strip()


# ── 장소 저장/조회 전용 엔드포인트 ───────────────────────────────────────────
# Android MainActivity에서 직접 호출 가능 (detect API 거치지 않고 빠르게 처리)

@router.post("/tts", dependencies=[Depends(_verify_api_key)])
async def tts_endpoint(text: str = Form("")):
    """ElevenLabs / gTTS — 텍스트를 음성 파일(MP3)로 변환해 Android 앱에 반환.
    API 키 없으면 gTTS로 자동 폴백."""
    from src.voice.tts import _cache_path, _generate
    from fastapi.responses import JSONResponse
    import os
    if not text:
        return JSONResponse({"error": "text is empty"}, status_code=400)
    path = _cache_path(text)
    if not os.path.exists(path):
        if not _generate(text, path):
            return JSONResponse({"error": "TTS generation failed"}, status_code=500)
    return FileResponse(path, media_type="audio/mpeg")


# /ocr/bus 엔드포인트 제거 — 버스 번호 OCR 실험 기능 비활성화
# /vision/clothing 엔드포인트 제거 — 옷 매칭·패턴 분석 기능 제거


# 개인 네비게이팅 엔드포인트 (/locations/*) 제거 — 실험 기능 비활성화


@router.post("/gps", dependencies=[Depends(_verify_api_key)])
async def save_gps_ping(
    wifi_ssid:  str   = Form(""),
    device_id:  str   = Form(""),
    lat:        float = Form(0.0),
    lng:        float = Form(0.0),
    request_id: str   = Form(""),
):
    """Android 온디바이스 모드에서도 대시보드가 위치를 받을 수 있게 GPS만 저장."""
    session_id = _normalize_session_id(wifi_ssid, device_id)
    if lat == 0.0 and lng == 0.0:
        print(f"[GPS] ignored empty location request_id={request_id} session={session_id}")
        return {"saved": False, "session_id": session_id, "reason": "empty_location"}
    db.save_gps(session_id, lat, lng)
    print(f"[GPS] saved request_id={request_id} session={session_id} lat={lat} lng={lng}")
    return {"saved": True, "session_id": session_id, "lat": lat, "lng": lng}


@router.get("/status/{session_id}", dependencies=[Depends(_verify_api_key)])
async def get_session_status(session_id: str):
    """
    세션(WiFi SSID)의 현재 추적 상태 반환 — 대시보드 폴링용.
    최근 3초 이내에 탐지된 물체 목록과 마지막 GPS 좌표를 반환.
    """
    requested_session_id = _normalize_session_id(session_id)
    resolved_session_id = requested_session_id

    gps = db.get_last_gps(resolved_session_id)

    tracker = get_tracker(resolved_session_id)
    current = tracker.get_current_state(max_age_s=5.0)
    # in-memory tracker 비어 있으면 DB 스냅샷 폴백 (Cloud Run 다중 인스턴스 / 서버 재시작 대비)
    if not current:
        current = db.get_snapshot(resolved_session_id, max_age_s=8.0) or []
    track   = db.get_gps_track(resolved_session_id, limit=100)
    return {
        "session_id": resolved_session_id,
        "requested_session_id": requested_session_id,
        "objects":    current,
        "gps":        gps,
        "track":      track,
    }


@router.get("/sessions", dependencies=[Depends(_verify_api_key)])
async def list_sessions():
    """GPS 데이터가 있는 최근 세션 ID 목록 반환 — 대시보드 세션 선택용."""
    return {"sessions": db.get_recent_sessions()}


@router.get("/team-locations", dependencies=[Depends(_verify_api_key)])
async def get_team_locations():
    """최근 30분 내 활성 세션의 마지막 GPS 반환 — 대시보드 팀원 위치 표시용."""
    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(minutes=30)).isoformat()
    sessions = db.get_recent_sessions(limit=20)
    locations = []
    for s in sessions:
        gps = db.get_last_gps(s)
        if gps and gps.get("timestamp", "") >= cutoff:
            locations.append({"session_id": s, "lat": gps["lat"], "lng": gps["lng"]})
    return {"locations": locations}


@router.get("/dashboard", dependencies=[Depends(_verify_api_key)])
async def dashboard():
    """대시보드 HTML 페이지 반환."""
    from fastapi.responses import HTMLResponse
    import os
    tpl_path = os.path.join(os.path.dirname(__file__), "../../templates/dashboard.html")
    if os.path.exists(tpl_path):
        with open(tpl_path, encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>dashboard.html not found</h1>", status_code=404)


@router.post("/spaces/snapshot", dependencies=[Depends(_verify_api_key)])
async def save_space_snapshot(body: dict):
    """공간 스냅샷 수동 저장 (테스트·디버깅용)."""
    space_id = body.get("space_id", "")
    objects  = body.get("objects", [])
    db.save_snapshot(space_id, objects)
    return {"saved": True}


@router.post("/stt")
async def stt_listen():
    """
    PC 마이크로 음성 인식 — Gradio 데모 전용.
    Android 앱은 SpeechRecognizer 내장 API를 직접 사용하므로 이 엔드포인트 호출 안 함.
    """
    try:
        from src.voice.stt import listen_and_classify
        text, mode = listen_and_classify()
        return {"text": text, "mode": mode, "success": bool(text)}
    except Exception as e:
        return {"text": "", "mode": "unknown", "success": False, "error": str(e)}
