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
exit /b %RC%
