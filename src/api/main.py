from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.api.routes import router
from src.api import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시: DB 초기화 + YOLO + Depth V2 워밍업
    db.init_db()
    import numpy as np
    from src.vision.detect import model, CONF_THRESHOLD
    model(np.zeros((640, 640, 3), dtype=np.uint8), conf=CONF_THRESHOLD, verbose=False)
    # Depth V2 모델 미리 로드 — 안 하면 첫 /detect 요청에서 10~30초 걸려 Android timeout 발생
    from src.depth.depth import _load_model
    _load_model()
    # EasyOCR·TTS 워밍업: 느려도 무관하므로 백그라운드 스레드
    import threading
    threading.Thread(target=_warmup_ocr, daemon=True).start()
    threading.Thread(target=_warmup_tts, daemon=True).start()
    yield


def _warmup_ocr():
    try:
        from src.ocr.bus_ocr import warmup
        warmup()
    except Exception as e:
        print(f"[main] EasyOCR 워밍업 실패: {e}")


def _warmup_tts():
    try:
        from src.voice.tts import warmup_cache
        warmup_cache()
    except Exception:
        pass  # TTS 워밍업 실패해도 서버 동작에 영향 없음 (첫 요청 시 자동 생성)


app = FastAPI(title="VoiceGuide API", lifespan=lifespan)

# CORS: 대시보드 브라우저 접속을 위해 필요
# ALLOWED_ORIGINS 환경변수로 제한 가능 (기본: 개발용 전체 허용)
# 예) ALLOWED_ORIGINS=https://myapp.ngrok-free.app,http://localhost:8000
_origins = os.getenv("ALLOWED_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _origins == "*" else _origins.split(","),
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """서버 상태 + Depth V2 모델 로드 여부 + DB 연결 확인."""
    from src.depth.depth import _check_model, _DEVICE
    depth_ok = _check_model()
    db_status = _check_db()
    overall = "ok" if db_status == "ok" else "degraded"
    return {
        "status":   overall,
        "depth_v2": "loaded" if depth_ok else "fallback (bbox)",
        "device":   _DEVICE,
        "db_mode":  "postgresql" if db._IS_POSTGRES else "sqlite",
        "db":       db_status,
    }


def _check_db() -> str:
    """DB에 간단한 쿼리를 날려 연결 상태를 확인한다."""
    try:
        from src.api.db import _conn, _IS_POSTGRES
        with _conn() as conn:
            if _IS_POSTGRES:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            else:
                conn.execute("SELECT 1")
        return "ok"
    except Exception as e:
        return f"error: {e}"


# 예외가 나도 Android가 음성 안내를 받을 수 있도록 안전 응답 반환
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "sentence": "분석 중 오류가 발생했어요. 주의해서 이동하세요.",
            "objects": [],
            "hazards": [],
            "changes": [],
            "depth_source": "error",
        }
    )


app.include_router(router)
