$ErrorActionPreference='Stop'
$image=(Get-Content -LiteralPath (Join-Path $PSScriptRoot 'runtime-image.id') -Raw).Trim()
$remote='/opt/mydocker/xiangrugu/data/var/batch-runner-request-reader-20261113'
function Prepare([string]$suffix){
    & (Join-Path $PSScriptRoot 'invoke-runtime.ps1') -ImageId $image -RunSuffix $suffix -RuntimeRoot $remote `
        -Mode readonly-prepare -Revision 8fbc8c97fcf1d818caddf6ab556fa82d986643ed -SourceCopy source-green-v2 `
        -LocalLog (Join-Path $PSScriptRoot ($suffix+'.log'))
    if($LASTEXITCODE -ne 0){throw ('Fixture preparation failed '+$suffix)}
}
function Execute([string]$suffix,[string]$scenario){
    & (Join-Path $PSScriptRoot 'invoke-owned.ps1') -Partition 1 -RunSuffix $suffix -Scenario $scenario -SourceCopy source-green-v2
    if($LASTEXITCODE -ne 0){throw ('Artificial execution failed '+$suffix)}
}
Prepare reader-prepare-change
Execute reader-request-change change
Prepare reader-prepare-large
Execute reader-large-cancel large
Execute reader-large large
