@echo off
chcp 65001 > nul
echo [VoiceGuide] 서버 종료 중...

REM 포트 8000 점유 프로세스 종료 (uvicorn / python)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " 2^>nul') do (
    if not "%%a"=="" (
        taskkill /f /pid %%a 2>nul
        echo   - PID %%a 종료
    )
)

REM ngrok 프로세스 종료
taskkill /f /im ngrok.exe 2>nul && echo   - ngrok 종료 || echo   - ngrok 미실행

echo [완료] 서버가 종료됐습니다.
pause
