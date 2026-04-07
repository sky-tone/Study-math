@echo off
title Study-Math Desktop
cd /d "%~dp0"

echo.
echo  ======================================
echo     Study-Math
echo     Starting desktop app...
echo  ======================================
echo.

if exist ".venv-2\Scripts\python.exe" (
    ".venv-2\Scripts\python.exe" desktop_app.py
) else if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" desktop_app.py
) else (
    python desktop_app.py
)

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to start.
    echo Please install streamlit: pip install streamlit
    echo.
    pause
)
