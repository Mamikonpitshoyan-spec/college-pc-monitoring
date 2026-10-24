@echo off
rem Устанавливает агента как службу Windows: автозапуск с системой,
rem права администратора (работает датчик температуры), без UAC каждый раз.
rem Разрешение спрашивается ОДИН раз - при этой установке.
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Установка службы требует прав администратора - подтвердите в окне Windows...
    powershell -NoProfile -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)
title Установка службы Monitoring Agent
cd /d "C:\Users\USER\Desktop\Arajin Ashxatanq Excel\agent"
echo Устанавливаю службу...
".venv\Scripts\python.exe" service.py install
echo Запускаю службу...
".venv\Scripts\python.exe" service.py start
echo.
echo === Состояние службы ===
sc query MonitoringAgent | findstr STATE
echo.
echo Готово: агент теперь стартует вместе с Windows и работает в фоне.
echo Проверка: http://127.0.0.1:8000/devices (устройство должно быть ОНЛАЙН).
pause
