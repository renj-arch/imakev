"""Schedule the pipeline to run daily at 3:00 AM via Windows Task Scheduler."""

import subprocess, sys, os, getpass
from pathlib import Path

TASK_NAME = "AICinematicEvery2H"
SCRIPT = str(Path(__file__).parent / "run_pipeline.py")
PYTHON = sys.executable


def install():
    print("Creating scheduled task: Daily at 3:00 AM")
    print(f"  Python: {PYTHON}")
    print(f"  Script: {SCRIPT}")
    print()

    # PowerShell command to create the task
    ps_command = f'''
$action = New-ScheduledTaskAction -Execute "{PYTHON}" -Argument "{SCRIPT}"
$trigger = New-ScheduledTaskTrigger -Daily -At 00:00AM
$trigger.RepetitionInterval = New-TimeSpan -Hours 2
$trigger.RepetitionDuration = New-TimeSpan -Days 365
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId "{getpass.getuser()}" -LogonType S4U -RunLevel Limited
Register-ScheduledTask -TaskName "{TASK_NAME}" -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force
'''

    # Also create a one-time startup trigger
    ps_command += f'''
$trigger2 = New-ScheduledTaskTrigger -AtStartup
Register-ScheduledTask -TaskName "{TASK_NAME}_boot" -Action $action -Trigger $trigger2 -Settings $settings -Principal $principal -Force
'''

    result = subprocess.run(
        ["powershell", "-Command", ps_command],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode == 0:
        print("Scheduled task created successfully!")
        print(f"  Name: {TASK_NAME}")
        print("  Schedule: Daily at 3:00 AM")
        print("\nTo test immediately:")
        print(f"  python run_pipeline.py")
        print("\nTo manage the task:")
        print("  Open: Task Scheduler (taskschd.msc)")
        print(f"  Look for: {TASK_NAME}")
    else:
        print(f"Error: {result.stderr}")
        print("\nManual setup:")
        print("1. Open Task Scheduler (Win+R, type taskschd.msc)")
        print("2. Create Basic Task → name 'AICinematicDaily'")
        print(f"3. Trigger: Daily at 3:00 AM")
        print(f"4. Action: Start program → '{PYTHON}'")
        print(f"5. Arguments: '{SCRIPT}'")


def remove():
    subprocess.run(
        ["powershell", "-Command", f"Unregister-ScheduledTask -TaskName '{TASK_NAME}' -Confirm:$false"],
        capture_output=True, timeout=15,
    )
    print("Task removed.")


if __name__ == "__main__":
    if "--remove" in sys.argv:
        remove()
    else:
        install()
