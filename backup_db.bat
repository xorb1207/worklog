@echo off
REM ─── worklog.db 일일 백업 (작업 스케줄러 등록용) ───
REM 매일 00:00 자동 실행하려면 Windows 작업 스케줄러에 이 .bat 등록.
REM 30일 넘은 백업은 자동 삭제.

setlocal
cd /d "%~dp0"

if not exist data\worklog.db (
    echo [SKIP] data\worklog.db not found — backup skipped.
    exit /b 0
)

if not exist backups mkdir backups

REM YYYY-MM-DD (로케일 의존성 없이 PowerShell로)
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set TODAY=%%i

REM SQLite의 안전한 온라인 백업 — venv\Scripts\python.exe 우선
set PY=python
if exist venv\Scripts\python.exe set PY=venv\Scripts\python.exe

%PY% -c "import sqlite3, shutil, sys; src=sqlite3.connect(r'data\worklog.db'); dst=sqlite3.connect(r'backups\%TODAY%.db'); src.backup(dst); src.close(); dst.close(); print('OK backups\\%TODAY%.db')"

REM 30일 넘은 백업 정리
forfiles /p backups /m *.db /d -30 /c "cmd /c del @path" 2>nul

endlocal
