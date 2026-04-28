@echo off
chcp 65001 > nul
echo.
echo  WorkLog 업무 자동화 앱 시작 중...
echo  브라우저에서 http://localhost:8080 로 접속하세요.
echo.

cd /d "%~dp0"

REM venv가 있으면 우선 사용 (폐쇄망 install_offline.bat 후), 없으면 시스템 python
if exist venv\Scripts\python.exe (
    start "" http://localhost:8080
    venv\Scripts\python.exe app.py
) else (
    start "" http://localhost:8080
    python app.py
)

pause
