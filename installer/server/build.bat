@echo off
rem Полная сборка: служба -> приложение пользователя -> админ (в него встраивается exe пользователя)
call "%~dp0..\agent\build.bat" nopause || goto :fail
cd /d "%~dp0..\..\server"
".venv\Scripts\python.exe" -m PyInstaller --noconfirm MonitoringAdminApp.spec || goto :fail
echo Готово: server\dist\MonitoringAdminApp.exe (раздавать этот файл, не MonitoringAdmin-Setup.zip)
if not "%1"=="nopause" pause
exit /b 0
:fail
echo ОШИБКА сборки
if not "%1"=="nopause" pause
exit /b 1
