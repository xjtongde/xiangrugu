$ErrorActionPreference='Stop'
$image=(Get-Content -LiteralPath (Join-Path $PSScriptRoot 'test-image.id') -Raw).Trim()
$remote='/opt/mydocker/xiangrugu/data/var/batch-runner-request-reader-20261113'
foreach($flavor in 'development','installed'){
    $prefix=if($flavor -eq 'development'){'dev'}else{'installed'}
    foreach($mode in 'metadata','remainder','fixture-negative'){
        $suffix=$prefix+'-'+$(if($mode -eq 'fixture-negative'){'fixtures'}else{$mode})
        & (Join-Path $PSScriptRoot 'invoke-tests.ps1') -ImageId $image -RunSuffix $suffix -RuntimeRoot $remote `
            -Mode $mode -Revision 8fbc8c97fcf1d818caddf6ab556fa82d986643ed -SourceCopy source-green-v2 `
            -ExecutionFlavor $flavor -LocalLog (Join-Path $PSScriptRoot ($suffix+'.log'))
        if($LASTEXITCODE -ne 0){throw ('Regression group failed '+$suffix)}
    }
}
