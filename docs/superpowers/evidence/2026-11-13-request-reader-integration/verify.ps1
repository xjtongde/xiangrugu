$ErrorActionPreference='Stop'
function Require($ok,$why){if(-not $ok){throw $why}}
function Json($file){Get-Content -LiteralPath $file -Raw|ConvertFrom-Json}
function Sha($file){(Get-FileHash -LiteralPath $file).Hash.ToLower()}
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
$raw=Join-Path $PSScriptRoot 'raw'
foreach($line in Get-Content "$PSScriptRoot/collection.sha256"){
    Require ($line -cmatch '^([a-f0-9]{64})  (raw.tar.gz|raw.sha256)$') 'Archive digest format'
    Require ((Sha (Join-Path $PSScriptRoot $Matches[2])) -ceq $Matches[1]) 'Archive digest mismatch'
}
$manifest=@(Get-Content "$PSScriptRoot/raw.sha256")
foreach($line in $manifest){
    Require ($line -cmatch '^([a-f0-9]{64})  (\./[a-zA-Z0-9_./-]+)$') 'Evidence digest format'
    Require (-not $Matches[2].Contains('..') -and -not $Matches[2].Contains('/fixture/snapshots/') -and -not $Matches[2].Contains('/disk-scratch/')) 'Evidence path boundary'
    Require ((Sha (Join-Path $raw $Matches[2])) -ceq $Matches[1]) 'Raw evidence digest mismatch'
}
$build=@{}
foreach($line in Get-Content (Join-Path $PSScriptRoot 'build-inputs.sha256')){$build[$line.Substring(66)]=$line.Substring(0,64)}
Require ($build.Count -eq 135) 'Build input count'
foreach($entry in $build.GetEnumerator()){Require ((Sha (Join-Path $repo $entry.Key)) -ceq $entry.Value) ('Build bytes changed '+$entry.Key)}
foreach($target in 'test','runtime'){
    Require ((Get-Content "$raw/build/build-$target.exit" -Raw).Trim() -eq '0') ('Build result '+$target)
    Require ((Get-Content "$raw/build/$target-image.id" -Raw).Trim() -ceq (Get-Content "$PSScriptRoot/$target-image.id" -Raw).Trim()) ('Build image identity '+$target)
}
$testRuns=@('request-reader-red','request-reader-green','dev-metadata','dev-remainder','dev-fixtures','installed-metadata','installed-remainder','installed-fixtures')
$runtimeRuns=@('reader-prepare-change','reader-request-change','reader-prepare-large','reader-large-cancel','reader-large')
foreach($name in $testRuns+$runtimeRuns){
    $run="$raw/$name"
    $config=Json "$run/host-config.json"
    $state=Json "$run/container-state.json"
    $monitor=Json "$run/output/monitor.json"
    $limits=Json "$run/output/limits.json"
    Require ($config.NanoCpus -eq 500000000 -and $config.Memory -eq 805306368 -and $config.MemorySwap -eq 805306368 -and $config.PidsLimit -eq 128 -and $config.NetworkMode -ceq 'none' -and $config.ReadonlyRootfs) "Candidate caps $name"
    $development=$name.StartsWith('dev-') -or $name -in @('request-reader-red','request-reader-green')
    foreach($mount in $config.Mounts){Require (-not $mount.Source.StartsWith('/mnt/') -and -not $mount.Target.StartsWith('/data/imports') -and -not $mount.Target.StartsWith('/usr/local/lib/') -and ($development -or $mount.Target -cne '/workspace')) 'Unexpected source or product mount'}
    Require ($limits.'cpu.max' -ceq '50000 100000' -and $limits.'memory.max' -ceq '805306368' -and $limits.'memory.swap.max' -ceq '0' -and $limits.worker_nice -eq 19 -and $limits.worker_ionice -ceq 'idle') 'Actual cgroup and priority'
    Require (-not $state.Running -and -not $state.OOMKilled -and $monitor.process_group_gone -and $monitor.cgroup_stats.'memory.swap.current' -ceq '0') 'Candidate terminal state'
    foreach($sample in $monitor.samples){Require ($sample.services_healthy -and $sample.swap_out_pages -eq $monitor.samples[0].swap_out_pages) 'Service or swap change'}
    Require ((Get-Content "$run/services-before.txt" -Raw) -ceq (Get-Content "$run/services-after.txt" -Raw)) 'PG baseline changed'
    $id=(Get-Content "$run/container-id.txt" -Raw).Trim()
    Require ((Get-Content "$raw/absence.txt") -contains "CONFIRMED_ABSENT $id") 'Exact candidate absence'
    if(-not $development){
        $origin=Json "$run/output/installed-origin.json"
        Require ($origin.installed_product_verified -and @($origin.modules.PSObject.Properties).Count -eq 7) 'Seven installed modules'
        foreach($module in $origin.modules.PSObject.Properties){Require ($module.Value.path.StartsWith('/usr/local/lib/python3.11/site-packages/xiangrugu_datamgmt/') -and $module.Value.sha256 -ceq $build['datamgmt/src/xiangrugu_datamgmt/'+$module.Name+'.py']) 'Installed module digest'}
    }
}
$absence=@(Get-Content "$raw/absence.txt")
Require ($absence.Count -eq 13 -and @($absence|Select-Object -Unique).Count -eq 13) 'Exact candidate count'
[xml]$red=Get-Content "$raw/request-reader-red/output/full.xml" -Raw
[xml]$green=Get-Content "$raw/request-reader-green/output/full.xml" -Raw
Require ([int]$red.testsuites.testsuite.tests -eq 8 -and [int]$red.testsuites.testsuite.errors -eq 8 -and (Get-Content "$raw/request-reader-red/worker.log" -Raw).Contains('ImportError')) 'Missing implementation reproduced'
Require ([int]$green.testsuites.testsuite.tests -eq 8 -and [int]$green.testsuites.testsuite.errors -eq 0 -and [int]$green.testsuites.testsuite.failures -eq 0 -and [int]$green.testsuites.testsuite.skipped -eq 0) 'Focused checks passed including fast path'
$suiteCounts=@();$identities=@{};$installedFastPath=$false
foreach($name in $testRuns[2..7]){
    [xml]$xml=Get-Content "$raw/$name/output/full.xml" -Raw
    $suite=$xml.testsuites.testsuite
    $family=$name.Split('-')[0]
    Require ([int]$suite.errors -eq 0 -and [int]$suite.failures -eq 0) ('Regression group '+$name)
    foreach($case in $suite.testcase){
        $key=$family+'|'+$case.classname+'|'+$case.name
        Require (-not $identities.ContainsKey($key)) ('Repeated test '+$key)
        $identities[$key]=$true
        if($family -eq 'installed' -and $case.name -ceq 'test_supported_fast_path_reopens_current_regular_file'){$installedFastPath=$null -eq $case.skipped}
    }
    $suiteCounts+=[ordered]@{name=$name;tests=[int]$suite.tests;skipped=[int]$suite.skipped}
}
$dev=@($suiteCounts|Where-Object{$_.name.StartsWith('dev-')})
$installed=@($suiteCounts|Where-Object{$_.name.StartsWith('installed-')})
Require (($dev.tests|Measure-Object -Sum).Sum -eq 1347 -and ($dev.skipped|Measure-Object -Sum).Sum -eq 0) 'Complete development suite'
Require (($installed.tests|Measure-Object -Sum).Sum -eq 1347 -and ($installed.skipped|Measure-Object -Sum).Sum -eq 23 -and $installedFastPath) 'Complete installed suite and actual fast-path test'
foreach($name in 'reader-request-change','reader-large-cancel'){
    $run="$raw/$name"
    $monitor=Json "$run/output/monitor.json"
    $failure=Json "$run/output/worker-failure.json"
    $pin=(Json "$PSScriptRoot/$name-pins.json").request_sha256
    $marker=Json "$run/output/read-frame-marker.json"
    Require ($marker.first_source_frame_appended -and $marker.test_fixture_only -and -not $marker.real_source_read) 'Negative first-frame marker'
    Require (-not (Test-Path "$run/output/batch.json") -and $monitor.worker_failure_state -ceq 'valid' -and $monitor.worker_exit_code -ne 0 -and $failure.stage -ceq 'object_read_sort' -and $failure.request_sha256 -ceq $pin) 'Negative stopped without publication'
    Require ((Sha "$run/output/worker-failure.json") -ceq $monitor.worker_failure_sha256 -and (Get-Content "$raw/final-state.txt") -contains "SCRATCH_EMPTY $name") 'Negative failure identity and scratch'
    if($name -ceq 'reader-request-change'){
        Require ($failure.code -ceq 'controller_request_changed' -and $monitor.reason -ceq 'worker_exit' -and (Sha "$run/request-before-change.json") -ceq $pin -and (Get-Content "$run/request-change.txt" -Raw).Trim() -ceq 'OWNED_REQUEST_CHANGED_AFTER_FIRST_FRAME') 'Request change rejected after first row'
    }else{
        Require ($failure.code -ceq 'cancelled' -and $monitor.reason -ceq 'cancelled' -and (Json "$run/controller-stop.json").reason -ceq 'artificial_cancel') 'Cancellation after first row'
    }
}
$fixture="$raw/reader-prepare-large/output/project"
$gold=(Json "$fixture/project-golden.json").objects[0]
$receipt=Json "$fixture/fixture-receipt.json"
Require ($receipt.test_fixture_only -and -not $receipt.real_source_read -and $gold.expected_count -eq 465284 -and $gold.field_count -eq 3722272) 'Fixed artificial fixture'
$scope=Json "$fixture/executions/large-p01/scope.json"
Require (@($scope.objects).Count -eq 1 -and ($scope.objects[0].columns.pg_type -join ' ') -ceq 'bigint bigint bigint bigint text text text text') 'Fixed p01 column types'
$pins=Json "$PSScriptRoot/reader-large-pins.json"
Require ((Sha "$fixture/executions/large-p01/request.json") -ceq $pins.request_sha256 -and (Sha "$fixture/executions/large-p01/approval.json") -ceq $pins.approval_sha256 -and (Sha "$fixture/metadata-repository/datamgmt/config/roots.yaml") -ceq $pins.roots_sha256) 'Raw fixture pin binding'
$run="$raw/reader-large"
$monitor=Json "$run/output/monitor.json"
$profile=Json "$run/output/profile.json"
Require ($profile.test_fixture_only -and -not $profile.real_source_read -and $profile.checks_skipped -eq 0 -and $profile.worker_exit_code -eq $monitor.worker_exit_code) 'Profile exit and scope'
Require ($profile.request_reader -ceq 'installed') 'Installed request reader identity'
Require (@($profile.phases|Where-Object{$_.measurements.request_reader_fallback.calls -gt 0}).Count -eq 0) 'Unexpected installed-reader fallback'
$baselineRoot=Join-Path $repo 'docs/superpowers/evidence/2026-11-12-p01-throughput'
$baseline=Json "$baselineRoot/verification.json"
$baselineFixture="$baselineRoot/raw/reader-prepare-large/output/project"
$oldRequest=Json "$baselineFixture/executions/large-p01/request.json"
$request=Json "$fixture/executions/large-p01/request.json"
Require ($request.expected_sha256 -ceq $oldRequest.expected_sha256 -and (Sha "$fixture/project-golden.json") -ceq (Sha "$baselineFixture/project-golden.json")) 'Baseline artificial bytes differ'
$phaseRows=@();$previous=$null
foreach($phase in $profile.phases){
    if($null -ne $previous){Require (($previous.start_ns+$previous.elapsed_ns) -eq $phase.start_ns) 'Discontinuous phase timing'}
    $read=[long]$phase.measurements.request_read.elapsed_ns
    $mount=[long]$phase.measurements.request_mount_check.elapsed_ns
    Require ($phase.elapsed_ns -ge 0 -and $read+$mount -le $phase.elapsed_ns) 'Invalid measurement times'
    $phaseRows+=[ordered]@{name=$phase.name;elapsed_seconds=$phase.elapsed_ns/1e9;request_read_seconds=$read/1e9;mount_check_seconds=$mount/1e9;request_read_calls=[long]$phase.measurements.request_read.calls;mount_check_calls=[long]$phase.measurements.request_mount_check.calls;sqlite_next_calls=[long]$phase.measurements.sqlite_next_inclusive.calls;sqlite_next_inclusive_seconds=([long]$phase.measurements.sqlite_next_inclusive.elapsed_ns)/1e9}
    $previous=$phase
}
Require (($previous.start_ns+$previous.elapsed_ns) -eq $profile.elapsed_ns) 'Profile terminal timing'
$complete=Test-Path "$run/output/batch.json"
if($complete){
    $batch=Json "$run/output/batch.json"
    Require ($monitor.status -ceq 'SOURCE_ONLY_WORKER_COMPLETED' -and $monitor.worker_exit_code -eq 0 -and $batch.complete -and $batch.full_snapshot_verified_this_run -and $batch.file_digest_passes -eq 2 -and -not $batch.raw_values_emitted -and -not $batch.postgresql_connected -and -not $batch.ready_for_import) 'Complete artificial terminal state'
    Require ($batch.controller_request_sha256 -ceq $pins.request_sha256 -and @($batch.objects).Count -eq 1) 'Batch identity'
    Require ($batch.image_id -ceq (Get-Content "$PSScriptRoot/runtime-image.id" -Raw).Trim()) 'Installed runtime image identity'
    foreach($field in 'source_object_id','schema_hash','expected_count','field_count','expected_sha256'){Require ($batch.objects[0].$field -ceq $gold.$field) ('Independent golden '+$field)}
    Require ($batch.objects[0].stream_bytes -eq $gold.canonical_stream_bytes -and $batch.source_sha256_before -ceq $request.expected_sha256 -and $batch.source_sha256_after -ceq $request.expected_sha256 -and $batch.objects[0].cleanup_complete) 'Complete stream and file digests'
    Require ($monitor.max_seconds -eq 1800 -and $monitor.final_sample_sequence -gt $monitor.final_sample_after_sequence) 'Fresh final sample within original deadline'
}else{
    Require ($monitor.status -ceq 'SOURCE_ONLY_WORKER_STOPPED' -and $monitor.worker_exit_code -ne 0 -and $monitor.worker_failure_state -ceq 'valid') 'Artificial stopped terminal state'
    Require ((Sha "$run/output/worker-failure.json") -ceq $monitor.worker_failure_sha256 -and $monitor.worker_failure.request_sha256 -ceq $pins.request_sha256) 'Failure identity'
}
Require ((Get-Content "$raw/final-state.txt") -contains 'SCRATCH_EMPTY reader-large') 'Scratch is not empty'
$record=[ordered]@{as_of='2026-11-13';status='INSTALLED_REQUEST_READER_ARTIFICIAL_VERIFIED';fixture_rows=$gold.expected_count;fixture_fields=$gold.field_count;fixture_stream_bytes=$gold.canonical_stream_bytes;instrumented=$true;measurement_overhead_calibrated=$false;sqlite_next_contains_request_checks=$true;complete=$complete;stop_reason=$monitor.reason;worker_failure=$monitor.worker_failure;supervisor_elapsed_seconds=$monitor.elapsed_seconds;worker_elapsed_seconds=$profile.elapsed_ns/1e9;peak_memory_bytes=[long]$monitor.cgroup_stats.'memory.peak';phase_metrics=$phaseRows;raw_members=$manifest.Count;removed_candidates=13;real_source_read=$false;new_real_expectations=0;coverage_complete_tables=68;coverage_total_tables=78;task8_complete=$false;ready_for_import=$false}
$record.request_checks_seconds=($phaseRows.request_read_seconds|Measure-Object -Sum).Sum+($phaseRows.mount_check_seconds|Measure-Object -Sum).Sum
$record.request_checks_percent=100*$record.request_checks_seconds/$record.worker_elapsed_seconds
$record.last_observed_phase=$phaseRows[-1].name
$events=@(Get-Content "$run/controller-events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json})
Require (@($events|Where-Object {$_.reason -ceq 'invalid_heartbeat'}).Count -eq 0) 'Unexpected heartbeat rejection'
$record.invalid_heartbeat_observed=$false
$record.scratch_empty=$true
$record.baseline_supervisor_elapsed_seconds=$baseline.supervisor_elapsed_seconds
$record.baseline_complete=$baseline.complete
$record.artificial_sqlite_sha256=$request.expected_sha256
$record.installed_fast_path_verified=$true
$record.request_reader_fallback_calls=0
$record.development_passed=1347
$record.installed_passed=1324
$record.installed_skipped=23
$record.test_groups=$suiteCounts
$record.actual_negative_triggers_verified=$true
$record.same_input_completed_phases=@(foreach($name in 'read_encode_bucket','chunk_sort'){
    $old=@($baseline.phase_metrics|Where-Object {$_.name -ceq $name})[0]
    $new=@($phaseRows|Where-Object {$_.name -ceq $name})[0]
    if($null -ne $new){[ordered]@{name=$name;baseline_seconds=$old.elapsed_seconds;installed_seconds=$new.elapsed_seconds;baseline_request_reads=$old.request_read_calls;installed_request_reads=$new.request_read_calls;baseline_mount_checks=$old.mount_check_calls;installed_mount_checks=$new.mount_check_calls}}
})
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'verification.json'),($record|ConvertTo-Json -Depth 10)+"`n",[Text.UTF8Encoding]::new($false))
$phaseRows|ForEach-Object{[pscustomobject]$_}|Format-Table name,elapsed_seconds,request_read_seconds,mount_check_seconds,sqlite_next_calls
