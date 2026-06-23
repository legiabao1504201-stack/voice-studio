@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Chua cai dat. Hay chay install.bat truoc.
    pause
    exit /b 1
)
echo Server chay tai:  http://localhost:8000
echo Nhan Ctrl+C de dung.
".venv\Scripts\python.exe" -m uvicorn server:app --host 0.0.0.0 --port 8000
pause
