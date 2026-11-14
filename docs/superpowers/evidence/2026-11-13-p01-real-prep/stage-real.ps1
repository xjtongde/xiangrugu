# Windows PowerShell 5 transport/staging only; project execution stays on host 32.
# Builds the Stage A/B real-execution packet for attempt real-p01-20261113-a,
# verifies every staged byte against packet-inputs-real.sha256 (catches CRLF
# corruption), then exclusively creates the private runtime root and rechecks
# there. Staged bytes are the ACCEPTED receipt outputs; nothing is regenerated.
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$evidence='docs/superpowers/evidence/2026-11-13-p01-real-prep'
$receipts='docs/superpowers/evidence/2026-11-13-p01-task-card-receipts'
$packet=Join-Path $PSScriptRoot 'packet-real'
if(Test-Path $packet){if(@(Get-ChildItem $packet -Force).Count){throw 'Existing nonempty packet'}}
else{[IO.Directory]::CreateDirectory($packet) | Out-Null}
function Copy-Input([string]$relative,[string]$destinationRelative){
    if($relative.StartsWith('/') -or $relative.Contains('\') -or ($relative.Split('/') -contains '..')){throw 'Unsafe path'}
    $source=Join-Path $repo ($relative -replace '/','\')
    $target=Join-Path $packet ($destinationRelative -replace '/','\')
    if(Test-Path $target){throw "Existing staged input: $destinationRelative"}
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target)) | Out-Null
    Copy-Item -LiteralPath $source -Destination $target
}
# 1. parent review + 14 bindings + evidence aliases (same set as accepted packet)
$review='datamgmt/contracts/releases/2026-10-06-bootstrap/sqlite-value-project-partition-readiness.closed.json'
$document=Get-Content (Join-Path $repo $review) -Raw | ConvertFrom-Json
foreach($relative in (@($review)+@($document.bindings.PSObject.Properties | ForEach-Object {$_.Value.path}))){
    Copy-Input $relative ('metadata/'+$relative)
}
$certificate='docs/superpowers/evidence/2026-10-13-medium-foreground/raw/batch-runner-medium-foreground-20261013/foreground-metadata/output/fixture/certificate.json'
if((Get-FileHash -LiteralPath (Join-Path $repo ($certificate -replace '/','\'))).Hash.ToLowerInvariant() -cne '58cb2e50f2124829130d4a9d6b8e55b8f6b2418bca18458685cb5d16ff193f9a'){throw 'Certificate identity'}
Copy-Input $certificate 'metadata/selected-certificate.json'
Copy-Input 'docs/superpowers/evidence/2026-11-13-request-reader-integration/verification.json' 'metadata/runtime-verification.json'
Copy-Input 'docs/superpowers/evidence/2026-11-13-request-reader-integration/build-inputs.sha256' 'metadata/build-inputs.sha256'
# 2. accepted run outputs verbatim (reproduced into /data/var/run at runtime)
$outputDir=Join-Path $repo (($receipts+'/returned/p01-card-metadata/output') -replace '/','\')
$outputFiles=@(Get-ChildItem $outputDir -Recurse -File -Force | ForEach-Object {$_.FullName.Substring($outputDir.Length+1) -replace '\\','/'})
foreach($rel in $outputFiles){Copy-Input "$receipts/returned/p01-card-metadata/output/$rel" ("returned-output/"+$rel)}
# 3. accepted card at packet root
Copy-Input "$receipts/returned/p01-card-metadata/output/task-card.closed.json" 'task-card.closed.json'
# 4. tools
Copy-Input 'docs/superpowers/evidence/2026-11-13-request-reader-integration/installed-origin.py' 'docs/superpowers/evidence/2026-11-13-request-reader-integration/installed-origin.py'
Copy-Input 'docs/superpowers/evidence/2026-11-13-p01-task-card/controller-evidence.sh' 'scripts/controller-evidence.sh'
Copy-Input 'docs/superpowers/evidence/2026-11-13-p01-task-card/controller-heartbeat.sh' 'scripts/controller-heartbeat.sh'
# stage-a-inputs.tsv reproduces every absolute bound path (sha/container/staged);
# verify-mount-table.py closes the REAL materialized mount set; verify-terminal.py
# checks Stage B terminal receipts against the adjudicated rehearsal expectations.
foreach($tool in @('materialize-real.py','run-real.sh','verify-real.sh',
                   'stage-a-inputs.tsv','verify-mount-table.py','verify-terminal.py')){Copy-Input "$evidence/$tool" "$evidence/$tool"}
# 5. authoritative byte gate
$files=@(Get-ChildItem $packet -Recurse -File | ForEach-Object {$_.FullName.Substring($packet.Length+1) -replace '\\','/'} | Sort-Object)
$manifestPath=Join-Path $PSScriptRoot 'packet-inputs-real.sha256'
if($env:XRG_REGENERATE_INPUTS -eq '1'){
    # Offline regeneration ONLY: rebuild the manifest from the staged bytes so a
    # packet that legitimately gains tools (e.g. stage-a-inputs.tsv,
    # verify-mount-table.py, verify-terminal.py) can be re-pinned for review.
    # Without this flag the existing manifest stays the authoritative gate.
    $manifest=[string[]]($files | ForEach-Object {
        (Get-FileHash -LiteralPath (Join-Path $packet ($_ -replace '/','\'))).Hash.ToLowerInvariant()+'  '+$_})
    [IO.File]::WriteAllLines($manifestPath,$manifest,[Text.UTF8Encoding]::new($false))
}
$expected=@{}
foreach($line in [IO.File]::ReadAllLines($manifestPath)){
    if($line){$parts=$line -split '  ',2; $expected[$parts[1]]=$parts[0]}
}
if($files.Count -ne $expected.Count){throw ('Staged file count '+$files.Count+' != manifest '+$expected.Count)}
foreach($relative in $files){
    if(-not $expected.ContainsKey($relative)){throw "Unexpected staged file: $relative"}
    $actual=(Get-FileHash -LiteralPath (Join-Path $packet ($relative -replace '/','\'))).Hash.ToLowerInvariant()
    if($actual -cne $expected[$relative]){throw "Staged byte mismatch (CRLF or drift): $relative"}
}
[IO.File]::WriteAllLines((Join-Path $PSScriptRoot 'packet-files-real.txt'),[string[]]$files,[Text.UTF8Encoding]::new($false))
$archive=Join-Path $PSScriptRoot 'packet-real.tar.gz'
if(Test-Path $archive){throw 'Existing packet archive'}
Push-Location $packet
try{& tar -czf $archive -T (Join-Path $PSScriptRoot 'packet-files-real.txt');if($LASTEXITCODE -ne 0){throw 'Packet tar failed'}}finally{Pop-Location}
$remote='/opt/mydocker/xiangrugu/data/var/batch-runner-real-p01-20261113-a'
& ssh -o BatchMode=yes root@192.168.3.32 "set -e; mkdir '$remote'; mkdir '$remote/source-green-v1'"
if($LASTEXITCODE -ne 0){throw 'Exclusive review root failed'}
& scp -q -O $archive ('root@192.168.3.32:'+$remote+'/packet-real.tar.gz')
if($LASTEXITCODE -ne 0){throw 'Packet transfer'}
& scp -q -O (Join-Path $PSScriptRoot 'packet-inputs-real.sha256') ('root@192.168.3.32:'+$remote+'/source-green-v1/INPUTS.sha256')
if($LASTEXITCODE -ne 0){throw 'Pin transfer'}
& ssh -o BatchMode=yes root@192.168.3.32 "set -e; tar -xzf '$remote/packet-real.tar.gz' -C '$remote/source-green-v1'; cd '$remote/source-green-v1'; sha256sum -c INPUTS.sha256 > ../packet-real-check.txt; bash -n $evidence/run-real.sh; bash -n $evidence/verify-real.sh"
if($LASTEXITCODE -ne 0){throw 'Review packet verification failed'}
Write-Output ('Staged '+$files.Count+' accepted-byte/tool files verbatim. No snapshot content, no authorization placed.')
Write-Output ('Remote receipts: '+$remote+'/packet-real-check.txt and '+$remote+'/source-green-v1/INPUTS.sha256')
