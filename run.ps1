param(
    [string]$script,

    [string]$name = "",
    [string]$out_dir = "output",
    [switch]$nocache = $false,
    [switch]$nochild = $false,
    [string]$seed = "42",
    [switch]$help = $false
)

if ($help -or $script -eq "" -or $script -like "-*") {
    Write-Host @"
Usage: .\run.ps1 <script.txt> [-name NAME] [-out_dir OUTPUT] [-nocache] [-nochild] [-seed N]

Examples:
  .\run.ps1 my_story.txt
  .\run.ps1 my_story.txt -name constantinople -nochild
  .\run.ps1 my_story.txt -nocache -seed 123
"@
    exit 0
}

# Resolve script path
$scriptPath = if (Test-Path $script) { (Resolve-Path $script).Path } else { $script }
$scriptName = [System.IO.Path]::GetFileNameWithoutExtension($scriptPath)
if ($name -eq "") { $name = $scriptName }

$outputDir = "$out_dir/$name" -replace '\\', '/'

Write-Host "=== Ding-Dong-Think Pipeline ===" -ForegroundColor Cyan
Write-Host "Script : $scriptPath"
Write-Host "Output : $outputDir"
Write-Host "Seed   : $seed"
Write-Host ""

# Clear cache if requested
if ($nocache -and (Test-Path "output/.mv_cache.json")) {
    Remove-Item "output/.mv_cache.json" -Force
    Write-Host "[cache cleared]" -ForegroundColor Yellow
}

# Step 1: Generate frames
$childFlag = if ($nochild) { "--no-child" } else { "" }
Write-Host ">>> Step 1: Generating frames..." -ForegroundColor Green
$genCmd = "python `"$PSScriptRoot\multi_voice.py`" --file `"$scriptPath`" --smart --output `"$outputDir`" --seed $seed $childFlag"
Write-Host "  $genCmd" -ForegroundColor Gray
Invoke-Expression $genCmd
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Frame generation failed" -ForegroundColor Red
    exit 1
}

# Step 2: Assemble video
Write-Host "`n>>> Step 2: Assembling video..." -ForegroundColor Green
$videoPath = "$outputDir.mp4"
$asmCmd = "python `"$PSScriptRoot\multi_voice.py`" --assemble --output `"$outputDir`" --video `"$videoPath`""
Write-Host "  $asmCmd" -ForegroundColor Gray
Invoke-Expression $asmCmd
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Video assembly failed" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== DONE ===" -ForegroundColor Cyan
Write-Host "Frames : $outputDir/"
Write-Host "Video  : $videoPath"
