@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (set "APP_PY=py -3") else (set "APP_PY=python")
%APP_PY% -c "import sys;sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if errorlevel 1 goto failed
if not exist ".venv\Scripts\python.exe" %APP_PY% -m venv .venv
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
.venv\Scripts\python.exe authorize_drive.py
if errorlevel 1 goto failed
pause
exit /b 0
:failed
echo 완료하지 못했습니다. Python 3.10 이상과 위 안내를 확인하세요.
echo 토큰, 시크릿, JSON 내용은 채팅에 보내지 마세요.
pause
exit /b 1
