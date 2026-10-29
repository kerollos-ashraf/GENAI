@echo off
REM Captures walkthrough screenshots into docs\screenshots (the app must already be running).
cd /d "%~dp0"
title OmniCare walkthrough capture
(
  where python >nul 2>nul || (echo Python not found. Install Python 3.11+ & exit /b 1)
  if not exist .walkthrough-venv (
    echo Setting up Playwright - first run only...
    python -m venv .walkthrough-venv
    .walkthrough-venv\Scripts\python -m pip install --quiet playwright
    .walkthrough-venv\Scripts\python -m playwright install chromium
  )
  .walkthrough-venv\Scripts\python scripts\capture_walkthrough.py
  echo DONE
) > walkthrough.log 2>&1
