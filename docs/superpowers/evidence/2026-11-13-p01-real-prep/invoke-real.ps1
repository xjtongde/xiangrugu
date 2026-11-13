# Windows PowerShell 5 SSH transport only; project execution stays on host 32.
# Modes: refuse|materialize|real. Expected remote exits: refuse 2 (by design),
# materialize 0, real 0 (staged) or nonzero bounded stop WITH failure evidence.
# The real mode consumes THE single attempt; never rerun it after a stop.
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidatePattern('^sha256:[0-9a-f]{64}$')][string]$ImageId,
    [Parameter(Mandatory)][ValidatePattern('^[a-z0-9][a-z0-9-]{0,40}$')][string]$RunSuffix,
    [Parameter(Mandatory)][ValidateSet('refuse','materialize','real')][string]$Mode,
    [Parameter(Mandatory)][string]$LocalLog,
    [string]$SourceCopy='source-green-v1',
    [string]$MaterializeSuffix='',
    [string]$RequestPin='',
    [string]$ApprovalPin=''
)
$ErrorActionPreference = 'Stop'
$expectedImage='sha256:8f899568909671131b14cc1c06afeef93d6ef1eef7d5d0a1b18c3bf287bd0a0a'
$expectedRevision='8fbc8c97fcf1d818caddf6ab556fa82d986643ed'
$expectedRoots='6235c356fca754a687a2f02998770c9609b20748ade674d0050d86a0a428e07c'
$runtimeRoot='/opt/mydocker/xiangrugu/data/var/batch-runner-real-p01-20261113-a'
if($ImageId -cne $expectedImage){throw 'Require the verified 2026-11-13 runtime image ID'}
if($SourceCopy -notmatch '^source-green(-v(?:[1-9]|[1-9][0-9]+))?$'){throw 'Invalid source copy'}
if($Mode -eq 'real'){
    if($MaterializeSuffix -notmatch '^[a-z0-9][a-z0-9-]{0,40}$'){throw 'MaterializeSuffix required'}
    if($RequestPin -notmatch '^[0-9a-f]{64}$' -or $ApprovalPin -notmatch '^[0-9a-f]{64}$'){throw 'External pins required'}
}
$evidence='docs/superpowers/evidence/2026-11-13-p01-real-prep'
. (Join-Path $PSScriptRoot '../../../../scripts/controller-transport-evidence.ps1')
$transportEvidence = $LocalLog + '.controller.jsonl'
if (Test-Path -LiteralPath $transportEvidence) { throw 'Refuse to overwrite transport evidence' }
function Note-TransportEvent([string]$reason, $remoteCode=$null) {
    try { Write-ControllerTransportEvent -Path $transportEvidence -RunSuffix $RunSuffix -Reason $reason -RemoteExitCode $remoteCode }
    catch { Write-Warning 'transport_evidence_unavailable' }
}
$remoteCommand = 'bash ' + $runtimeRoot + '/' + $SourceCopy + '/' + $evidence + '/run-real.sh ' + $ImageId + ' ' + $RunSuffix + ' ' + $runtimeRoot + ' ' + @{refuse='refuse-no-authorization';materialize='materialize';real='real-readonly'}[$Mode] + ' ' + $expectedRevision
if ($Mode -eq 'real') { $remoteCommand += ' ' + $MaterializeSuffix + ' ' + $RequestPin + ' ' + $ApprovalPin + ' ' + $expectedRoots }
# Real candidate 1800s + host 1830s => transport deadline 1880s (card bound).
$transportSeconds = if ($Mode -eq 'real') { 1880 } else { 380 }
$startInfo = [Diagnostics.ProcessStartInfo]::new()
$startInfo.FileName = 'ssh.exe'
$startInfo.Arguments = '-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=5 -o ServerAliveCountMax=2 root@192.168.3.32 "' + $remoteCommand + '"'
$startInfo.UseShellExecute = $false
$startInfo.CreateNoWindow = $true
$startInfo.RedirectStandardInput = $true
$startInfo.RedirectStandardOutput = $true
$startInfo.RedirectStandardError = $true
$process = [Diagnostics.Process]::new()
$process.StartInfo = $startInfo
$closed = $false
$processStarted = $false
try {
    [void]$process.Start()
    $processStarted = $true
    $stdout = $process.StandardOutput.ReadToEndAsync()
    $stderr = $process.StandardError.ReadToEndAsync()
    $timer = [Diagnostics.Stopwatch]::StartNew()
    while (-not $process.HasExited) {
        if (-not $closed) {
            $heartbeat = [Text.Encoding]::ASCII.GetBytes("tick`n")
            try {
                $process.StandardInput.BaseStream.Write($heartbeat, 0, $heartbeat.Length)
                $process.StandardInput.BaseStream.Flush()
            } catch {
                Note-TransportEvent heartbeat_write_failed
                throw 'SSH controller heartbeat write failed'
            }
        }
        if ($timer.Elapsed.TotalSeconds -ge $transportSeconds) {
            Note-TransportEvent transport_deadline
            $process.StandardInput.Close()
            $closed = $true
            throw 'SSH transport deadline exceeded; remote EOF/lease watchdog must cancel the exact candidate.'
        }
        [void]$process.WaitForExit(2000)
    }
    $process.WaitForExit()
    Note-TransportEvent remote_exit $process.ExitCode
    [IO.File]::WriteAllText($LocalLog, $stdout.Result + $stderr.Result, [Text.UTF8Encoding]::new($false))
    Write-Output ('Remote runner exited ' + $process.ExitCode)
    exit $process.ExitCode
}
catch {
    Note-TransportEvent transport_error
    throw
}
finally {
    if ($processStarted -and -not $closed) {
        Note-TransportEvent stdin_close
        $process.StandardInput.Close()
    }
    if ($processStarted -and -not $process.HasExited) { [void]$process.WaitForExit(20000) }
    $process.Dispose()
}
