param(
    [string]$DeviceSerial = '',
    [switch]$Build
)

$ErrorActionPreference = 'Stop'
$repoPath = Split-Path -Parent $PSScriptRoot
$adbCandidates = @(
    (Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'),
    'C:\Android\platform-tools\adb.exe'
)
$adbPath = $adbCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $adbPath) { throw 'Android SDK platform-tools/adb.exe was not found.' }

if (-not $DeviceSerial) {
    $connectedDevices = @(& $adbPath devices | ForEach-Object {
        if ($_ -match '^([^\s]+)\s+device$') { $Matches[1] }
    })
    if ($connectedDevices.Count -ne 1) { throw 'Connect one authorized Android device, or pass -DeviceSerial.' }
    $DeviceSerial = $connectedDevices[0]
}

$capabilities = Invoke-RestMethod 'http://localhost:8000/api/auth/ctt/capabilities'
if (-not $capabilities.available) { throw 'Start the local backend with CTT browser login enabled first.' }

if ($Build) {
    $previousJavaHome = $env:JAVA_HOME
    try {
        if (-not $env:JAVA_HOME) {
            $jdk = Get-ChildItem 'C:\Program Files\Microsoft' -Directory -Filter 'jdk-21*' | Select-Object -First 1
            if (-not $jdk) { throw 'Set JAVA_HOME to a JDK 21 installation.' }
            $env:JAVA_HOME = $jdk.FullName
        }
        Push-Location (Join-Path $repoPath 'frontend')
        try {
            & npm.cmd run cap:sync
            if ($LASTEXITCODE -ne 0) { throw 'Capacitor sync failed.' }
            Push-Location android
            try {
                & .\gradlew.bat assembleUsbDebug --console=plain
                if ($LASTEXITCODE -ne 0) { throw 'USB APK build failed.' }
            } finally { Pop-Location }
        } finally { Pop-Location }
    } finally { $env:JAVA_HOME = $previousJavaHome }
}

$apkPath = Join-Path $repoPath 'frontend\android\app\build\outputs\apk\usbDebug\app-usbDebug.apk'
if (-not (Test-Path -LiteralPath $apkPath)) { throw 'Build the USB APK first with -Build.' }
& $adbPath -s $DeviceSerial reverse tcp:8000 tcp:8000
if ($LASTEXITCODE -ne 0) { throw 'USB port forwarding failed.' }
& $adbPath -s $DeviceSerial install -r $apkPath
if ($LASTEXITCODE -ne 0) { throw 'USB APK installation failed. Check the phone for an installation prompt.' }
& $adbPath -s $DeviceSerial shell am start -n vn.hust.advisor.usb/vn.hust.advisor.MainActivity
if ($LASTEXITCODE -ne 0) { throw 'USB app launch failed.' }
Write-Output 'AdvisorBK USB is connected to this PC. Keep USB connected and the backend running.'
Write-Output 'Choose the school account in the app, then sign in yourself in the CTT browser on the PC.'
