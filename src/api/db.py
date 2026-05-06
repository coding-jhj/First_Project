"""
VoiceGuide DB 모듈
==================
DATABASE_URL 환경변수 유무에 따라 자동 전환:
  - 없음 → SQLite (로컬, 파일 기반)
  - 있음 → PostgreSQL / Supabase (외부, LTE 접속 가능)

설정 방법:
  로컬: .env에 DATABASE_URL 없으면 자동으로 SQLite 사용
  외부: .env에 DATABASE_URL=postgresql://... 추가 (Supabase 연결 문자열)
        서버_DB/SUPABASE_DB_CONNECT_GUIDE.md 참고
"""

import os
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime

# ── 모드 결정 ─────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL")  # Supabase: postgresql://user:pass@host/db
DB_PATH      = "voiceguide.db"            # SQLite 로컬 파일
_IS_POSTGRES = bool(DATABASE_URL)

_pool = None  # PostgreSQL 커넥션 풀 (Supabase 모드에서만)


def _get_pool():
    global _pool
    if _pool is None:
        from psycopg_pool import ConnectionPool
        from psycopg.rows import dict_row
        _pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=5, open=True,
                               kwargs={"row_factory": dict_row})
    return _pool


@contextmanager
def _conn():
    """SQLite / PostgreSQL 구분 없이 사용하는 커넥션 컨텍스트."""
    if _IS_POSTGRES:
        with _get_pool().connection() as conn:
            yield conn
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


# ── DB 초기화 ─────────────────────────────────────────────────────────────────

def init_db():
    """앱 시작 시 테이블 생성. 이미 있으면 무시."""
    if _IS_POSTGRES:
        _init_postgres()
    else:
        _init_sqlite()
    mode = "PostgreSQL/Supabase" if _IS_POSTGRES else "SQLite"
    print(f"[DB] 초기화 완료 ({mode})")


def _init_sqlite():
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                space_id  TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                objects   TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS saved_locations (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                label     TEXT NOT NULL,
                wifi_ssid TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS gps_history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                lat        REAL NOT NULL,
                lng        REAL NOT NULL,
                timestamp  TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS detections (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id   TEXT    NOT NULL,
                session_id  TEXT    NOT NULL,
                request_id  TEXT    NOT NULL DEFAULT '',
                class_ko    TEXT    NOT NULL,
                confidence  REAL    NOT NULL,
                cx          REAL    NOT NULL,
                cy          REAL    NOT NULL,
                w           REAL    NOT NULL,
                h           REAL    NOT NULL,
                zone        TEXT    NOT NULL DEFAULT '12시',
                dist_m      REAL    NOT NULL DEFAULT 0.0,
                is_vehicle  INTEGER NOT NULL DEFAULT 0,
                is_animal   INTEGER NOT NULL DEFAULT 0,
                mode        TEXT    NOT NULL DEFAULT '장애물',
                lat         REAL    NOT NULL DEFAULT 0.0,
                lng         REAL    NOT NULL DEFAULT 0.0,
                detected_at TEXT    NOT NULL
            );
        """)


def _init_postgres():
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    id        BIGSERIAL PRIMARY KEY,
                    space_id  TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    objects   TEXT NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS saved_locations (
                    id        BIGSERIAL PRIMARY KEY,
                    label     TEXT NOT NULL,
                    wifi_ssid TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS gps_history (
                    id         BIGSERIAL PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    lat        DOUBLE PRECISION NOT NULL,
                    lng        DOUBLE PRECISION NOT NULL,
                    timestamp  TEXT NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS detections (
                    id          BIGSERIAL PRIMARY KEY,
                    device_id   TEXT             NOT NULL,
                    session_id  TEXT             NOT NULL,
                    request_id  TEXT             NOT NULL DEFAULT '',
                    class_ko    TEXT             NOT NULL,
                    confidence  DOUBLE PRECISION NOT NULL,
                    cx          DOUBLE PRECISION NOT NULL,
                    cy          DOUBLE PRECISION NOT NULL,
                    w           DOUBLE PRECISION NOT NULL,
                    h           DOUBLE PRECISION NOT NULL,
                    zone        TEXT             NOT NULL DEFAULT '12시',
                    dist_m      DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                    is_vehicle  BOOLEAN          NOT NULL DEFAULT FALSE,
                    is_animal   BOOLEAN          NOT NULL DEFAULT FALSE,
                    mode        TEXT             NOT NULL DEFAULT '장애물',
                    lat         DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                    lng         DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                    detected_at TEXT             NOT NULL
                )
            """)


