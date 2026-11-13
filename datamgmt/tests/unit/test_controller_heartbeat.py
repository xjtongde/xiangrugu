"""Heartbeat framing including the observed Bash delimiter/timeout race."""
from pathlib import Path
import subprocess

import pytest


HELPER = Path(__file__).resolve().parents[3] / 'scripts/controller-heartbeat.sh'


def test_complete_frame_survives_timeout_after_delimiter_consumption():
    # Real Bash consumes a complete frame, then reproduce the observed status
    # 142. With -n the delimiter is lost; with -N it remains in the variable.
    script = f'''source "{HELPER}"
first=true
read() {{
    builtin read "$@"; local actual=$?
    if "$first" && ((actual == 0)); then first=false; return 142; fi
    return "$actual"
}}
for i in 1 2; do
    if controller_read_heartbeat; then code=0; else code=$?; fi
    printf '%s\\n' "$code"
done
'''
    result = subprocess.run(['bash', '-c', script], input=b'tick\ntick\n',
                            capture_output=True, timeout=5, check=True)
    assert result.stdout == b'0\n0\n'


@pytest.mark.parametrize('payload,expected', [
    (b'tick\n', 0), (b'tick\ntick\n', 0), (b'', 3),
    (b't', 3), (b'tick', 3), (b'\n', 2), (b'tic\n', 2),
    (b'tickt', 2), (b'tick\r\n', 2), (b'noise\n', 2),
])
def test_only_delimited_tick_is_a_heartbeat(payload, expected):
    script = f'''source "{HELPER}"
if controller_read_heartbeat; then code=0; else code=$?; fi
printf '%s\\n' "$code"
'''
    result = subprocess.run(['bash', '-c', script], input=payload,
                            capture_output=True, timeout=5, check=True)
    assert result.stdout == f'{expected}\n'.encode()
    assert result.stderr == b''
