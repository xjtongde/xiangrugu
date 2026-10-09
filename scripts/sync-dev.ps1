[CmdletBinding()]
param(
    [ValidateSet("192.168.3.32")]
    [string]$HostName = "192.168.3.32",
    [ValidateSet("/opt/mydocker/xiangrugu/deploy")]
    [string]$RemoteRoot = "/opt/mydocker/xiangrugu/deploy"
)

$ErrorActionPreference = "Stop"

$repositoryRoot = (& git rev-parse --show-toplevel).Trim()
if ($LASTEXITCODE -ne 0 -or -not $repositoryRoot) {
    throw "Run this script from the Xiangrugu Git working tree."
}

Push-Location $repositoryRoot
$temporaryDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ("xiangrugu-sync-" + [guid]::NewGuid())
try {
    New-Item -ItemType Directory -Path $temporaryDirectory | Out-Null
    $manifest = Join-Path $temporaryDirectory "manifest.txt"
    $archive = Join-Path $temporaryDirectory "workspace.tar"

    $files = @(& git ls-files --cached --others --exclude-standard)
    if ($LASTEXITCODE -ne 0) {
        throw "git ls-files failed."
    }

    $excludedPattern = '(^|/)(\.git|\.agents|\.secrets|data|usedata)(/|$)|(^|/)\.env($|\.)|\.(pem|key|p12|pfx)$'
    $files = @($files | ForEach-Object { $_ -replace '\\', '/' } | Where-Object { $_ -notmatch $excludedPattern -and (Test-Path -LiteralPath $_ -PathType Leaf) })
    if ($files.Count -eq 0) {
        throw "No eligible files found to synchronize."
    }

    [System.IO.File]::WriteAllLines($manifest, $files, [System.Text.UTF8Encoding]::new($false))
    & tar -cf $archive -T $manifest
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to create the synchronization archive."
    }

    $remoteArchive = "/tmp/xiangrugu-sync-$([guid]::NewGuid()).tar"
    & scp -O $archive "${HostName}:$remoteArchive"
    if ($LASTEXITCODE -ne 0) {
        throw "Upload to host 32 failed."
    }

    & ssh $HostName "mkdir -p '$RemoteRoot' && tar -xf '$remoteArchive' -C '$RemoteRoot' && rm -f '$remoteArchive'"
    if ($LASTEXITCODE -ne 0) {
        throw "Extraction on host 32 failed."
    }

    Write-Host "Synchronized $($files.Count) files to ${HostName}:$RemoteRoot"
}
finally {
    Pop-Location
    if (Test-Path -LiteralPath $temporaryDirectory) {
        Remove-Item -LiteralPath $temporaryDirectory -Recurse -Force
    }
}
