param(
    [string]$script,

    [string]$name = "",
    [string]$out_dir = "output",
    [switch]$nocache = $false,
    [switch]$nochild = $false,
    [switch]$nohanddrawn = $false,
    [switch]$tts = $false,
    [string]$restyle = "",
    [string]$seed = "42",
    [switch]$help = $false
)

if ($help -or $script -eq "" -or $script -like "-*") {
    Write-Host @"
Usage: .\run.ps1 <script.txt> [-name NAME] [-out_dir OUTPUT] [-nocache] [-nochild] [-nohanddrawn] [-tts] [-seed N] [-restyle TECHNIQUE]

Examples:
  .\run.ps1 my_story.txt
  .\run.ps1 my_story.txt -name constantinople -nochild
  .\run.ps1 my_story.txt -nocache -seed 123
  .\run.ps1 my_story.txt -nohanddrawn
  .\run.ps1 my_story.txt -tts           # Add TTS voice narration
  .\run.ps1 my_story.txt -restyle comic # Re-style existing frames to comic
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
$handDrawnFlag = if ($nohanddrawn) { "--no-hand-drawn" } else { "" }

# Restyle mode: re-style existing clean frames with a different technique
if ($restyle -ne "") {
    Write-Host ">>> Restyling frames with technique '$restyle'..." -ForegroundColor Green
    $videoPath = "$outputDir`_$restyle.mp4"
    $rstCmd = "python `"$PSScriptRoot\multi_voice.py`" --restyle $restyle --output `"$outputDir`" --video `"$videoPath`""
    Write-Host "  $rstCmd" -ForegroundColor Gray
    Invoke-Expression $rstCmd
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Restyle failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "`n=== DONE ===" -ForegroundColor Cyan
    Write-Host "Video  : $videoPath"
    exit 0
}

Write-Host ">>> Step 1: Generating frames..." -ForegroundColor Green
$genCmd = "python `"$PSScriptRoot\multi_voice.py`" --file `"$scriptPath`" --smart --output `"$outputDir`" --seed $seed $childFlag $handDrawnFlag"
Write-Host "  $genCmd" -ForegroundColor Gray
Invoke-Expression $genCmd
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Frame generation failed" -ForegroundColor Red
    exit 1
}

# Step 2: Assemble video
Write-Host "`n>>> Step 2: Assembling video..." -ForegroundColor Green
$videoPath = "$outputDir.mp4"
$ttsFlag = if ($tts) { "--tts" } else { "" }
$asmCmd = "python `"$PSScriptRoot\multi_voice.py`" --assemble $ttsFlag --output `"$outputDir`" --video `"$videoPath`""
Write-Host "  $asmCmd" -ForegroundColor Gray
Invoke-Expression $asmCmd
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Video assembly failed" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== DONE ===" -ForegroundColor Cyan
Write-Host "Frames : $outputDir/"
Write-Host "Video  : $videoPath"
