@echo off
echo =========================================
echo Starting Media Analyzer Web UI...
echo =========================================
python app.py
if %errorlevel% neq 0 (
    echo.
    echo Error occurred!
)
echo.
pause
