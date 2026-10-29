@echo off
REM OmniCare Assistant launcher (Windows). Double-click to run.
cd /d "%~dp0"
title OmniCare Assistant

if not exist .env (
  copy .env.example .env >nul
  echo Created .env from .env.example - add your GROQ_API_KEY to it for chat answers.
)

REM Docker Desktop's CLI isn't always on PATH (old terminal, fresh install/update): look for it.
where docker >nul 2>nul
if %errorlevel% neq 0 (
  for %%D in ("%ProgramFiles%\Docker\Docker\resources\bin" "%LOCALAPPDATA%\Programs\Docker\Docker\resources\bin") do (
    if exist "%%~D\docker.exe" set "PATH=%%~D;%PATH%"
  )
)
where docker >nul 2>nul
if %errorlevel% neq 0 goto :python

docker info >nul 2>nul
if %errorlevel% equ 0 goto :dockerup
echo Docker is installed but not running. Starting Docker Desktop...
start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
echo Waiting for Docker to start (this can take a minute)...
:waitdocker
timeout /t 5 >nul
docker info >nul 2>nul || goto :waitdocker
:dockerup
echo.
echo === Starting with Docker: UI http://localhost:8501  API http://localhost:8000/docs ===
start "" cmd /c "timeout /t 90 >nul & start http://localhost:8501"
docker compose up --build
pause
exit /b

:python
echo Docker not found - running locally with Python and Node.js instead.
where python >nul 2>nul || (echo Python is not installed. Install Docker Desktop, or Python 3.11+ and Node.js 22. & pause & exit /b 1)
where npm >nul 2>nul || (echo Node.js is not installed. Install Docker Desktop, or Node.js 22 from nodejs.org. & pause & exit /b 1)
if not exist backend\.venv (
  python -m venv backend\.venv
  backend\.venv\Scripts\python -m pip install --upgrade pip
  backend\.venv\Scripts\pip install -r backend\requirements-dev.txt
)
if not exist frontend\node_modules (
  pushd frontend & call npm ci & popd
)
copy /y .env backend\.env >nul
start "OmniCare API" cmd /k "cd /d backend && .venv\Scripts\uvicorn app.main:app --port 8000"
timeout /t 15 >nul
start "OmniCare UI" cmd /k "cd /d frontend && npx vite --port 8501"
start "" cmd /c "timeout /t 8 >nul & start http://localhost:8501"
echo UI: http://localhost:8501   API docs: http://localhost:8000/docs
pause
