[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $PackageDir,

    [string] $PythonExe = "",

    [switch] $SkipGuiLaunch,

    [int] $TimeoutSeconds = 30,

    [int] $GuiLaunchSeconds = 5
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-IsWindows {
    return [Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT
}

function Invoke-VerifyPython {
    param(
        [Parameter(Mandatory = $true)]
        [string[]] $Arguments
    )
    if ($PythonExe) {
        & $PythonExe @Arguments
    } else {
        & py -3.11 @Arguments
    }
    if ($LASTEXITCODE -ne 0) {
        throw "verify_portable_package.py failed."
    }
}

function Set-IsolatedRuntimeEnvironment {
    param(
        [Parameter(Mandatory = $true)]
        [string] $PackageDir
    )
    Remove-Item Env:\PYTHONHOME -ErrorAction SilentlyContinue
    Remove-Item Env:\PYTHONPATH -ErrorAction SilentlyContinue
    Remove-Item Env:\VIRTUAL_ENV -ErrorAction SilentlyContinue
    Remove-Item Env:\MUSIC_DECOMP_FFMPEG -ErrorAction SilentlyContinue
    Remove-Item Env:\MUSIC_DECOMP_FFPROBE -ErrorAction SilentlyContinue

    $pathEntries = @(
        $PackageDir,
        (Join-Path $PackageDir "_internal"),
        (Join-Path $PackageDir "vendor\ffmpeg\bin"),
        (Join-Path $PackageDir "_internal\vendor\ffmpeg\bin"),
        (Join-Path $env:SystemRoot "System32"),
        $env:SystemRoot
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }
    $env:PATH = ($pathEntries -join [IO.Path]::PathSeparator)
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$PackageDir = (Resolve-Path $PackageDir).Path
$verifyScript = Join-Path $RepoRoot "scripts\verify_portable_package.py"

Invoke-VerifyPython -Arguments @(
    $verifyScript,
    "--package-dir",
    $PackageDir,
    "--timeout-seconds",
    "$TimeoutSeconds"
)

if ($SkipGuiLaunch) {
    Write-Host "GUI launch smoke skipped."
    return
}

if (-not (Test-IsWindows)) {
    throw "GUI launch smoke must run on Windows."
}

$guiExe = Join-Path $PackageDir "MusicDecomp.exe"
if (-not (Test-Path -LiteralPath $guiExe -PathType Leaf)) {
    throw "GUI executable is missing: $guiExe"
}

$savedPath = $env:PATH
$savedPythonHome = $env:PYTHONHOME
$savedPythonPath = $env:PYTHONPATH
$savedVirtualEnv = $env:VIRTUAL_ENV
$savedFfmpeg = $env:MUSIC_DECOMP_FFMPEG
$savedFfprobe = $env:MUSIC_DECOMP_FFPROBE

try {
    Set-IsolatedRuntimeEnvironment -PackageDir $PackageDir
    $process = Start-Process -FilePath $guiExe -WorkingDirectory $PackageDir -PassThru
    if ($process.WaitForExit($GuiLaunchSeconds * 1000)) {
        throw "GUI process exited during launch smoke with code $($process.ExitCode)."
    }
    Stop-Process -Id $process.Id -Force
    Write-Host "GUI launch smoke passed for $GuiLaunchSeconds seconds."
} finally {
    $env:PATH = $savedPath
    if ($null -eq $savedPythonHome) {
        Remove-Item Env:\PYTHONHOME -ErrorAction SilentlyContinue
    } else {
        $env:PYTHONHOME = $savedPythonHome
    }
    if ($null -eq $savedPythonPath) {
        Remove-Item Env:\PYTHONPATH -ErrorAction SilentlyContinue
    } else {
        $env:PYTHONPATH = $savedPythonPath
    }
    if ($null -eq $savedVirtualEnv) {
        Remove-Item Env:\VIRTUAL_ENV -ErrorAction SilentlyContinue
    } else {
        $env:VIRTUAL_ENV = $savedVirtualEnv
    }
    if ($null -eq $savedFfmpeg) {
        Remove-Item Env:\MUSIC_DECOMP_FFMPEG -ErrorAction SilentlyContinue
    } else {
        $env:MUSIC_DECOMP_FFMPEG = $savedFfmpeg
    }
    if ($null -eq $savedFfprobe) {
        Remove-Item Env:\MUSIC_DECOMP_FFPROBE -ErrorAction SilentlyContinue
    } else {
        $env:MUSIC_DECOMP_FFPROBE = $savedFfprobe
    }
}
