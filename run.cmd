@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" call install.cmd || exit /b 1
if not exist logs mkdir logs
set PYTHONIOENCODING=utf-8
".venv\Scripts\python.exe" salesintel.py %* >> logs\run.log 2>&1
set RC=%ERRORLEVEL%
type logs\run.log | more +0 >nul
echo 끝 (코드 %RC%). 결과: data\leads.csv / reports\  로그: logs\run.log
rem 더블클릭했을 때 결과를 읽을 수 있게 20초 뒤 닫힘 (자동 실행도 20초 뒤 끝남)
timeout /t 20 >nul
exit /b %RC%
