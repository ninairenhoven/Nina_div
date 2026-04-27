@echo off
cd /d "%~dp0"
set PYTHON=C:\Users\NinaIrenHoven\AppData\Local\Programs\Python\Python310\python.exe
echo Starter Eventor Startliste...
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:5001"
"%PYTHON%" app.py
pause
