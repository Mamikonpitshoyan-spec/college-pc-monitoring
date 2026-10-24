@echo off
rem Удаляет службу агента (права администратора, один раз confirm UAC).
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Удаление службы требует прав администратора - подтвердите в окне Windows...
    powershell -NoProfile -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)
title Удаление службы Monitoring Agent
cd /d "C:\Users\USER\Desktop\Arajin Ashxatanq Excel\agent"
".venv\Scripts\python.exe" service.py stop
".venv\Scripts\python.exe" service.py remove
echo.
echo Служба удалена. Агент больше не запускается автоматически.
pause
