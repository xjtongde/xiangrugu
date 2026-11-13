# Bounded tick-line framing across Bash read timeouts; never emit input contents.
controller_heartbeat_pending=
controller_read_heartbeat() {
    local part= code
    # Retain the delimiter itself: Bash can time out after consuming a newline.
    # Read only the remainder of this five-character frame, never the next one.
    if IFS= read -r -N "$((5-${#controller_heartbeat_pending}))" -t 1 part; then code=0; else code=$?; fi
    controller_heartbeat_pending+="$part"
    case "$controller_heartbeat_pending" in
        $'tick\n') controller_heartbeat_pending=; return 0 ;;
        ''|t|ti|tic|tick) ;;
        *) controller_heartbeat_pending=; return 2 ;;
    esac
    if (( code == 0 )); then
        controller_heartbeat_pending=
        return 2
    fi
    if (( code == 1 )); then
        controller_heartbeat_pending=
        return 3  # EOF including a partial frame is never a valid heartbeat.
    fi
    if (( code > 128 )); then return 1; fi  # Incomplete; does not renew idle clock.
    controller_heartbeat_pending=
    return 2
}
