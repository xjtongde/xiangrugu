_negative_field() {
    local file=$1 key=$2 expected=$3
    [[ -f "$file" && ! -L "$file" ]] || return 1
    grep -Eq "\"$key\"[[:space:]]*:[[:space:]]*$expected([[:space:]]*[,}]|[[:space:]]*$)" -- "$file"
}

assert_negative_case() {
    local run=$1 kind=$2 code=$3 changed=$4 request_pin=$5
    local output="$run/output" remaining after
    [[ "$request_pin" =~ ^[0-9a-f]{64}$ && "$code" =~ ^[0-9]+$ && "$code" != 0 && ! -e "$output/batch.json" ]] || return 1
    _negative_field "$output/read-frame-marker.json" first_source_frame_appended true || return 1
    _negative_field "$output/read-frame-marker.json" test_fixture_only true || return 1
    _negative_field "$output/read-frame-marker.json" real_source_read false || return 1
    _negative_field "$run/container-state.json" Running false || return 1
    _negative_field "$run/container-state.json" OOMKilled false || return 1
    _negative_field "$output/monitor.json" process_group_gone true || return 1
    _negative_field "$output/monitor.json" worker_failure_state '"valid"' || return 1
    _negative_field "$output/worker-failure.json" request_sha256 "\"$request_pin\"" || return 1
    _negative_field "$output/worker-failure.json" stage '"object_read_sort"' || return 1
    [[ -d "$output/disk-scratch" && ! -L "$output/disk-scratch" ]] || return 1
    remaining=$(find "$output/disk-scratch" -mindepth 1 -print -quit) || return 1
    [[ -z "$remaining" ]] || return 1
    case "$kind" in
        cancel)
            _negative_field "$run/controller-stop.json" reason '"artificial_cancel"' || return 1
            _negative_field "$output/monitor.json" reason '"cancelled"' || return 1
            _negative_field "$output/worker-failure.json" code '"cancelled"' || return 1
            ;;
        change)
            [[ "$changed" == true && -f "$run/request-change.txt" ]] || return 1
            grep -qx 'OWNED_REQUEST_CHANGED_AFTER_FIRST_FRAME' "$run/request-change.txt" || return 1
            read -r after _ < "$run/request-after-change.sha256" || return 1
            [[ "$after" =~ ^[0-9a-f]{64}$ && "$after" != "$request_pin" ]] || return 1
            _negative_field "$output/monitor.json" reason '"worker_exit"' || return 1
            _negative_field "$output/worker-failure.json" code '"controller_request_changed"' || return 1
            ;;
        *) return 1 ;;
    esac
}
