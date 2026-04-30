@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ============================================
echo   VoiceGuide 서버 + ngrok 한 번에 시작
echo ============================================
echo.

REM ── FastAPI 서버 (새 창에서 conda ai_env 활성화 후 실행) ──────────────────
start "VoiceGuide-Server" cmd /k "conda activate ai_env 2>nul || echo [conda 없음 - 기본 Python 사용] && uvicorn src.api.main:app --host 0.0.0.0 --port 8000"

echo [1/2] FastAPI 서버 창이 열렸습니다. 초기화 대기 중 (4초)...
timeout /t 4 /nobreak > nul

REM ── ngrok 터널 (새 창에서 실행) ──────────────────────────────────────────
start "VoiceGuide-ngrok" cmd /k "ngrok http 8000"

echo [2/2] ngrok 터널 창이 열렸습니다.
echo.
echo ============================================
echo   접속 주소
echo   로컬  : http://localhost:8000/health
echo   외부  : ngrok 창의 Forwarding URL 확인
echo           예) https://jubilant-trimmer-reggae.ngrok-free.app
echo.
echo   Android 앱 서버 URL 입력창에 ngrok URL 붙여넣기
echo ============================================
echo.
echo [종료하려면] stop.bat 실행 또는 각 창을 닫으세요.
pause
