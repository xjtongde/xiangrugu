$ErrorActionPreference='Stop'
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
$enc=[Text.UTF8Encoding]::new($false)
& (Join-Path $PSScriptRoot 'verify.ps1') | Tee-Object -FilePath (Join-Path $PSScriptRoot 'native-verification.txt')
git -C $repo diff --check
if($LASTEXITCODE -ne 0){throw 'Whitespace check failed'}
if((& git -C $repo rev-parse HEAD) -cne '8fbc8c97fcf1d818caddf6ab556fa82d986643ed'){throw 'HEAD changed'}
$files=@('AGENTS.md','rules.md','HANDOFF.md','docs/index.md','docs/log.md','docs/improvements.md','datamgmt/README.md','datamgmt/docs/IMPLEMENTATION-PLAN.md',
    'docs/superpowers/evidence/2026-11-08-metadata-reader-integration/verification.json',
    'docs/superpowers/evidence/2026-11-08-metadata-reader-integration/build-inputs.sha256',
    'docs/superpowers/evidence/2026-11-08-metadata-reader-integration/README.md')
foreach($directory in @($PSScriptRoot)){
    $files+=Get-ChildItem -LiteralPath $directory -Recurse -File | Where-Object{$_.Name -notlike 'final-summary-*'} | ForEach-Object{$_.FullName.Substring($repo.Length+1).Replace('\','/')}
}
$files+=@('docs/superpowers/evidence/2026-11-12-p01-throughput/verification.json',
    'docs/superpowers/evidence/2026-11-12-p01-throughput/raw/reader-prepare-large/output/project/executions/large-p01/request.json',
    'docs/superpowers/evidence/2026-11-12-p01-throughput/raw/reader-prepare-large/output/project/project-golden.json')
$files+=Get-Content (Join-Path $PSScriptRoot 'build-inputs.sha256') | ForEach-Object{$_.Substring(66)}
$files=@($files|Sort-Object -Unique)
$manifest=Join-Path $PSScriptRoot 'final-summary-inputs.sha256'
$list=Join-Path $PSScriptRoot 'final-summary-files.txt'
[IO.File]::WriteAllText($manifest,(@($files|ForEach-Object{(Get-FileHash -LiteralPath (Join-Path $repo $_)).Hash.ToLower()+'  '+$_}) -join "`n")+"`n",$enc)
[IO.File]::WriteAllText($list,((@($files)+$manifest.Substring($repo.Length+1).Replace('\','/')) -join "`n")+"`n",$enc)
$archive=Join-Path $PSScriptRoot 'final-summary-v1.tar.gz'
tar -czf $archive -C $repo -T $list
if($LASTEXITCODE -ne 0){throw 'Summary tar failed'}
$digest=(Get-FileHash -LiteralPath $archive).Hash.ToLower()
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'final-summary-v1.sha256'),$digest+"  final-summary-v1.tar.gz`n",$enc)
$remote='/opt/mydocker/xiangrugu/data/var/batch-runner-request-reader-20261113'
scp $archive ('root@192.168.3.32:'+$remote+'/final-summary-v1.tar.gz')
if($LASTEXITCODE -ne 0){throw 'Summary transfer failed'}
$relativeManifest=$manifest.Substring($repo.Length+1).Replace('\','/')
$receipt=@(& ssh root@192.168.3.32 "set -eu; cd '$remote'; test `"`$(sha256sum final-summary-v1.tar.gz | cut -d ' ' -f1)`" = '$digest'; mkdir final-summary-v1; nice -n 19 ionice -c 3 tar -xzf final-summary-v1.tar.gz -C final-summary-v1; cd final-summary-v1; sha256sum -c '$relativeManifest'")
if($LASTEXITCODE -ne 0){throw 'Remote summary check failed'}
$receipt+=('ARCHIVE_SHA256 '+$digest)
$receipt+=('VERIFIED_FILES '+$files.Count)
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'final-summary-sync.txt'),($receipt -join "`n")+"`n",$enc)
Write-Output ('Installed reader evidence handoff verified: '+$files.Count+' files; '+$digest)
