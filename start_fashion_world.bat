@echo off
setlocal enabledelayedexpansion

title Fashion World Pro Launcher
cd /d "C:\Users\kasul\Downloads\Fashion World pro"

echo ========================================================
echo       FASHION WORLD PRO - SAFE SERVER LAUNCHER
echo ========================================================
echo Project Location: C:\Users\kasul\Downloads\Fashion World pro
echo Database:         C:\Users\kasul\Downloads\Fashion World pro\instance\fashion_world.db
echo Target URL:       http://127.0.0.1:5000
echo ========================================================

REM Safe inspection of Port 5000
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$conns = Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue; " ^
  "if ($conns) { " ^
  "  $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique; " ^
  "  foreach ($pidVal in $pids) { " ^
  "    if ($pidVal -gt 0) { " ^
  "      $proc = Get-Process -Id $pidVal -ErrorAction SilentlyContinue; " ^
  "      $cim = Get-CimInstance Win32_Process -Filter \"ProcessId = $pidVal\" -ErrorAction SilentlyContinue; " ^
  "      $cmd = if ($cim) { $cim.CommandLine } else { '' }; " ^
  "      $isFashionWorld = ($cmd -like '*fashion world*' -or $cmd -like '*app.py*'); " ^
  "      if ($isFashionWorld) { " ^
  "        Write-Host ('[PORT 5000] Stopping Fashion World server process (PID: ' + $pidVal + ')...'); " ^
  "        Stop-Process -Id $pidVal -Force -ErrorAction SilentlyContinue; " ^
  "        Write-Host ('[PORT 5000] Safely stopped PID: ' + $pidVal); " ^
  "      } else { " ^
  "        Write-Host ('[WARNING] Port 5000 is occupied by an unrelated process (PID: ' + $pidVal + ', Name: ' + ($proc.ProcessName) + '). It will NOT be stopped.'); " ^
  "      } " ^
  "    } " ^
  "  } " ^
  "}"

REM Wait briefly before starting server
ping -n 2 127.0.0.1 >nul

echo [LAUNCH] Starting Fashion World Pro server...
start "Fashion World Pro Server" /d "C:\Users\kasul\Downloads\Fashion World pro" python app.py

echo.
echo ========================================================
echo [SUCCESS] Server launched from:
echo C:\Users\kasul\Downloads\Fashion World pro
echo Access URL: http://127.0.0.1:5000
echo ========================================================
