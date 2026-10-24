@echo off
rem Сборка агента: сначала служба (onedir), затем приложение пользователя (onefile, служба встроена)
cd /d "%~dp0..\..\agent"
".venv\Scripts\python.exe" -m PyInstaller --noconfirm MonitoringAgentService.spec || goto :fail
".venv\Scripts\python.exe" -m PyInstaller --noconfirm MonitoringAgentApp.spec || goto :fail
echo Готово: agent\dist\MonitoringAgentApp.exe
if not "%1"=="nopause" pause
exit /b 0
:fail
echo ОШИБКА сборки агента
if not "%1"=="nopause" pause
exit /b 1
