"""Owned test only: stop after the first source frame was actually appended."""
import runpy
import sys
import time
from pathlib import Path

from xiangrugu_datamgmt.value_sort import SortWorkspace
from xiangrugu_datamgmt.snapshots import write_json_exclusive

original=SortWorkspace.append
seen=False
def append(self,file,frame):
    global seen
    original(self,file,frame)
    if not seen:
        seen=True
        write_json_exclusive(Path('/data/var/run/read-frame-marker.json'),dict(
            first_source_frame_appended=True,test_fixture_only=True,real_source_read=False))
        while True:
            self.check();time.sleep(.02)
SortWorkspace.append=append
sys.argv=['task_control',*sys.argv[1:]]
runpy.run_module('xiangrugu_datamgmt.task_control',run_name='__main__')
