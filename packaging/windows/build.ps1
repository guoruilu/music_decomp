[CmdletBinding()]
param(
    [ValidateSet("cpu", "cuda")]
    [string] $Profile = "cpu",

    [string] $VenvPath = "",

    [string] $RequirementsFile = "",

    [string] $TorchIndexUrl = "",

    [switch] $AllowUnpinnedBaseRequirements,

    [switch] $SkipTests,

    [switch] $SkipGuiSmoke
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-IsWindows {
    return [Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT
}

function Invoke-BasePython {
    param(
        [Parameter(Mandatory = $true)]
        [string[]] $Arguments
    )
    & py -3.11 @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python launcher command failed: py -3.11 $($Arguments -join ' ')"
    }
}

function Invoke-PackagePython {
    param(
        [Parameter(Mandatory = $true)]
        [string] $PythonExe,

        [Parameter(Mandatory = $true)]
        [string[]] $Arguments
    )
    & $PythonExe @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed: $PythonExe $($Arguments -join ' ')"
    }
}

function Invoke-PackagePythonOutput {
    param(
        [Parameter(Mandatory = $true)]
        [string] $PythonExe,

        [Parameter(Mandatory = $true)]
        [string[]] $Arguments
    )
    $output = & $PythonExe @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed: $PythonExe $($Arguments -join ' ')"
    }
    return $output
}

function Assert-FileExists {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path,

        [Parameter(Mandatory = $true)]
        [string] $Description
    )
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Description is missing: $Path"
    }
}

function Assert-DirectoryExists {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path,

        [Parameter(Mandatory = $true)]
        [string] $Description
    )
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        throw "$Description is missing: $Path"
    }
}

function Get-LicenseLikeFiles {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Root
    )
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
        return @()
    }
    return @(
        Get-ChildItem -LiteralPath $Root -Recurse -File |
            Where-Object {
                $name = $_.Name.ToLowerInvariant()
                $name.StartsWith("license") -or
                $name.StartsWith("copying") -or
                $name.StartsWith("notice")
            }
    )
}

function Assert-UsableRequirements {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path
    )
    Assert-FileExists -Path $Path -Description "requirements file"
    $content = Get-Content -LiteralPath $Path -Raw
    $meaningfulLines = @(
        Get-Content -LiteralPath $Path |
            ForEach-Object { $_.Trim() } |
            Where-Object {
                $_ -and
                -not $_.StartsWith("#") -and
                -not $_.StartsWith("--")
            }
    )
    if ($content -match "NOT GENERATED" -or $meaningfulLines.Count -eq 0) {
        throw (
            "Requirements file is still a placeholder: $Path. " +
            "Generate and validate the Windows $Profile lock first, or rerun " +
            "with -AllowUnpinnedBaseRequirements for a non-reproducible local build."
        )
    }
}

function Assert-PackagingAssets {
    param(
        [Parameter(Mandatory = $true)]
        [string] $RepoRoot
    )
    $ffmpegDir = Join-Path $RepoRoot "vendor\ffmpeg"
    $modelsDir = Join-Path $RepoRoot "models"
    Assert-FileExists -Path (Join-Path $ffmpegDir "bin\ffmpeg.exe") -Description "bundled FFmpeg executable"
    Assert-FileExists -Path (Join-Path $ffmpegDir "bin\ffprobe.exe") -Description "bundled FFprobe executable"
    Assert-FileExists -Path (Join-Path $modelsDir "manifest.json") -Description "model manifest"

    $modelPayloadFiles = @(
        Get-ChildItem -LiteralPath $modelsDir -Recurse -File |
            Where-Object { $_.FullName -ne (Join-Path $modelsDir "manifest.json") }
    )
    if ($modelPayloadFiles.Count -eq 0) {
        throw "No model payload files were found under $modelsDir."
    }

    $ffmpegLicenseFiles = Get-LicenseLikeFiles -Root $ffmpegDir
    if ($ffmpegLicenseFiles.Count -eq 0) {
        throw "No FFmpeg license or notice files were found under $ffmpegDir."
    }
}

