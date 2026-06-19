@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================================
echo   VOICE STUDIO - Cai dat (chi chay 1 lan)
echo ============================================================
echo.

REM --- 1. Kiem tra Python ---
where python >nul 2>nul
if errorlevel 1 (
    echo [LOI] Chua cai Python that.
    echo.
    echo Hay cai Python 3.11 tai: https://www.python.org/downloads/release/python-3119/
    echo  - Tai "Windows installer (64-bit)"
    echo  - Khi cai NHO TICH "Add python.exe to PATH"
    echo Sau do chay lai install.bat
    echo.
    pause
    exit /b 1
)

python --version
echo.

REM --- 2. Tao moi truong ao ---
if not exist ".venv" (
    echo [1/4] Tao moi truong ao .venv ...
    python -m venv .venv
)
call .venv\Scripts\activate.bat

echo [2/4] Nang cap pip ...
python -m pip install --upgrade pip

REM --- 3. Cai PyTorch ban CUDA 12.1 (cho RTX 3060) ---
echo [3/4] Cai PyTorch (CUDA 12.1) - tai ~2.5GB, vui long cho ...
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121

REM --- 4. Cai cac thu vien con lai ---
echo [4/4] Cai engine giong noi va giao dien ...
pip install -r requirements.txt

echo.
echo ============================================================
echo   XONG! Chay app bang cach nhay dup file:  run.bat
echo ============================================================
echo.
echo (Tuy chon) De xuat file MP3, cai ffmpeg:
echo     winget install Gyan.FFmpeg
echo.
pause
