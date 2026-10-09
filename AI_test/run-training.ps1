param(
    [string]$PythonCommand = "",
    [double]$DurationDays = 14,
    [switch]$PlanOnly
)

$ErrorActionPreference = "Stop"
$projectDirectory = $PSScriptRoot
$runLogPath = Join-Path $projectDirectory "auto_train_log.txt"
$stopPath = Join-Path $projectDirectory "python\STOP_TRAINING"
$deadline = (Get-Date).AddDays($DurationDays)

if ([string]::IsNullOrWhiteSpace($PythonCommand)) {
    $venvPython = Join-Path $projectDirectory "..\.venv\Scripts\python.exe"
    $PythonCommand = if (Test-Path -LiteralPath $venvPython) {
        (Resolve-Path -LiteralPath $venvPython).Path
    } else {
        "py"
    }
}

if ($PlanOnly) {
    Write-Host "Plan: $DurationDays Tage; Python: $PythonCommand; Trainingsdaten werden einmalig erzeugt."
    return
}

$powerStateConfigured = $false
$mutex = [System.Threading.Mutex]::new($false, "Global\AI_test_training_supervisor")
$mutexOwned = $false
try {
    $mutexOwned = $mutex.WaitOne(0)
} catch [System.Threading.AbandonedMutexException] {
    $mutexOwned = $true
    Write-Host "Vorheriger Supervisor wurde unerwartet beendet; übernehme die freie Sperre."
}
if (-not $mutexOwned) {
    $mutex.Dispose()
    Write-Host "Ein automatischer Trainingslauf läuft bereits. Kein zweiter Lauf wird gestartet."
    exit 2
}

function Write-RunLog {
    param([string]$Message)
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -LiteralPath $runLogPath -Value $line -Encoding UTF8
    Write-Host $line
}

try {
    Add-Type -TypeDefinition @"
using System.Runtime.InteropServices;
public static class TrainingPowerState {
    [DllImport("kernel32.dll")]
    public static extern uint SetThreadExecutionState(uint flags);
}
"@
    [void][TrainingPowerState]::SetThreadExecutionState(2147483649)
    $powerStateConfigured = $true

    Set-Location -LiteralPath $projectDirectory
    $existingTraining = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^python(w)?\.exe$' -and
        $_.CommandLine -match 'train_all\.py' -and
        $_.ProcessId -ne $PID
    }
    if ($existingTraining) {
        $processIds = ($existingTraining | ForEach-Object { $_.ProcessId }) -join ", "
        throw "Training process already running (PID $processIds). Stop it before starting the supervisor."
    }

    Remove-Item -LiteralPath $stopPath -ErrorAction SilentlyContinue
    Write-RunLog "Starte automatischen Trainingslauf für $DurationDays Tage."
    Write-RunLog "Ollama erzeugt einmalig bis zu 20 Trainingsbeispiele und wird danach entladen; im Chat läuft nur das eigene Modell."
    & $PythonCommand "python\generate_data.py" "--count" "20"
    Write-RunLog "Datengenerator beendet (Exitcode $LASTEXITCODE)."

    while ((Get-Date) -lt $deadline) {
        $remainingHours = ($deadline - (Get-Date)).TotalHours
        if ($remainingHours -le 0) {
            break
        }

        $seed = Get-Random -Minimum 1 -Maximum 2147483647
        $env:AI_TRAIN_SEED = [string]$seed
        $env:AI_TRAIN_HOURS = $remainingHours.ToString("R", [Globalization.CultureInfo]::InvariantCulture)

        Write-RunLog "Kontinuierliches Training startet (Seed $seed, noch $([Math]::Round($remainingHours, 2)) Stunden; kein automatischer Plateau-Abbruch)."
        & $PythonCommand "python\train_all.py"
        $trainingExitCode = $LASTEXITCODE
        Write-RunLog "Trainingsprozess beendet (Exitcode $trainingExitCode)."

        if (Test-Path -LiteralPath $stopPath) {
            Write-RunLog "Stoppsignal erkannt. Training wurde manuell beendet."
            break
        }

        if ($trainingExitCode -eq 0) {
            Write-RunLog "Trainingsdauer erreicht; Prozess beendet."
            break
        }

        if ((Get-Date) -lt $deadline) {
            Write-RunLog "Training endete unerwartet mit Fehler $trainingExitCode; Neustart vom gespeicherten Stand in 30 Sekunden."
            [System.Threading.Thread]::Sleep(30000)
        }
    }

    Write-RunLog "Der geplante Trainingszeitraum ist beendet."
}
finally {
    Remove-Item Env:AI_TRAIN_SEED -ErrorAction SilentlyContinue
    Remove-Item Env:AI_TRAIN_HOURS -ErrorAction SilentlyContinue
    if ($powerStateConfigured) {
        [void][TrainingPowerState]::SetThreadExecutionState(2147483648)
    }
    $mutex.ReleaseMutex()
    $mutex.Dispose()
}