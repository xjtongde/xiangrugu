[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidatePattern('^sha256:[0-9a-f]{64}$')][string]$ImageId,
    [Parameter(Mandatory)][ValidatePattern('^[a-z0-9][a-z0-9-]{0,40}$')][string]$RunSuffix,
    [Parameter(Mandatory)][ValidatePattern('^/opt/mydocker/xiangrugu/data/var/batch-runner-[a-z0-9-]+$')][string]$RuntimeRoot,
    [Parameter(Mandatory)][ValidateSet('batch','full','lease-loss','timeout','cancel','disconnect','collector-failure','readonly-prepare','readonly','readonly-writable','readonly-controlled')][string]$Mode,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{40}$')][string]$Revision,
    [Parameter(Mandatory)][string]$LocalLog,
    [ValidatePattern('^[a-z0-9][a-z0-9-]{0,40}$')][string]$FixtureSuffix,
    [ValidatePattern('^[0-9a-f]{64}$')][string]$RequestPin,
    [ValidatePattern('^[0-9a-f]{64}$')][string]$ApprovalPin,
    [ValidatePattern('^[0-9a-f]{64}$')][string]$RootsPin
)
# PowerShell transport only: project execution always occurs on host 32.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'controller-transport-evidence.ps1')
$transportEvidence = $LocalLog + '.controller.jsonl'
if (Test-Path -LiteralPath $transportEvidence) { throw 'Refuse to overwrite transport evidence' }
function Note-TransportEvent([string]$reason, $remoteCode=$null) {
    try { Write-ControllerTransportEvent -Path $transportEvidence -RunSuffix $RunSuffix -Reason $reason -RemoteExitCode $remoteCode }
    catch { Write-Warning 'transport_evidence_unavailable' }
}
$startInfo = [Diagnostics.ProcessStartInfo]::new()
$startInfo.FileName = 'ssh.exe'
$startInfo.Arguments = '-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=5 -o ServerAliveCountMax=2 root@192.168.3.32 "bash /opt/mydocker/xiangrugu/deploy/scripts/run-synthetic-batch.sh ' + $ImageId + ' ' + $RunSuffix + ' ' + $RuntimeRoot + ' ' + $Mode + ' ' + $Revision + '"'
if ($FixtureSuffix) {
    $startInfo.Arguments = $startInfo.Arguments.Substring(0, $startInfo.Arguments.Length - 1) + ' ' + $FixtureSuffix + '"'
}
if ($Mode -eq 'readonly-controlled') {
    if (-not $FixtureSuffix -or -not $RequestPin -or -not $ApprovalPin -or -not $RootsPin) {
        throw 'Controlled mode requires fixture and three externally selected digest pins.'
    }
    $startInfo.Arguments = $startInfo.Arguments.Substring(0, $startInfo.Arguments.Length - 1) + ' ' + $RequestPin + ' ' + $ApprovalPin + ' ' + $RootsPin + '"'
} elseif ($RequestPin -or $ApprovalPin -or $RootsPin) {
    throw 'Digest pins are accepted only in controlled mode.'
}
$startInfo.UseShellExecute = $false
$startInfo.CreateNoWindow = $true
$startInfo.RedirectStandardInput = $true
$startInfo.RedirectStandardOutput = $true
$startInfo.RedirectStandardError = $true
$process = [Diagnostics.Process]::new()
$process.StartInfo = $startInfo
$closed = $false
$processStarted = $false
$transportSeconds = if ($Mode -eq 'readonly-controlled') { 1880 } else { 380 }
try {
    [void]$process.Start()
    $processStarted = $true
    $stdout = $process.StandardOutput.ReadToEndAsync()
    $stderr = $process.StandardError.ReadToEndAsync()
    $timer = [Diagnostics.Stopwatch]::StartNew()
    while (-not $process.HasExited) {
        if ($Mode -eq 'disconnect' -and $timer.Elapsed.TotalSeconds -ge 3 -and -not $closed) {
            Note-TransportEvent artificial_disconnect
            $process.StandardInput.Close()
            $closed = $true
        }
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
    Write-Output ('Remote synthetic runner exited ' + $process.ExitCode)
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
