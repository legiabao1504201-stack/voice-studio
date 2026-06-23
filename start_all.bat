@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Chua cai dat. Hay chay install.bat truoc.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" start_all.py
pause
