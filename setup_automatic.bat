@echo off
:: Auto-elevate to admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    powershell start -verb runas '%0'
    exit /b
)

cd /d "C:\Users\Renjith\Desktop\icode (2)\imakev"

:: Delete old tasks
schtasks /delete /tn "AICinematicDaily" /f >nul 2>&1
schtasks /delete /tn "AICinematicEvery2H" /f >nul 2>&1
schtasks /delete /tn "AICinematicEvery2H_boot" /f >nul 2>&1

:: Create task: every 1.5 hours (90 minutes)
schtasks /create /tn "AICinematic" /tr "C:\Users\Renjith\AppData\Local\Python\pythoncore-3.14-64\python.exe C:\Users\Renjith\Desktop\icode (2)\imakev\run_automatic.py" /sc minute /mo 90 /st 00:00 /f

:: Create task: on boot (catch up if PC was off)
schtasks /create /tn "AICinematicBoot" /tr "C:\Users\Renjith\AppData\Local\Python\pythoncore-3.14-64\python.exe C:\Users\Renjith\Desktop\icode (2)\imakev\run_automatic.py" /sc onstart /delay 0005:00 /f

echo.
echo ========================================
echo  Fully automated!
echo  - Every 2 hours from now
echo  - On boot (delayed 5 min)
echo  - 12 videos/day
echo ========================================
echo.
echo Testing now...
start /b "" python run_pipeline.py

pause