function Copy-IfPresent {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Source,

        [Parameter(Mandatory = $true)]
        [string] $DestinationDirectory
    )
    if (Test-Path -LiteralPath $Source -PathType Leaf) {
        New-Item -ItemType Directory -Force -Path $DestinationDirectory | Out-Null
        Copy-Item -LiteralPath $Source -Destination $DestinationDirectory -Force
    }
}

function Copy-PortableMetadata {
    param(
        [Parameter(Mandatory = $true)]
        [string] $RepoRoot,

        [Parameter(Mandatory = $true)]
        [string] $PackageDir,

        [Parameter(Mandatory = $true)]
        [string] $PythonExe,

        [Parameter(Mandatory = $true)]
        [string] $Profile,

        [Parameter(Mandatory = $true)]
        [string] $RequirementsPath
    )
    Assert-DirectoryExists -Path $PackageDir -Description "PyInstaller package directory"

    $manifestDir = Join-Path $PackageDir "manifests"
    $requirementsManifestDir = Join-Path $manifestDir "requirements"
    $projectLicenseDir = Join-Path $PackageDir "licenses\project"
    $ffmpegLicenseDir = Join-Path $PackageDir "licenses\ffmpeg"
    $packageLicenseDir = Join-Path $PackageDir "licenses\python-packages"
    New-Item -ItemType Directory -Force -Path $manifestDir | Out-Null
    New-Item -ItemType Directory -Force -Path $requirementsManifestDir | Out-Null
    New-Item -ItemType Directory -Force -Path $projectLicenseDir | Out-Null
    New-Item -ItemType Directory -Force -Path $ffmpegLicenseDir | Out-Null
    New-Item -ItemType Directory -Force -Path $packageLicenseDir | Out-Null

    Copy-Item -LiteralPath (Join-Path $RepoRoot "docs\by-feature\dependency-and-asset-manifest.md") -Destination $manifestDir -Force
    Copy-Item -LiteralPath (Join-Path $RepoRoot "models\manifest.json") -Destination (Join-Path $manifestDir "models-manifest.json") -Force
    Copy-Item -LiteralPath (Join-Path $RepoRoot "requirements\base.in") -Destination $requirementsManifestDir -Force
    Copy-Item -LiteralPath (Join-Path $RepoRoot "requirements\win-cpu.txt") -Destination $requirementsManifestDir -Force
    Copy-Item -LiteralPath (Join-Path $RepoRoot "requirements\win-cuda.txt") -Destination $requirementsManifestDir -Force
    Copy-IfPresent -Source (Join-Path $RepoRoot "vendor\README.md") -DestinationDirectory (Join-Path $manifestDir "vendor")

    foreach ($pattern in @("LICENSE*", "NOTICE*", "COPYING*", "THIRD_PARTY*")) {
        Get-ChildItem -Path $RepoRoot -File -Filter $pattern -ErrorAction SilentlyContinue |
            ForEach-Object {
                Copy-Item -LiteralPath $_.FullName -Destination $projectLicenseDir -Force
            }
    }

    Get-LicenseLikeFiles -Root (Join-Path $RepoRoot "vendor\ffmpeg") |
        ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination $ffmpegLicenseDir -Force
        }

    $sitePackages = Invoke-PackagePythonOutput -PythonExe $PythonExe -Arguments @(
        "-c",
        "import site; print(site.getsitepackages()[0])"
    ) | Select-Object -First 1
    if ($sitePackages) {
        Get-ChildItem -LiteralPath $sitePackages -Directory -Filter "*.dist-info" |
            ForEach-Object {
                $distInfo = $_
                $licenseFiles = Get-LicenseLikeFiles -Root $distInfo.FullName
                if ($licenseFiles.Count -gt 0) {
                    $target = Join-Path $packageLicenseDir $distInfo.Name
                    New-Item -ItemType Directory -Force -Path $target | Out-Null
                    $licenseFiles |
                        ForEach-Object {
                            Copy-Item -LiteralPath $_.FullName -Destination $target -Force
                        }
                }
            }
    }

    $packageManifest = @(
        "MusicDecomp portable package",
        "Built: $(Get-Date -Format o)",
        "Profile: $Profile",
        "Requirements: $RequirementsPath",
        "FFmpeg source: vendor\ffmpeg",
        "Model manifest: models\manifest.json"
    )
    $packageManifest | Set-Content -LiteralPath (Join-Path $manifestDir "PACKAGE-MANIFEST.txt") -Encoding ascii
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $RepoRoot

