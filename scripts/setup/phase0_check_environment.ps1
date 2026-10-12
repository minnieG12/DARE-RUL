$ErrorActionPreference = 'Continue'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$RawDir = Join-Path $ProjectRoot 'data\CMAPSSData'
$OutDir = Join-Path $ProjectRoot 'results\phase0'
$ReportPath = Join-Path $OutDir 'environment_report.txt'
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

$Report = [System.Collections.Generic.List[string]]::new()
$Report.Add('DARE-RUL Phase 0 Environment Report')
$Report.Add("Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
$Report.Add("Project root: $ProjectRoot")
$Report.Add("Raw dataset directory: $RawDir")
$Report.Add('')

function Invoke-RecordedCheck {
    param(
        [Parameter(Mandatory=$true)][string]$Label,
        [Parameter(Mandatory=$true)][string]$CommandName,
        [string[]]$Arguments = @()
    )

    $Report.Add("--- $Label ---")
    $command = Get-Command $CommandName -ErrorAction SilentlyContinue
    if (-not $command) {
        $message = "NOT FOUND: command '$CommandName' is not on PATH."
        Write-Host $message -ForegroundColor Yellow
        $Report.Add($message)
        $Report.Add('')
        return
    }

    try {
        $output = & $CommandName @Arguments 2>&1
        $exitCode = $LASTEXITCODE
        $text = ($output | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine
        if ([string]::IsNullOrWhiteSpace($text)) { $text = '(no output)' }
        $Report.Add($text)
        $Report.Add("Exit code: $exitCode")
        if ($exitCode -eq 0) {
            Write-Host "$Label : OK" -ForegroundColor Green
            Write-Host $text
        } else {
            Write-Host "$Label : command returned exit code $exitCode" -ForegroundColor Yellow
            Write-Host $text
        }
    } catch {
        $message = "CHECK FAILED: $($_.Exception.Message)"
        Write-Host "$Label : $message" -ForegroundColor Yellow
        $Report.Add($message)
    }
    $Report.Add('')
}

Invoke-RecordedCheck -Label 'Python 3.10' -CommandName 'py' -Arguments @('-3.10', '--version')
Invoke-RecordedCheck -Label 'Git' -CommandName 'git' -Arguments @('--version')
Invoke-RecordedCheck -Label 'Docker CLI' -CommandName 'docker' -Arguments @('--version')
Invoke-RecordedCheck -Label 'Docker Compose' -CommandName 'docker' -Arguments @('compose', 'version')
Invoke-RecordedCheck -Label 'Docker engine / resources' -CommandName 'docker' -Arguments @('info', '--format', 'OS={{.OperatingSystem}} CPUs={{.NCPU}} MemoryBytes={{.MemTotal}}')
Invoke-RecordedCheck -Label 'Java' -CommandName 'java' -Arguments @('-version')
Invoke-RecordedCheck -Label 'WSL status' -CommandName 'wsl' -Arguments @('--status')

$Report.Add('--- Windows and disk ---')
$Report.Add("PowerShell: $($PSVersionTable.PSVersion)")
try {
    $os = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
    $Report.Add("Windows: $($os.Caption)")
    $Report.Add("Physical RAM (bytes): $($os.TotalVisibleMemorySize * 1024)")
} catch { $Report.Add("Windows/RAM check unavailable: $($_.Exception.Message)") }
try {
    $driveLetter = (Split-Path -Qualifier $ProjectRoot).TrimEnd(':')
    $drive = Get-PSDrive -Name $driveLetter -ErrorAction Stop
    $Report.Add("Project drive: $driveLetter`:")
    $Report.Add("Drive free space (bytes): $($drive.Free)")
} catch { $Report.Add("Drive check unavailable: $($_.Exception.Message)") }
$Report.Add('')

$Report.Add('--- Expected C-MAPSS files ---')
$Expected = @(
    'train_FD001.txt', 'train_FD002.txt', 'train_FD003.txt', 'train_FD004.txt',
    'test_FD001.txt', 'test_FD002.txt', 'test_FD003.txt', 'test_FD004.txt',
    'RUL_FD001.txt', 'RUL_FD002.txt', 'RUL_FD003.txt', 'RUL_FD004.txt'
)
$Missing = @()
if (-not (Test-Path -LiteralPath $RawDir -PathType Container)) {
    $message = "MISSING DATA DIRECTORY: $RawDir"
    Write-Host $message -ForegroundColor Red
    $Report.Add($message)
} else {
    foreach ($filename in $Expected) {
        $path = Join-Path $RawDir $filename
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            $Report.Add("FOUND: $filename")
        } else {
            $Report.Add("MISSING: $filename")
            $Missing += $filename
        }
    }
    $present = $Expected.Count - $Missing.Count
    Write-Host "C-MAPSS files found: $present / $($Expected.Count)"
    if ($Missing.Count -gt 0) {
        Write-Host ('Missing: ' + ($Missing -join ', ')) -ForegroundColor Red
    } else {
        Write-Host 'All 12 expected C-MAPSS files are present.' -ForegroundColor Green
    }
}

$Report | Set-Content -LiteralPath $ReportPath -Encoding UTF8
Write-Host ''
Write-Host "Environment report saved to: $ReportPath" -ForegroundColor Cyan
Write-Host 'This script only checks and records. It does not install or delete anything.'
