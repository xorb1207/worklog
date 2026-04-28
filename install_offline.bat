@echo off
REM ─── WorkLog 폐쇄망 설치 스크립트 (Windows / Python 3.12) ───
REM 사용: 폐쇄망 PC에서 git clone 후 이 스크립트 더블클릭 또는 cmd에서 실행

setlocal
cd /d "%~dp0"

echo.
echo === 1/3. Python 3.12 확인 ===
python --version 2>nul
if errorlevel 1 (
    echo [ERROR] Python이 PATH에 없습니다. Python 3.12를 먼저 설치하세요.
    pause
    exit /b 1
)

echo.
echo === 2/3. venv 생성 ===
if not exist venv (
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] venv 생성 실패
        pause
        exit /b 1
    )
) else (
    echo venv 이미 존재 — 건너뜀
)

echo.
echo === 3/3. 의존성 오프라인 설치 (wheels/) ===
call venv\Scripts\activate.bat
python -m pip install --upgrade --no-index --find-links wheels\ pip 2>nul
python -m pip install --no-index --find-links wheels\ -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install 실패. wheels\ 디렉터리에 모든 .whl이 있는지 확인.
    pause
    exit /b 1
)

echo.
echo === 설치 완료 ===
echo 실행: run.bat 더블클릭 또는 venv\Scripts\python.exe app.py
echo.
pause
