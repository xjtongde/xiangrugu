# Windows PowerShell 5 transport/staging only; project execution stays on host 32.
# Builds the closed p01 task-card metadata packet, verifies every staged byte
# against the authoritative packet-inputs.sha256 (catches CRLF corruption),
# then exclusively creates the private runtime root on 32 and verifies there.
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$evidence='docs/superpowers/evidence/2026-11-13-p01-task-card'
$packet=Join-Path $PSScriptRoot 'packet'
if(Test-Path $packet){if(@(Get-ChildItem $packet -Force).Count){throw 'Existing nonempty packet'}}
else{[IO.Directory]::CreateDirectory($packet) | Out-Null}
$review='datamgmt/contracts/releases/2026-10-06-bootstrap/sqlite-value-project-partition-readiness.closed.json'
$document=Get-Content (Join-Path $repo $review) -Raw | ConvertFrom-Json
$metadata=@($review)+@($document.bindings.PSObject.Properties | ForEach-Object {$_.Value.path})
function Copy-Input([string]$relative,[string]$destinationRelative){
    if($relative.StartsWith('/') -or $relative.Contains('\') -or ($relative.Split('/') -contains '..') -or
       $relative.Contains('.env') -or $relative.EndsWith('.key') -or $relative.EndsWith('.pem')){throw 'Unsafe metadata path'}
    $source=Join-Path $repo ($relative -replace '/','\')
    $target=Join-Path $packet ($destinationRelative -replace '/','\')
    if(Test-Path $target){throw 'Existing staged input'}
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target)) | Out-Null
    Copy-Item -LiteralPath $source -Destination $target
}
foreach($relative in $metadata){Copy-Input $relative ('metadata/'+$relative)}
$certificate='docs/superpowers/evidence/2026-10-13-medium-foreground/raw/batch-runner-medium-foreground-20261013/foreground-metadata/output/fixture/certificate.json'
if((Get-FileHash -LiteralPath (Join-Path $repo ($certificate -replace '/','\'))).Hash.ToLowerInvariant() -cne '58cb2e50f2124829130d4a9d6b8e55b8f6b2418bca18458685cb5d16ff193f9a'){throw 'Certificate identity'}
Copy-Input $certificate 'metadata/selected-certificate.json'
$runtimeVerification='docs/superpowers/evidence/2026-11-13-request-reader-integration/verification.json'
if((Get-FileHash -LiteralPath (Join-Path $repo ($runtimeVerification -replace '/','\'))).Hash.ToLowerInvariant() -cne '8c121fd05e47db385b170d379436492ffd79e96ef99c1adae4b5ea0951f7f3da'){throw 'Runtime verification identity'}
Copy-Input $runtimeVerification 'metadata/runtime-verification.json'
$buildInputs='docs/superpowers/evidence/2026-11-13-request-reader-integration/build-inputs.sha256'
if((Get-FileHash -LiteralPath (Join-Path $repo ($buildInputs -replace '/','\'))).Hash.ToLowerInvariant() -cne 'df1c63d6fc242369266cd5d122654a4c46f6d014c03bd388eefb7efa58ef0d18'){throw 'Build inputs identity'}
Copy-Input $buildInputs 'metadata/build-inputs.sha256'
$installedOrigin='docs/superpowers/evidence/2026-11-13-request-reader-integration/installed-origin.py'
if((Get-FileHash -LiteralPath (Join-Path $repo ($installedOrigin -replace '/','\'))).Hash.ToLowerInvariant() -cne '99359c17c687dad23af36db1f97d5f2ba512e4afa0d526036ebb333dde06fa3a'){throw 'Installed origin identity'}
Copy-Input $installedOrigin $installedOrigin
# LF-safe controller copies live under the evidence tree (-text in .gitattributes);
# they are byte-identical to scripts/ originals and staged at the scripts/ paths.
Copy-Input "$evidence/controller-evidence.sh" 'scripts/controller-evidence.sh'
Copy-Input "$evidence/controller-heartbeat.sh" 'scripts/controller-heartbeat.sh'
foreach($tool in @('prepare-closed-review.py','product-gate-probe.py','run-review.sh','verify.sh')){
    Copy-Input "$evidence/$tool" "$evidence/$tool"
}
$files=@(Get-ChildItem $packet -Recurse -File | ForEach-Object {$_.FullName.Substring($packet.Length+1) -replace '\\','/'} | Sort-Object)
# Authoritative manifest check: exact file set and per-file SHA-256. Any CRLF
# conversion or content drift in the Windows working tree fails here, before
# anything leaves this machine.
$expected=@{}
foreach($line in [IO.File]::ReadAllLines((Join-Path $PSScriptRoot 'packet-inputs.sha256'))){
    if($line){$parts=$line -split '  ',2; $expected[$parts[1]]=$parts[0]}
}
if($files.Count -ne $expected.Count){throw ('Staged file count '+$files.Count+' != manifest '+$expected.Count)}
foreach($relative in $files){
    if(-not $expected.ContainsKey($relative)){throw "Unexpected staged file: $relative"}
    $actual=(Get-FileHash -LiteralPath (Join-Path $packet ($relative -replace '/','\'))).Hash.ToLowerInvariant()
    if($actual -cne $expected[$relative]){throw "Staged byte mismatch (CRLF or drift): $relative"}
}
$hashes=@($files | ForEach-Object {$expected[$_]+'  '+$_})
[IO.File]::WriteAllLines((Join-Path $PSScriptRoot 'packet-files.txt'),[string[]]$files,[Text.UTF8Encoding]::new($false))
$archive=Join-Path $PSScriptRoot 'packet.tar.gz'
if(Test-Path $archive){throw 'Existing packet archive'}
Push-Location $packet
try{& tar -czf $archive -T (Join-Path $PSScriptRoot 'packet-files.txt');if($LASTEXITCODE -ne 0){throw 'Packet tar failed'}}finally{Pop-Location}
$remote='/opt/mydocker/xiangrugu/data/var/batch-runner-p01-task-card-20261113'
& ssh -o BatchMode=yes root@192.168.3.32 "set -e; mkdir '$remote'; mkdir '$remote/source-green-v1'"
if($LASTEXITCODE -ne 0){throw 'Exclusive review root failed'}
& scp -q -O $archive ('root@192.168.3.32:'+$remote+'/packet.tar.gz')
if($LASTEXITCODE -ne 0){throw 'Packet transfer'}
& scp -q -O (Join-Path $PSScriptRoot 'packet-inputs.sha256') ('root@192.168.3.32:'+$remote+'/source-green-v1/INPUTS.sha256')
if($LASTEXITCODE -ne 0){throw 'Pin transfer'}
& ssh -o BatchMode=yes root@192.168.3.32 "set -e; tar -xzf '$remote/packet.tar.gz' -C '$remote/source-green-v1'; cd '$remote/source-green-v1'; sha256sum -c INPUTS.sha256 > ../packet-check.txt; bash -n $evidence/run-review.sh; bash -n $evidence/verify.sh"
if($LASTEXITCODE -ne 0){throw 'Review packet verification failed'}
Write-Output ('Staged '+$files.Count+' metadata/tool files. No source snapshot or installed product override.')
Write-Output ('Remote receipts: '+$remote+'/packet-check.txt and '+$remote+'/source-green-v1/INPUTS.sha256')
