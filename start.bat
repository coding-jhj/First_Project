@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ============================================
echo   VoiceGuide 서버 + ngrok 한 번에 시작
echo ============================================
echo.

REM ── FastAPI 서버 ──────────────────────────────────────────────────────────
REM conda 있으면 ai_env 환경으로, 없으면 기본 Python으로 실행
where conda >nul 2>&1
if %errorlevel%==0 (
    REM conda run -n: 쉘 활성화 없이 환경 지정 실행 (conda activate보다 안정적)
    start "VoiceGuide-Server" cmd /k "cd /d "%~dp0" && conda run -n ai_env uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
) else (
    start "VoiceGuide-Server" cmd /k "cd /d "%~dp0" && uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
)

echo [1/2] FastAPI 서버 창이 열렸습니다. 초기화 대기 중 (4초)...
timeout /t 4 /nobreak > nul

REM ── ngrok 터널 ────────────────────────────────────────────────────────────
start "VoiceGuide-ngrok" cmd /k "ngrok http 8000"

echo [2/2] ngrok 터널 창이 열렸습니다.
echo.
echo ============================================
echo   접속 주소
echo   로컬 : http://localhost:8000/health
echo   외부 : ngrok 창의 Forwarding URL 확인
echo.
echo   Android 앱 서버 URL 입력창에 ngrok URL 붙여넣기
echo   종료 : stop.bat
echo ============================================
pause
