@echo off
rem Запуск агента мониторинга с правами администратора.
rem Даёт доступ к датчикам температуры ACPI. Ничего не скачивает.
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Требуются права администратора - подтвердите в окне Windows...
    powershell -NoProfile -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)
title Monitoring Agent (ADMIN)
cd /d "C:\Users\USER\Desktop\Arajin Ashxatanq Excel\agent"
echo Агент запускается с правами администратора. Не закрывайте это окно.
".venv\Scripts\python.exe" main.py
echo.
echo Агент остановлен.
pause