# ── 공간 스냅샷 ───────────────────────────────────────────────────────────────

def get_snapshot(space_id: str, max_age_s: float | None = None) -> list[dict] | None:
    cutoff = None
    if max_age_s is not None:
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(seconds=max_age_s)).isoformat()
    with _conn() as conn:
        if _IS_POSTGRES:
            with conn.cursor() as cur:
                if cutoff:
                    cur.execute(
                        "SELECT objects FROM snapshots WHERE space_id = %s "
                        "AND timestamp > %s ORDER BY id DESC LIMIT 1", (space_id, cutoff))
                else:
                    cur.execute(
                        "SELECT objects FROM snapshots WHERE space_id = %s "
                        "ORDER BY id DESC LIMIT 1", (space_id,))
                row = cur.fetchone()
            return json.loads(row["objects"]) if row else None
        else:
            if cutoff:
                row = conn.execute(
                    "SELECT objects FROM snapshots WHERE space_id = ? "
                    "AND timestamp > ? ORDER BY id DESC LIMIT 1", (space_id, cutoff)).fetchone()
            else:
                row = conn.execute(
                    "SELECT objects FROM snapshots WHERE space_id = ? "
                    "ORDER BY id DESC LIMIT 1", (space_id,)).fetchone()
            return json.loads(row[0]) if row else None


_SNAPSHOT_KEEP = 20  # 공간별 스냅샷 최대 보관 수 (이 이상이면 오래된 것부터 삭제)


def save_snapshot(space_id: str, objects: list[dict]):
    ts  = datetime.now().isoformat()          # ISO 8601 형식 타임스탬프
    obj = json.dumps(objects, ensure_ascii=False)  # 한국어 유지하여 JSON 직렬화
    with _conn() as conn:
        if _IS_POSTGRES:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO snapshots (space_id, timestamp, objects) "
                    "VALUES (%s, %s, %s)", (space_id, ts, obj))
                # 공간별 최근 N개만 유지 (DB 무한 증가 방지)
                cur.execute(
                    "DELETE FROM snapshots WHERE space_id = %s AND id NOT IN "
                    "(SELECT id FROM snapshots WHERE space_id = %s "
                    " ORDER BY id DESC LIMIT %s)",
                    (space_id, space_id, _SNAPSHOT_KEEP))
        else:
            conn.execute(
                "INSERT INTO snapshots (space_id, timestamp, objects) "
                "VALUES (?, ?, ?)", (space_id, ts, obj))
            # 공간별 최근 N개만 유지 (DB 무한 증가 방지)
            conn.execute(
                "DELETE FROM snapshots WHERE space_id = ? AND id NOT IN "
                "(SELECT id FROM snapshots WHERE space_id = ? "
                " ORDER BY id DESC LIMIT ?)",
                (space_id, space_id, _SNAPSHOT_KEEP))


# ── 개인 장소 저장 ────────────────────────────────────────────────────────────

def save_location(label: str, wifi_ssid: str):
    ts = datetime.now().isoformat()
    with _conn() as conn:
        if _IS_POSTGRES:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO saved_locations (label, wifi_ssid, timestamp) "
                    "VALUES (%s, %s, %s)", (label, wifi_ssid, ts))
        else:
            conn.execute(
                "INSERT INTO saved_locations (label, wifi_ssid, timestamp) "
                "VALUES (?, ?, ?)", (label, wifi_ssid, ts))


def delete_location(label: str):
    with _conn() as conn:
        if _IS_POSTGRES:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM saved_locations WHERE label = %s", (label,))
        else:
            conn.execute(
                "DELETE FROM saved_locations WHERE label = ?", (label,))


def get_locations(wifi_ssid: str = "") -> list[dict]:
    with _conn() as conn:
        if _IS_POSTGRES:
            with conn.cursor() as cur:
                if wifi_ssid:
                    cur.execute(
                        "SELECT label, wifi_ssid, timestamp FROM saved_locations "
                        "WHERE wifi_ssid = %s ORDER BY id DESC", (wifi_ssid,))
                else:
                    cur.execute(
                        "SELECT label, wifi_ssid, timestamp FROM saved_locations "
                        "ORDER BY id DESC")
                rows = cur.fetchall()
            return [{"label": r["label"], "wifi_ssid": r["wifi_ssid"],
                     "timestamp": r["timestamp"]} for r in rows]
        else:
            if wifi_ssid:
                rows = conn.execute(
                    "SELECT label, wifi_ssid, timestamp FROM saved_locations "
                    "WHERE wifi_ssid = ? ORDER BY id DESC", (wifi_ssid,)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT label, wifi_ssid, timestamp FROM saved_locations "
                    "ORDER BY id DESC").fetchall()
            return [{"label": r[0], "wifi_ssid": r[1], "timestamp": r[2]}
                    for r in rows]


