"""Record installed product origins, then exec the selected owned worker."""
import hashlib
import importlib
import os
from pathlib import Path
import sys
import sysconfig

from xiangrugu_datamgmt.snapshots import write_json_exclusive

expected=Path(sysconfig.get_paths()['purelib'])/'xiangrugu_datamgmt'
modules={}
for name in ('project_partition','project_partition_coverage','task_control','readonly_batch','candidate_supervisor'):
    module=importlib.import_module('xiangrugu_datamgmt.'+name);path=Path(module.__file__)
    if path.parent!=expected:raise ValueError('installed_origin')
    modules[name]=dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
write_json_exclusive(Path('/data/var/run/installed-origin.json'),dict(installed_product_verified=True,modules=modules))
os.execvp(sys.executable,[sys.executable,*sys.argv[1:]])
