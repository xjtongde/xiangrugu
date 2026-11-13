[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateRange(1,10)][int]$Partition,
    [Parameter(Mandatory)][ValidatePattern('^[a-z0-9][a-z0-9-]{0,40}$')][string]$RunSuffix,
    [ValidateSet('small','baseline','large','change','baseline-large')][string]$Scenario='small',
    [ValidateSet('first','cancel','retry')][string]$Attempt='first',
    [ValidatePattern('^source-green(-v(?:[2-9]|[1-9][0-9]+))?$')][string]$SourceCopy='source-green-v3'
)
$ErrorActionPreference='Stop'
if($Partition -ne 1 -or $Attempt -ne 'first'){throw 'Fixed owned p01 only'}
$selectedImage=(Get-Content -LiteralPath (Join-Path $PSScriptRoot 'runtime-image.id') -Raw).Trim()
if($Attempt -ne 'first' -and ($Partition -ne 1 -or $Scenario -ne 'coverage')){throw 'Attempt fixture only supports owned p01'}
$runtime='/opt/mydocker/xiangrugu/data/var/batch-runner-request-reader-20261113'
$prepared=if($Scenario -eq 'small'){'small-v2'}else{$Scenario}
$root=$runtime+'/reader-prepare-'+$prepared+'/output/project'
$pidName='large-p'+$Partition.ToString('00')
$attemptSuffix=if($Attempt -eq 'first'){''}else{'-'+$Attempt}
$relative=@(('executions/'+$pidName+'/request.json'),('executions/'+$pidName+$attemptSuffix+'/approval.json'),
    'metadata-repository/datamgmt/config/roots.yaml',('preparations/'+$pidName+'/parent.scope.draft.json'),
    ('preparations/'+$pidName+'/parent.budget.draft.json'),('preparations/'+$pidName+'/partition.selection.draft.json'),
    ('reviews/'+$pidName+$attemptSuffix+'/descriptor.review.json'))
$paths=@($relative | ForEach-Object {$root+'/'+$_})
$output=@(& ssh root@192.168.3.32 ('sha256sum '+($paths -join ' ')))
if($LASTEXITCODE -ne 0 -or $output.Count -ne 7){throw 'Independent metadata pins unavailable'}
$pins=@($output | ForEach-Object {if($_ -notmatch '^([0-9a-f]{64})  /opt/mydocker/xiangrugu/data/var/batch-runner-request-reader-20261113/'){throw 'Malformed external pin'};$Matches[1]})
$record=Join-Path $PSScriptRoot ($RunSuffix+'-pins.json')
if(Test-Path $record){throw 'External selection record exists'}
$selected=[ordered]@{test_fixture_only=$true;real_source_read=$false;new_real_expectations=0;
    partition_id=$pidName;retry=($Attempt -eq 'retry');attempt_kind=$Attempt;scenario=$Scenario;request_sha256=$pins[0];approval_sha256=$pins[1];roots_sha256=$pins[2];
    parent_scope_sha256=$pins[3];parent_budget_sha256=$pins[4];partition_selection_sha256=$pins[5];descriptor_sha256=$pins[6]}
[IO.File]::WriteAllText($record,($selected | ConvertTo-Json)+"`n",[Text.UTF8Encoding]::new($false))
$quiet='test "$(docker top xiangrugu-dev -eo pid,comm | wc -l)" -eq 2 && sleep 4 && test "$(docker top xiangrugu-dev -eo pid,comm | wc -l)" -eq 2'
& ssh root@192.168.3.32 $quiet
if($LASTEXITCODE -ne 0){throw 'Devwatch not idle twice'}
& (Join-Path $PSScriptRoot 'invoke-runtime.ps1') -ImageId $selectedImage `
    -RunSuffix $RunSuffix -RuntimeRoot $runtime -Mode readonly-controlled -SourceCopy $SourceCopy `
    -Revision 8fbc8c97fcf1d818caddf6ab556fa82d986643ed -FixtureSuffix $Scenario `
    -RequestPin $pins[0] -ApprovalPin $pins[1] -RootsPin $pins[2] -LocalLog (Join-Path $PSScriptRoot ($RunSuffix+'.log'))
if($LASTEXITCODE -ne 0){throw 'Owned protocol execution failed; no next partition scheduled'}
