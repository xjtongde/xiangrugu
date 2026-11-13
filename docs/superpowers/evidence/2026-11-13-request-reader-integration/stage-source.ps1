[CmdletBinding()]
param([Parameter(Mandatory)][ValidatePattern('^source-(red|green)(-v(?:[2-9]|[1-9][0-9]+))?$')][string]$Name)
$ErrorActionPreference='Stop'
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
$remote='/opt/mydocker/xiangrugu/data/var/batch-runner-request-reader-20261113'
$files=@()
foreach($directory in @('datamgmt/src','datamgmt/tests','datamgmt/config','datamgmt/contracts','scripts')) {
    $files+=Get-ChildItem (Join-Path $repo $directory) -Recurse -File | Where-Object FullName -NotMatch '__pycache__|\.pyc$' | ForEach-Object {$_.FullName.Substring($repo.Length+1) -replace '\\','/'}
}
$files+=@('docs/superpowers/evidence/2026-10-24-real-partition-control/build-inputs.sha256','Dockerfile','.dockerignore','docker-compose.yml','datamgmt/pyproject.toml','datamgmt/requirements.lock','datamgmt/requirements-dev.lock',
    'docs/superpowers/plans/2026-10-09-sqlite-remaining-types.scope.json',
    'docs/superpowers/evidence/2026-10-08-text-source-values/text-source-value-expectations.draft.json')
$files+=Get-ChildItem $PSScriptRoot -Recurse -File | Where-Object Extension -In '.sh','.ps1','.py' | ForEach-Object {$_.FullName.Substring($repo.Length+1) -replace '\\','/'}
if(Test-Path (Join-Path $PSScriptRoot 'build-inputs-b.sha256')){$files+='docs/superpowers/evidence/2026-10-24-real-partition-control/build-inputs-b.sha256'}
$files+=@('docs/superpowers/evidence/2026-10-24-real-partition-control/run-tests.sh','docs/superpowers/evidence/2026-10-24-real-partition-control/installed-origin.py')
$files+=@('docs/superpowers/evidence/2026-10-24-real-partition-control/cancel-probe.py','docs/superpowers/evidence/2026-10-24-real-partition-control/prepare-retry.py')
$files+='docs/superpowers/evidence/2026-11-08-metadata-reader-integration/assert-negative.sh'
if(Test-Path (Join-Path $PSScriptRoot 'build-inputs.sha256')){$files+='docs/superpowers/evidence/2026-11-13-request-reader-integration/build-inputs.sha256'}
$files=@($files | Sort-Object -Unique)
if($files | Where-Object {$_ -match '(^|/)(\.git|\.secrets|data|usedata)(/|$)|(^|/)\.env($|\.)|\.(pem|key|p12|pfx)$'}){throw 'Unsafe source member'}
$manifest=Join-Path $PSScriptRoot ($Name+'-files.txt')
$digests=Join-Path $PSScriptRoot ($Name+'-inputs.sha256')
$archive=Join-Path $PSScriptRoot ($Name+'.tar.gz')
if(Test-Path $archive){throw 'Source archive already exists'}
[IO.File]::WriteAllLines($manifest,[string[]]$files,[Text.UTF8Encoding]::new($false))
$hashes=@($files | ForEach-Object {((Get-FileHash (Join-Path $repo $_) -Algorithm SHA256).Hash.ToLowerInvariant())+'  '+$_})
[IO.File]::WriteAllLines($digests,[string[]]$hashes,[Text.UTF8Encoding]::new($false))
Push-Location $repo
try { & tar -czf $archive -T $manifest;if($LASTEXITCODE -ne 0){throw 'Source archive failed'} } finally {Pop-Location}
& ssh root@192.168.3.32 "mkdir -p '$remote'; mkdir '$remote/$Name'"
if($LASTEXITCODE -ne 0){throw 'Exclusive source directory failed'}
& scp -q -O $archive "root@192.168.3.32:$remote/$Name.tar.gz"
if($LASTEXITCODE -ne 0){throw 'Source transfer failed'}
& scp -q -O $digests "root@192.168.3.32:$remote/$Name/SOURCE-INPUTS.sha256"
if($LASTEXITCODE -ne 0){throw 'Source digest transfer failed'}
& ssh root@192.168.3.32 "tar -xzf '$remote/$Name.tar.gz' -C '$remote/$Name' && cd '$remote/$Name' && sha256sum -c SOURCE-INPUTS.sha256 > ../$Name-check.txt && bash -n docs/superpowers/evidence/2026-10-24-real-partition-control/run-tests.sh"
if($LASTEXITCODE -ne 0){throw 'Source digest or shell syntax check failed'}
Write-Output ('Staged '+$files.Count+' exact Windows inputs into '+$remote+'/'+$Name)
