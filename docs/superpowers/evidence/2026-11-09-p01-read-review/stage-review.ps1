$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$packet=Join-Path $PSScriptRoot 'packet'
if(Test-Path $packet){if(@(Get-ChildItem $packet -Force).Count){throw 'Existing nonempty packet'}}
else{[IO.Directory]::CreateDirectory($packet) | Out-Null}
$review='datamgmt/contracts/releases/2026-10-06-bootstrap/sqlite-value-project-partition-readiness.closed.json'
$document=Get-Content (Join-Path $repo $review) -Raw | ConvertFrom-Json
$metadata=@($review)+@($document.bindings.PSObject.Properties | ForEach-Object {$_.Value.path})
function Copy-Input([string]$relative,[string]$destinationRelative){
    if($relative.StartsWith('/') -or $relative.Contains('\') -or ($relative.Split('/') -contains '..') -or
       $relative.Contains('.env') -or $relative.EndsWith('.key') -or $relative.EndsWith('.pem')){throw 'Unsafe metadata path'}
    $source=Join-Path $repo $relative
    $target=Join-Path $packet $destinationRelative
    if(Test-Path $target){throw 'Existing staged input'}
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target)) | Out-Null
    Copy-Item -LiteralPath $source -Destination $target
}
foreach($relative in $metadata){Copy-Input $relative ('metadata/'+$relative)}
$certificate='docs/superpowers/evidence/2026-10-13-medium-foreground/raw/batch-runner-medium-foreground-20261013/foreground-metadata/output/fixture/certificate.json'
if((Get-FileHash -LiteralPath (Join-Path $repo $certificate)).Hash.ToLowerInvariant() -cne '58cb2e50f2124829130d4a9d6b8e55b8f6b2418bca18458685cb5d16ff193f9a'){throw 'Certificate identity'}
Copy-Input $certificate 'metadata/selected-certificate.json'
foreach($relative in @('scripts/controller-evidence.sh','scripts/controller-heartbeat.sh',
    'docs/superpowers/evidence/2026-11-08-metadata-reader-integration/installed-origin.py',
    'docs/superpowers/evidence/2026-11-09-p01-read-review/prepare-closed-review.py',
    'docs/superpowers/evidence/2026-11-09-p01-read-review/run-review.sh')){Copy-Input $relative $relative}
$files=@(Get-ChildItem $packet -Recurse -File | ForEach-Object {$_.FullName.Substring($packet.Length+1) -replace '\\','/'} | Sort-Object)
$hashes=@($files | ForEach-Object {(Get-FileHash -LiteralPath (Join-Path $packet $_)).Hash.ToLowerInvariant()+'  '+$_})
[IO.File]::WriteAllLines((Join-Path $PSScriptRoot 'packet-files.txt'),[string[]]$files,[Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllLines((Join-Path $PSScriptRoot 'packet-inputs.sha256'),[string[]]$hashes,[Text.UTF8Encoding]::new($false))
$archive=Join-Path $PSScriptRoot 'packet.tar.gz'
if(Test-Path $archive){throw 'Existing packet archive'}
Push-Location $packet
try{& tar -czf $archive -T (Join-Path $PSScriptRoot 'packet-files.txt');if($LASTEXITCODE -ne 0){throw 'Packet tar failed'}}finally{Pop-Location}
$remote='/opt/mydocker/xiangrugu/data/var/batch-runner-p01-read-review-20261109'
& ssh -o BatchMode=yes root@192.168.3.32 "set -e; mkdir '$remote'; mkdir '$remote/source-green-v16'"
if($LASTEXITCODE -ne 0){throw 'Exclusive review root failed'}
& scp -q -O $archive ('root@192.168.3.32:'+$remote+'/packet.tar.gz')
if($LASTEXITCODE -ne 0){throw 'Packet transfer'}
& scp -q -O (Join-Path $PSScriptRoot 'packet-inputs.sha256') ('root@192.168.3.32:'+$remote+'/source-green-v16/INPUTS.sha256')
if($LASTEXITCODE -ne 0){throw 'Pin transfer'}
& ssh -o BatchMode=yes root@192.168.3.32 "set -e; tar -xzf '$remote/packet.tar.gz' -C '$remote/source-green-v16'; cd '$remote/source-green-v16'; sha256sum -c INPUTS.sha256 > ../packet-check.txt; bash -n docs/superpowers/evidence/2026-11-09-p01-read-review/run-review.sh"
if($LASTEXITCODE -ne 0){throw 'Review packet verification failed'}
Write-Output ('Staged '+$files.Count+' metadata/tool files. No source snapshot or installed product override.')
