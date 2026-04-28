@echo off
chcp 65001 > nul
echo.
echo  Windows 작업 스케줄러에 자동화 작업 등록 중...
echo  (관리자 권한으로 실행해야 합니다)
echo.

set PYTHON=python
set SCRIPT_DIR=%~dp0scripts\scheduler.py

REM 모닝 브리핑 — 매일 오전 9:00
schtasks /create /tn "WorkLog_Morning" /tr "%PYTHON% \"%SCRIPT_DIR%\" morning" /sc daily /st 09:00 /f
echo  [OK] 모닝 브리핑 등록 (매일 09:00)

REM 퇴근 전 체크 — 매일 오후 5:30
schtasks /create /tn "WorkLog_Evening" /tr "%PYTHON% \"%SCRIPT_DIR%\" evening" /sc daily /st 17:30 /f
echo  [OK] 퇴근 전 체크 등록 (매일 17:30)

REM 방치 Task 알림 — 매일 오전 9:05
schtasks /create /tn "WorkLog_Stale" /tr "%PYTHON% \"%SCRIPT_DIR%\" stale" /sc daily /st 09:05 /f
echo  [OK] 방치 Task 알림 등록 (매일 09:05)

echo.
echo  등록 완료! 작업 스케줄러에서 'WorkLog_*' 항목을 확인하세요.
echo.
pause
