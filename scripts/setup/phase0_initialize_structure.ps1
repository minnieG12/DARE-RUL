$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

$Directories = @(
    'config',
    'data\processed', 'data\features',
    'scripts\setup', 'scripts\data', 'scripts\kafka', 'scripts\spark',
    'scripts\features', 'scripts\models', 'scripts\evaluation',
    'src\data', 'src\streaming', 'src\processing', 'src\features',
    'src\models', 'src\evaluation',
    'tests', 'notebooks', 'models', 'checkpoints', 'logs',
    'results\phase0', 'results\phase1', 'results\phase2', 'results\phase3',
    'results\phase4', 'results\phase5', 'results\phase6', 'results\phase7',
    'results\phase8',
    'docs\project\literature', 'docs\project\requirements',
    'docs\project\architecture',
    'docker\kafka', 'docker\spark', 'docker\hdfs',
    'dashboard', 'paper'
)

foreach ($RelativePath in $Directories) {
    $FullPath = Join-Path $ProjectRoot $RelativePath
    New-Item -ItemType Directory -Path $FullPath -Force | Out-Null
}

foreach ($RelativePath in @(
    'data\processed\.gitkeep', 'data\features\.gitkeep',
    'models\.gitkeep', 'checkpoints\.gitkeep', 'logs\.gitkeep'
)) {
    $FullPath = Join-Path $ProjectRoot $RelativePath
    if (-not (Test-Path -LiteralPath $FullPath)) {
        New-Item -ItemType File -Path $FullPath | Out-Null
    }
}

Write-Host ''
Write-Host 'Phase 0 folder setup complete.' -ForegroundColor Green
Write-Host "Project root: $ProjectRoot"
Write-Host 'No existing data or study documents were deleted.'
Write-Host 'Next: run .\scripts\setup\phase0_check_environment.ps1'
