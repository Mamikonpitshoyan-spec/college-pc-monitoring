# Запуск агента с правами администратора (включает датчики температуры ACPI).
# Все сообщения агента и любые ошибки пишутся в лог: C:\Users\USER\.zcode\tmp\agent_admin.log
try {
    Set-Location "C:\Users\USER\Desktop\Arajin Ashxatanq Excel\agent"
    "=== agent (admin) started $(Get-Date -Format s) ===" | Out-File "C:\Users\USER\.zcode\tmp\agent_admin.log" -Append -Encoding utf8
    & ".\.venv\Scripts\python.exe" main.py 2>&1 | Out-File "C:\Users\USER\.zcode\tmp\agent_admin.log" -Append -Encoding utf8
} catch {
    "LAUNCHER ERROR: $_" | Out-File "C:\Users\USER\.zcode\tmp\agent_admin.log" -Append -Encoding utf8
}
