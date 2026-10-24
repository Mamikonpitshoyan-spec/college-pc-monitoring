@echo off
chcp 65001 >nul
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -NoProfile -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)
title Удаление Monitoring Server
echo Закрываю приложение...
taskkill /IM MonitoringAdminApp.exe /F 2>nul
echo Удаляю ярлык...
del "%USERPROFILE%\Desktop\Monitoring Admin.lnk" 2>nul
echo Удаляю файлы...
rmdir /S /Q "C:\Program Files\MonitoringServer"
echo.
echo Сервер мониторинга удалён. База данных удалена вместе с папкой.
pause
