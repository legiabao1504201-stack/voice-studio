@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Tao duong ham Cloudflare ra internet (mien phi, khong can tai khoan)...
echo Cho dong "https://....trycloudflare.com" hien ra ben duoi - do la dia chi cong khai.
echo (Server phai dang chay: chay serve.bat o cua so khac truoc.)
echo.
cloudflared tunnel --url http://localhost:8000
pause
