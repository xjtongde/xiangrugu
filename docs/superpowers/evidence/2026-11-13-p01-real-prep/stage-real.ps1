# Windows PowerShell 5 transport/staging only; project execution stays on host 32.
# Builds the Stage A/B real-execution packet for attempt real-p01-20261113-a,
# verifies every staged byte against packet-inputs-real.sha256 (catches CRLF
# corruption), then exclusively creates the private runtime root and rechecks
# there. Staged bytes are the ACCEPTED receipt outputs; nothing is regenerated.
# Modes (mutually exclusive):
#   default              staging + authoritative-manifest gate + tar + SSH/SCP transfer.
#                        The committed manifest is used READ-ONLY in this mode.
#   -LocalOnly           staging + authoritative-manifest gate ONLY: no pin rewrite,
#                        no file-list write, no archive, no ssh/scp. The temp packet
#                        dir created here is removed in a finally block BEFORE the
#                        success line is printed; any failure also cleans up via the
#                        same finally and exits nonzero.
#   -RegeneratePins      independent LOCAL re-pin entry point: builds its own temp
#                        packet, rewrites packet-inputs-real.sha256 and
#                        packet-files-real.txt from the verified staged bytes, then
#                        exits — it never reaches the transport section.
[CmdletBinding()]
param(
    [switch]$LocalOnly,
    [switch]$RegeneratePins
)
$ErrorActionPreference='Stop'
if($LocalOnly -and $RegeneratePins){throw '-LocalOnly and -RegeneratePins are mutually exclusive'}
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$evidence='docs/superpowers/evidence/2026-11-13-p01-real-prep'
$receipts='docs/superpowers/evidence/2026-11-13-p01-task-card-receipts'
# Transient modes (-LocalOnly / -RegeneratePins) use a throwaway packet dir so
# review runs never collide with the transport-mode packet-real tree (which
# must stay exclusive/fresh). We only ever delete a dir WE created this run.
$createdPacket=$false
if($LocalOnly -or $RegeneratePins){
    $packet=Join-Path $PSScriptRoot ('packet-local-check-{0}' -f [guid]::NewGuid().ToString('N').Substring(0,8))
}else{
    $packet=Join-Path $PSScriptRoot 'packet-real'
    if(Test-Path $packet){if(@(Get-ChildItem $packet -Force).Count){throw 'Existing nonempty packet'}}
}
if(-not (Test-Path $packet)){[IO.Directory]::CreateDirectory($packet) | Out-Null; $createdPacket=$true}
function Copy-Input([string]$relative,[string]$destinationRelative){
    if($relative.StartsWith('/') -or $relative.Contains('\') -or ($relative.Split('/') -contains '..')){throw 'Unsafe path'}
    $source=Join-Path $repo ($relative -replace '/','\')
    $target=Join-Path $packet ($destinationRelative -replace '/','\')
    if(Test-Path $target){throw "Existing staged input: $destinationRelative"}
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target)) | Out-Null
    Copy-Item -LiteralPath $source -Destination $target
}
try {
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
    # 5. authoritative byte gate (identical in all three modes)
    $files=@(Get-ChildItem $packet -Recurse -File | ForEach-Object {$_.FullName.Substring($packet.Length+1) -replace '\\','/'} | Sort-Object)
    $manifestPath=Join-Path $PSScriptRoot 'packet-inputs-real.sha256'
    if(-not (Test-Path $manifestPath)){throw 'Authoritative manifest packet-inputs-real.sha256 is missing'}
    if($RegeneratePins){
        # Independent local entry point: rebuild BOTH pin lists from the staged
        # bytes, then exit before the gate below — regeneration is decoupled
        # from verification, and the default transport path can therefore treat
        # the committed manifest as strictly read-only.
        $manifest=[string[]]($files | ForEach-Object {
            (Get-FileHash -LiteralPath (Join-Path $packet ($_ -replace '/','\'))).Hash.ToLowerInvariant()+'  '+$_})
        [IO.File]::WriteAllLines($manifestPath,$manifest,[Text.UTF8Encoding]::new($false))
        [IO.File]::WriteAllLines((Join-Path $PSScriptRoot 'packet-files-real.txt'),[string[]]$files,[Text.UTF8Encoding]::new($false))
        Write-Output ('PINS REGENERATED LOCALLY from '+$files.Count+' staged files; no archive, no ssh/scp.')
        return
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
    if($LocalOnly){
        # Local-only verification entry point: authoritative gate passed above.
        # No pin/file-list writes, no archive, no ssh/scp. Return (not exit) so
        # the finally block runs FIRST; the success line prints after cleanup.
        Write-Output ('LOCAL-ONLY STAGING CHECK PASSED: '+$files.Count+' files verified against committed manifest; no pin rewrite, no archive, no ssh/scp.')
        return
    }
    # 6. default transport mode: both committed pin lists were consumed read-only
    #    above; regenerating them is exclusively -RegeneratePins' job.
    $filesListPath=Join-Path $PSScriptRoot 'packet-files-real.txt'
    $expectedList=[IO.File]::ReadAllLines($filesListPath) | Where-Object {$_}
    if(compare $expectedList $files){throw 'Staged file list differs from committed packet-files-real.txt (run -RegeneratePins after review)'}
    $archive=Join-Path $PSScriptRoot 'packet-real.tar.gz'
    if(Test-Path $archive){throw 'Existing packet archive'}
    Push-Location $packet
    try{& tar -czf $archive -T $filesListPath;if($LASTEXITCODE -ne 0){throw 'Packet tar failed'}}finally{Pop-Location}
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
} finally {
    # Covers the ENTIRE staging span: whatever we created this run comes down,
    # including on the -LocalOnly/-RegeneratePins `exit 0` paths and on any
    # throw. Transport-mode packet-real is left in place by design (operator
    # inspects it), so we only remove dirs we created AND that are transient.
    if($createdPacket -and (Test-Path $packet)){
        Remove-Item -LiteralPath $packet -Recurse -Force
    }
}
