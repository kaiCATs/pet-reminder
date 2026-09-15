[CmdletBinding()]
param(
    [switch]$Sign,
    [string]$CertificateThumbprint = $env:PETREMINDER_SIGN_CERT_THUMBPRINT,
    [string]$TimestampUrl = $(if ($env:PETREMINDER_TIMESTAMP_URL) { $env:PETREMINDER_TIMESTAMP_URL } else { 'http://timestamp.digicert.com' }),
    [string]$SignToolPath = $env:PETREMINDER_SIGNTOOL_PATH
)

$ErrorActionPreference = 'Stop'

$installerDir = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$projectDir = Split-Path -Parent $installerDir
$sourceExe = Join-Path $projectDir 'dist\PetReminder.exe'
$versionPath = Join-Path $projectDir 'app_version.py'
$scriptPath = Join-Path $installerDir 'PetReminder.iss'
$isccCandidates = @(
    (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
    'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
    'C:\Program Files\Inno Setup 6\ISCC.exe'
)
$iscc = $isccCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1

function Find-SignTool {
    if (-not [string]::IsNullOrWhiteSpace($SignToolPath)) {
        if (-not (Test-Path -LiteralPath $SignToolPath -PathType Leaf)) {
            throw "signtool.exe was not found at '$SignToolPath'."
        }
        return (Resolve-Path -LiteralPath $SignToolPath).Path
    }

    $fromPath = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($fromPath) {
        return $fromPath.Source
    }

    $sdkRoots = @(
        (Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10\bin'),
        (Join-Path $env:ProgramFiles 'Windows Kits\10\bin')
    ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) -and (Test-Path -LiteralPath $_) }

    foreach ($sdkRoot in $sdkRoots) {
        $candidate = Get-ChildItem -LiteralPath $sdkRoot -Filter signtool.exe -File -Recurse -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($candidate) {
            return $candidate.FullName
        }
    }

    return $null
}

function Sign-File([string]$Path, [string]$Description) {
    if (-not $Sign) {
        return
    }

    if ([string]::IsNullOrWhiteSpace($CertificateThumbprint)) {
        throw 'Signing was requested, but PETREMINDER_SIGN_CERT_THUMBPRINT was not provided.'
    }

    $certificate = Get-ChildItem "Cert:\CurrentUser\My\$CertificateThumbprint" -ErrorAction SilentlyContinue
    if (-not $certificate) {
        throw "The signing certificate with thumbprint '$CertificateThumbprint' is not installed in the current user certificate store."
    }
    if (-not $certificate.HasPrivateKey) {
        throw 'The selected signing certificate does not have an available private key.'
    }

    $signTool = Find-SignTool
    if ([string]::IsNullOrWhiteSpace($signTool)) {
        throw 'signtool.exe was not found. Install the Windows SDK or pass -SignToolPath.'
    }

    Write-Host "Signing $Description..." -ForegroundColor Cyan
    $signArgs = @(
        'sign',
        '/sha1', $CertificateThumbprint,
        '/fd', 'SHA256',
        '/td', 'SHA256',
        '/tr', $TimestampUrl,
        '/d', 'Pet Reminder',
        $Path
    )
    & $signTool @signArgs
    if ($LASTEXITCODE -ne 0) {
        throw "signtool failed for $Description with code $LASTEXITCODE."
    }

    $signature = Get-AuthenticodeSignature -LiteralPath $Path
    if ($signature.Status -ne 'Valid') {
        throw "The signature for $Description could not be verified: $($signature.Status)."
    }
}

if (-not (Test-Path -LiteralPath $sourceExe -PathType Leaf)) {
    throw 'Build the application first: dist\PetReminder.exe was not found.'
}
if (-not (Test-Path -LiteralPath $versionPath -PathType Leaf)) {
    throw 'app_version.py was not found.'
}
if ([string]::IsNullOrWhiteSpace($iscc)) {
    throw 'Inno Setup compiler (ISCC.exe) was not found.'
}

if ($Sign) {
    Write-Host 'Code signing is enabled.' -ForegroundColor Cyan
} else {
    Write-Host 'Code signing is disabled. Pass -Sign after installing a trusted certificate.' -ForegroundColor Yellow
}

$versionMatch = [regex]::Match((Get-Content -LiteralPath $versionPath -Raw), 'APP_VERSION\s*=\s*["'']([^"'']+)["'']')
if (-not $versionMatch.Success) {
    throw 'Could not read APP_VERSION from app_version.py.'
}
$version = $versionMatch.Groups[1].Value
$outputExe = Join-Path $installerDir "PetReminder_Setup_v${version}_GUI.exe"
$checksumPath = "$outputExe.sha256"

Sign-File -Path $sourceExe -Description 'PetReminder.exe'

& $iscc "/DMyAppVersion=$version" $scriptPath
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $outputExe -PathType Leaf)) {
    throw "Inno Setup failed with code $LASTEXITCODE."
}

Sign-File -Path $outputExe -Description 'GUI installer'

$hash = (Get-FileHash -LiteralPath $outputExe -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath $checksumPath -Value "$hash *$([IO.Path]::GetFileName($outputExe))" -Encoding ascii

Write-Host "GUI installer created: $outputExe"
Write-Host "SHA-256 file created: $checksumPath"
if ($Sign) {
    Write-Host 'Authenticode signatures verified for the app and installer.' -ForegroundColor Green
}
