# Sourced by the host-side controller. Static metadata only, never command/input text.
controller_phase=runner
controller_event_sequence=0
controller_first_trigger=false
controller_writing=false
controller_pending_signals=()
controller_record() {
    local event=$1 reason=$2 observed_signal=${3:-null} code=${4:-0} container=null row first=false
    case "$event" in trigger|stop_requested|kill_requested|runner_exit) ;; *) return 1 ;; esac
    case "$reason" in signal|invalid_heartbeat|controller_eof|controller_idle|artificial_cancel|host_deadline|collector_failure|runner_error|cleanup|runner_exit) ;; *) return 1 ;; esac
    case "$observed_signal" in TERM|INT|HUP) observed_signal="\"$observed_signal\"" ;; null) ;; *) return 1 ;; esac
    [[ "$code" =~ ^[0-9]+$ && "$suffix" =~ ^[a-z0-9][a-z0-9-]{0,40}$ ]] || return 1
    if [[ -n "${id:-}" ]]; then
        [[ "$id" =~ ^[0-9a-f]{64}$ ]] || return 1
        container="\"$id\""
    fi
    [[ ! -L "$run/controller-events.jsonl" && ! -L "$run/controller-stop.json" ]] || return 1
    controller_event_sequence=$((controller_event_sequence+1))
    printf -v row '{"version":1,"sequence":%s,"event":"%s","reason":"%s","signal":%s,"run_suffix":"%s","container_id":%s,"elapsed_seconds":%s,"exit_code":%s,"ready_for_import":false}' \
        "$controller_event_sequence" "$event" "$reason" "$observed_signal" "$suffix" "$container" "$SECONDS" "$code"
    # Claim before any external command can let a pending signal trap reenter.
    if [[ "$event" == trigger ]] && ! "$controller_first_trigger"; then
        controller_first_trigger=true
        first=true
    fi
    printf '%s\n' "$row" >> "$run/controller-events.jsonl" || return 1
    if "$first"; then
        # First observed trigger survives later cleanup/errors; never overwrite it.
        (set -o noclobber; printf '%s\n' "$row" > "$run/controller-stop.json") || return 1
    fi
    # sync FILE uses per-file fsync; do not sync the entire shared filesystem.
    # Best effort is bounded and never replaces the existing stop/kill budgets.
    timeout --kill-after=1 1 sync -- "$run/controller-events.jsonl" || return 1
    if "$first"; then timeout --kill-after=1 1 sync -- "$run/controller-stop.json" || return 1; fi
    timeout --kill-after=1 1 sync -- "$run" || return 1
}
controller_note() {
    local failed=false pending
    controller_writing=true
    controller_record "$@" || failed=true
    controller_writing=false
    if "$failed"; then echo controller_evidence_unavailable >&2; fi
    # Defer trap reentry even between Bash builtins, not just during sync.
    while ((${#controller_pending_signals[@]})); do
        pending=${controller_pending_signals[0]}
        controller_pending_signals=("${controller_pending_signals[@]:1}")
        controller_note trigger signal "$pending"
    done
}
controller_signal() {
    cancel_requested=true
    if "$controller_writing"; then
        controller_pending_signals+=("$1")
    else
        controller_note trigger signal "$1"
    fi
}
controller_error() {
    local code=$1 reason=runner_error
    # Parent assignment/function failure records the error once; subshell state
    # cannot safely update the parent's sequence or first-trigger flag.
    [[ "$BASH_SUBSHELL" == 0 ]] || return 0
    [[ "$controller_phase" != collector ]] || reason=collector_failure
    if ! "$controller_first_trigger"; then controller_note trigger "$reason" null "$code"; fi
}
