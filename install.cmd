@echo off
chcp 65001 >nul
cd /d "%~dp0"

rem 1) 파이썬 찾기, 없으면 설치
set "PY="
py -3 -c "import sys; sys.exit(sys.version_info < (3, 9))" >nul 2>nul && set "PY=py -3"
if not defined PY python -c "import sys; sys.exit(sys.version_info < (3, 9))" >nul 2>nul && set "PY=python"
if not defined PY (
  echo [1/4] 파이썬이 없어 설치합니다...
  winget install -e --id Python.Python.3.12 --scope user --location "%LocalAppData%\Programs\Python\Python312" --silent --accept-package-agreements --accept-source-agreements || goto :fail
  set "PY="%LocalAppData%\Programs\Python\Python312\python.exe""
)
%PY% -c "import sys; sys.exit(sys.version_info < (3, 9))" >nul 2>nul || goto :fail
echo [1/4] 파이썬: %PY%

rem 2) 전용 가상환경 + Playwright 설치 (이미 있으면 건너뜀)
if not exist ".venv\Scripts\python.exe" %PY% -m venv .venv || goto :fail
".venv\Scripts\python.exe" -c "import playwright" >nul 2>nul || (
  echo [2/4] Playwright 설치 중...
  ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || goto :fail
)
echo [2/4] Playwright 준비 완료

rem 3) Playwright 크롬 설치 (PC에 크롬이 없을 때 대신 씀)
echo [3/4] 브라우저 설치 확인 중...
".venv\Scripts\python.exe" -m playwright install chromium || goto :fail

rem 4) 매주 월요일 09:00 자동 실행 등록
schtasks /create /f /sc weekly /d MON /st 09:00 /tn "NHB-Buyer-Collect" /tr "\"%~dp0run.cmd\"" >nul || goto :fail
echo [4/4] 매주 월요일 09:00 자동 실행 등록 완료

echo.
echo 설치 끝. 지금 바로 돌려보려면 run.cmd 를 더블클릭하세요.
pause
exit /b 0

:fail
echo 설치 실패. 위 메시지를 확인하세요.
pause
exit /b 1
