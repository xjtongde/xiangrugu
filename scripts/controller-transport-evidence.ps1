# Native PowerShell transport metadata only; no exception text or heartbeat bytes.
function Write-ControllerTransportEvent {
    param([string]$Path, [string]$RunSuffix,
        [ValidateSet('remote_exit','transport_deadline','heartbeat_write_failed','transport_error','artificial_disconnect','stdin_close')][string]$Reason,
        [AllowNull()][object]$RemoteExitCode = $null)
    if ($RunSuffix -notmatch '^[a-z0-9][a-z0-9-]{0,40}$') { throw 'Invalid transport run identity' }
    if ($null -ne $RemoteExitCode -and $RemoteExitCode -isnot [int]) { throw 'Invalid transport exit code' }
    $row = [ordered]@{version=1; run_suffix=$RunSuffix; layer='windows_ssh_transport';
        reason=$Reason; utc=[DateTime]::UtcNow.ToString('o'); remote_exit_code=$RemoteExitCode;
        ready_for_import=$false} | ConvertTo-Json -Compress
    $bytes = [Text.UTF8Encoding]::new($false).GetBytes($row + "`n")
    $stream = [IO.FileStream]::new($Path, [IO.FileMode]::Append, [IO.FileAccess]::Write, [IO.FileShare]::Read)
    try { $stream.Write($bytes, 0, $bytes.Length); $stream.Flush($true) }
    finally { $stream.Dispose() }
}
