@echo off
echo Installing AI Cinematic Daily Schedule (3:00 AM)
echo.

:: Create the task
schtasks /create /tn "AICinematicDaily" /tr "C:\Users\Renjith\AppData\Local\Python\pythoncore-3.14-64\python.exe C:\Users\Renjith\Desktop\icode (2)\youtuberevenue\run_pipeline.py" /sc daily /st 03:00 /f

if %errorlevel% equ 0 (
    echo.
    echo Scheduled task created!
    echo Pipeline will run daily at 3:00 AM
    echo.
    echo To test now: python run_pipeline.py
) else (
    echo.
    echo Failed. Right-click this file and select "Run as administrator"
)

pause