if (-not (Test-IsWindows)) {
    throw "Step 12 packaging must run on Windows x64. This script does not create a Linux substitute package."
}

if (-not $VenvPath) {
    $VenvPath = Join-Path $RepoRoot ".venv"
}

if (-not $RequirementsFile) {
    $RequirementsFile = Join-Path $RepoRoot "requirements\win-$Profile.txt"
}

$pythonVersionCheck = @"
import platform
import struct
import sys

if sys.version_info[:2] != (3, 11):
    raise SystemExit(f"Python 3.11 is required, got {sys.version.split()[0]}")
if struct.calcsize("P") * 8 != 64:
    raise SystemExit("A 64-bit Python interpreter is required for Windows packaging")
print(f"Python {sys.version.split()[0]} {platform.architecture()[0]}")
"@
Invoke-BasePython -Arguments @("-c", $pythonVersionCheck)

Assert-PackagingAssets -RepoRoot $RepoRoot

$requirementsPath = (Resolve-Path $RequirementsFile).Path
try {
    Assert-UsableRequirements -Path $requirementsPath
} catch {
    if (-not $AllowUnpinnedBaseRequirements) {
        throw
    }
    $requirementsPath = Join-Path $RepoRoot "requirements\base.in"
    Write-Warning "Using unpinned requirements/base.in. Do not claim a reproducible release from this build."
}

Invoke-BasePython -Arguments @("-m", "venv", $VenvPath)
$venvPython = Join-Path $VenvPath "Scripts\python.exe"
Assert-FileExists -Path $venvPython -Description "virtual environment Python"

Invoke-PackagePython -PythonExe $venvPython -Arguments @("-m", "pip", "install", "-U", "pip")

$pipInstallArgs = @("-m", "pip", "install")
if ($TorchIndexUrl) {
    $pipInstallArgs += @("--index-url", $TorchIndexUrl, "--extra-index-url", "https://pypi.org/simple")
}
$pipInstallArgs += @("-r", $requirementsPath)
Invoke-PackagePython -PythonExe $venvPython -Arguments $pipInstallArgs
Invoke-PackagePython -PythonExe $venvPython -Arguments @("-m", "pip", "install", "--no-deps", "-e", $RepoRoot)

if (-not $SkipTests) {
    Invoke-PackagePython -PythonExe $venvPython -Arguments @("-m", "pytest")
}

$specPath = Join-Path $RepoRoot "packaging\pyinstaller\music_decomp.spec"
Invoke-PackagePython -PythonExe $venvPython -Arguments @(
    "-m",
    "PyInstaller",
    "--noconfirm",
    "--clean",
    $specPath
)

$packageDir = Join-Path $RepoRoot "dist\MusicDecomp"
Copy-PortableMetadata -RepoRoot $RepoRoot -PackageDir $packageDir -PythonExe $venvPython -Profile $Profile -RequirementsPath $requirementsPath

$smokeArgs = @(
    "-PackageDir",
    $packageDir,
    "-PythonExe",
    $venvPython
)
if ($SkipGuiSmoke) {
    $smokeArgs += "-SkipGuiLaunch"
}
& (Join-Path $RepoRoot "packaging\windows\smoke-test.ps1") @smokeArgs
if ($LASTEXITCODE -ne 0) {
    throw "Portable smoke test failed."
}

Write-Host "Portable package created at $packageDir"
