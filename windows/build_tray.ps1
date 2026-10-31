# Build script for OmiDaemon Windows System Tray Companion
$csc = "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (-not (Test-Path $csc)) {
    Write-Error "Microsoft .NET C# compiler (csc.exe) not found."
    exit 1
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectDir = Split-Path -Parent $scriptDir

Write-Host "Compiling OmiDaemonTray.exe..." -ForegroundColor Cyan
& $csc /target:winexe /win32icon:"$projectDir\assets\icon.ico" /out:"$scriptDir\OmiDaemonTray.exe" /reference:System.Windows.Forms.dll /reference:System.Drawing.dll "$scriptDir\OmiDaemonTray.cs"

if ($LASTEXITCODE -eq 0) {
    Write-Host "OmiDaemonTray.exe compiled successfully!" -ForegroundColor Green
} else {
    Write-Error "Compilation failed with exit code $LASTEXITCODE"
}
