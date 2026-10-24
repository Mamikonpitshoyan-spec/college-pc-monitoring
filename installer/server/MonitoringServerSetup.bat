@echo off
chcp 65001 >nul
rem ============================================================
rem  Monitoring Server - installer (Level 12)
rem  Один exe: встроенный сервер + дашборд в окне + иконка в трее.
rem  Пароль администратора создаётся при первом открытии дашборда.
rem ============================================================
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Установка требует прав администратора - подтвердите в окне Windows...
    powershell -NoProfile -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)
title Установка Monitoring Server

set "SRC=%~dp0..\..\server\dist\MonitoringAdminApp"
set "DEST=C:\Program Files\MonitoringServer"

echo ============================================
echo   Установка сервера мониторинга
echo ============================================
echo.
echo [1/3] Копирую файлы в %DEST% ...
xcopy "%SRC%" "%DEST%\" /E /I /Y >nul

echo [2/3] Создаю ярлык на рабочем столе...
powershell -NoProfile -Command "$s = (New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop') + '\Monitoring Admin.lnk'); $s.TargetPath = '%DEST%\MonitoringAdminApp.exe'; $s.IconLocation = '%DEST%\MonitoringAdminApp.exe'; $s.Save()"

echo [3/3] Запускаю приложение...
start "" "%DEST%\MonitoringAdminApp.exe"

echo.
echo ============================================
echo   Готово! Откроется окно дашборда:
echo   - придумайте пароль администратора (один раз)
echo   - юзеры подключаются по коду из «＋ Добавить компьютер»
echo   Удалить: UninstallMonitoringServer.bat
echo ============================================
pause
