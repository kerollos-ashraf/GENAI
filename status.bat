@echo off
REM Writes the OmniCare Docker status and recent logs to status.txt
cd /d "%~dp0"
(
  echo === %date% %time% ===
  echo --- docker version ---
  docker version --format "{{.Server.Version}}"
  echo --- compose ps ---
  docker compose ps -a
  echo --- images ---
  docker images
  echo --- startup ---
  docker compose logs backend | findstr /C:"Agent ready" /C:"LLM provider" /C:"is not set"
  echo --- logs ---
  docker compose logs --tail 80
) > status.txt 2>&1
