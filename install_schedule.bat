@echo off
echo Installing AI Cinematic Schedule - Every 2 Hours
echo.

:: Remove old daily task if exists
schtasks /delete /tn "AICinematicDaily" /f >nul 2>&1

:: Create new task every 2 hours
schtasks /create /tn "AICinematicEvery2H" /tr "C:\Users\Renjith\AppData\Local\Python\pythoncore-3.14-64\python.exe C:\Users\Renjith\Desktop\icode (2)\imakev\run_pipeline.py" /sc hourly /mo 2 /st 00:00 /f

if %errorlevel% equ 0 (
    echo.
    echo Scheduled task created!
    echo Pipeline will run every 2 hours, 24/7
    echo That is 12 videos per day!
    echo.
    echo To test now: python run_pipeline.py
) else (
    echo.
    echo Failed. Right-click this file and select "Run as administrator"
)

pause