def find_location(label: str) -> dict | None:
    with _conn() as conn:
        if _IS_POSTGRES:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT label, wifi_ssid, timestamp FROM saved_locations "
                    "WHERE label LIKE %s ORDER BY id DESC LIMIT 1",
                    (f"%{label}%",))
                row = cur.fetchone()
            return {"label": row["label"], "wifi_ssid": row["wifi_ssid"],
                    "timestamp": row["timestamp"]} if row else None
        else:
            row = conn.execute(
                "SELECT label, wifi_ssid, timestamp FROM saved_locations "
                "WHERE label LIKE ? ORDER BY id DESC LIMIT 1",
                (f"%{label}%",)).fetchone()
            return {"label": row[0], "wifi_ssid": row[1],
                    "timestamp": row[2]} if row else None


# ── GPS 위치 이력 ─────────────────────────────────────────────────────────────

def save_gps(session_id: str, lat: float, lng: float):
    ts = datetime.now().isoformat()
    with _conn() as conn:
        if _IS_POSTGRES:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO gps_history (session_id, lat, lng, timestamp) "
                    "VALUES (%s, %s, %s, %s)", (session_id, lat, lng, ts))
                cur.execute(
                    "DELETE FROM gps_history WHERE session_id = %s AND id NOT IN "
                    "(SELECT id FROM gps_history WHERE session_id = %s "
                    " ORDER BY id DESC LIMIT 200)",
                    (session_id, session_id))
        else:
            conn.execute(
                "INSERT INTO gps_history (session_id, lat, lng, timestamp) "
                "VALUES (?, ?, ?, ?)", (session_id, lat, lng, ts))
            conn.execute(
                "DELETE FROM gps_history WHERE session_id = ? AND id NOT IN "
                "(SELECT id FROM gps_history WHERE session_id = ? "
                " ORDER BY id DESC LIMIT 200)",
                (session_id, session_id))


def get_last_gps(session_id: str) -> dict | None:
    with _conn() as conn:
        if _IS_POSTGRES:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT lat, lng, timestamp FROM gps_history "
                    "WHERE session_id = %s ORDER BY id DESC LIMIT 1",
                    (session_id,))
                row = cur.fetchone()
            return {"lat": row["lat"], "lng": row["lng"],
                    "timestamp": row["timestamp"]} if row else None
        else:
            row = conn.execute(
                "SELECT lat, lng, timestamp FROM gps_history "
                "WHERE session_id = ? ORDER BY id DESC LIMIT 1",
                (session_id,)).fetchone()
            return {"lat": row[0], "lng": row[1],
                    "timestamp": row[2]} if row else None


def get_recent_sessions(limit: int = 10) -> list[str]:
    """GPS 데이터가 있는 최근 세션 ID 목록 반환 (대시보드 세션 선택용)."""
    with _conn() as conn:
        if _IS_POSTGRES:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT session_id FROM gps_history "
                    "GROUP BY session_id "
                    "ORDER BY MAX(id) DESC LIMIT %s", (limit,))
                rows = cur.fetchall()
            return [r["session_id"] for r in rows]
        else:
            rows = conn.execute(
                "SELECT session_id FROM gps_history "
                "GROUP BY session_id "
                "ORDER BY MAX(id) DESC LIMIT ?", (limit,)).fetchall()
            return [r[0] for r in rows]


def get_latest_session() -> str | None:
    """가장 최근 GPS를 보낸 세션 ID 반환."""
    sessions = get_recent_sessions(limit=1)
    return sessions[0] if sessions else None


# ── 온디바이스 탐지 결과 저장 ─────────────────────────────────────────────────

_DETECTIONS_KEEP = 500  # 세션별 최대 보관 수

