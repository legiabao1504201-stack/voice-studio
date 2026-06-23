@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Chua cai dat. Hay chay install.bat truoc.
    pause
    exit /b 1
)
REM Goi thang python trong venv (khong dung activate de tranh loi khi di chuyen thu muc)
".venv\Scripts\python.exe" app.py
if errorlevel 1 pause
