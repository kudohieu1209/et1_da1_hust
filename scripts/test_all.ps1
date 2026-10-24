$ErrorActionPreference = 'Stop'
$repoDirectory = Split-Path -Parent $PSScriptRoot
$backendDirectory = Join-Path $repoDirectory 'project/backend'
$frontendDirectory = Join-Path $repoDirectory 'project/frontend'
$pythonExecutable = if ($env:PYTHON_BIN) { $env:PYTHON_BIN } else { Join-Path $backendDirectory '.venv-win/Scripts/python.exe' }
if (-not (Test-Path -LiteralPath $pythonExecutable)) { throw 'Chưa có venv. Hãy thực hiện bước cài đặt trong README.' }

function Invoke-Checked([string]$Program, [string[]]$CommandArguments) {
    & $Program @CommandArguments
    if ($LASTEXITCODE -ne 0) { throw "Lệnh thất bại (exit $LASTEXITCODE): $Program $CommandArguments" }
}

$environmentNames = @('PYTHONPATH','PYTHONIOENCODING','MONGODB_URI','GEMINI_API_KEY','GOOGLE_API_KEY','OPENAI_API_KEY')
$originalEnvironment = @{}
foreach ($name in $environmentNames) { $originalEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
try {
    $env:PYTHONIOENCODING = 'utf-8'
    $env:PYTHONPATH = $backendDirectory
    # unittest/eval also disable real integrations before importing configuration.
    $env:MONGODB_URI = ''
    $env:GEMINI_API_KEY = ''
    $env:GOOGLE_API_KEY = ''
    $env:OPENAI_API_KEY = ''
    Invoke-Checked $pythonExecutable @('-m','unittest','discover','-s',"$backendDirectory/tests",'-t',$backendDirectory,'-v')
    Invoke-Checked $pythonExecutable @('-m','unittest','discover','-s',"$repoDirectory/project/data/tests",'-v')
    Invoke-Checked $pythonExecutable @('-m','unittest','discover','-s',"$repoDirectory/project/eval/tests",'-v')
    Invoke-Checked $pythonExecutable @("$repoDirectory/project/eval/run_eval.py",'--label','latest','--check')
    Invoke-Checked $pythonExecutable @("$repoDirectory/project/eval/run_eval.py",'--golden',"$repoDirectory/project/eval/validation_questions.jsonl",'--label','validation_latest')
    Invoke-Checked 'npm.cmd' @('--prefix',$frontendDirectory,'run','lint')
    Invoke-Checked 'npm.cmd' @('--prefix',$frontendDirectory,'run','build')
} finally {
    foreach ($name in $environmentNames) { [Environment]::SetEnvironmentVariable($name, $originalEnvironment[$name], 'Process') }
}