def save_detections(
    device_id: str,
    session_id: str,
    request_id: str,
    detections: list[dict],
    mode: str = "장애물",
    lat: float = 0.0,
    lng: float = 0.0,
) -> None:
    """폰에서 온 탐지 결과 리스트를 DB에 저장."""
    if not detections:
        return
    ts = datetime.now().isoformat()
    with _conn() as conn:
        for d in detections:
            if _IS_POSTGRES:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO detections "
                        "(device_id, session_id, request_id, class_ko, confidence, "
                        " cx, cy, w, h, zone, dist_m, is_vehicle, is_animal, "
                        " mode, lat, lng, detected_at) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (device_id, session_id, request_id,
                         d.get("class_ko",""), d.get("confidence", 0.0),
                         d.get("cx", 0.0), d.get("cy", 0.0),
                         d.get("w", 0.0),  d.get("h", 0.0),
                         d.get("zone","12시"), d.get("dist_m", 0.0),
                         d.get("is_vehicle", False), d.get("is_animal", False),
                         mode, lat, lng, ts),
                    )
                    cur.execute(
                        "DELETE FROM detections WHERE session_id = %s AND id NOT IN "
                        "(SELECT id FROM detections WHERE session_id = %s "
                        " ORDER BY id DESC LIMIT %s)",
                        (session_id, session_id, _DETECTIONS_KEEP),
                    )
            else:
                conn.execute(
                    "INSERT INTO detections "
                    "(device_id, session_id, request_id, class_ko, confidence, "
                    " cx, cy, w, h, zone, dist_m, is_vehicle, is_animal, "
                    " mode, lat, lng, detected_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (device_id, session_id, request_id,
                     d.get("class_ko",""), d.get("confidence", 0.0),
                     d.get("cx", 0.0), d.get("cy", 0.0),
                     d.get("w", 0.0),  d.get("h", 0.0),
                     d.get("zone","12시"), d.get("dist_m", 0.0),
                     int(d.get("is_vehicle", False)), int(d.get("is_animal", False)),
                     mode, lat, lng, ts),
                )
        if not _IS_POSTGRES:
            conn.execute(
                "DELETE FROM detections WHERE session_id = ? AND id NOT IN "
                "(SELECT id FROM detections WHERE session_id = ? "
                " ORDER BY id DESC LIMIT ?)",
                (session_id, session_id, _DETECTIONS_KEEP),
            )


def get_recent_detections(session_id: str, max_age_s: float = 3.0) -> list[dict]:
    """최근 N초 이내 탐지 결과 반환 — 질문 응답 및 tracker 복원용."""
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(seconds=max_age_s)).isoformat()
    with _conn() as conn:
        if _IS_POSTGRES:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT class_ko, confidence, cx, cy, w, h, zone, dist_m, "
                    "       is_vehicle, is_animal, detected_at "
                    "FROM detections WHERE session_id = %s AND detected_at > %s "
                    "ORDER BY id DESC LIMIT 100",
                    (session_id, cutoff),
                )
                rows = cur.fetchall()
            return [dict(r) for r in rows]
        else:
            rows = conn.execute(
                "SELECT class_ko, confidence, cx, cy, w, h, zone, dist_m, "
                "       is_vehicle, is_animal, detected_at "
                "FROM detections WHERE session_id = ? AND detected_at > ? "
                "ORDER BY id DESC LIMIT 100",
                (session_id, cutoff),
            ).fetchall()
            keys = ["class_ko","confidence","cx","cy","w","h",
                    "zone","dist_m","is_vehicle","is_animal","detected_at"]
            return [dict(zip(keys, r)) for r in rows]


def get_gps_track(session_id: str, limit: int = 100) -> list[dict]:
    """대시보드 지도에 표시할 이동 경로 포인트 목록 반환."""
    with _conn() as conn:
        if _IS_POSTGRES:
            with conn.cursor() as cur:
                # DESC로 최신 100개 조회 후 reversed()로 시간순 정렬
                cur.execute(
                    "SELECT lat, lng, timestamp FROM gps_history "
                    "WHERE session_id = %s ORDER BY id DESC LIMIT %s",
                    (session_id, limit))
                rows = cur.fetchall()
            result = [{"lat": r["lat"], "lng": r["lng"],
                       "timestamp": r["timestamp"]} for r in rows]
        else:
            rows = conn.execute(
                "SELECT lat, lng, timestamp FROM gps_history "
                "WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit)).fetchall()
            result = [{"lat": r[0], "lng": r[1], "timestamp": r[2]}
                      for r in rows]
    return list(reversed(result))  # 시간순 오름차순 반환 (지도 경로 그리기 위해)
