import json, sys, importlib.util, pathlib
# 把 srccheck 作为包目录的父，加载 xiangrugu_datamgmt
sys.path.insert(0, '/tmp/a01pkg')
import shutil, os
# srccheck 本身就是包目录（名字不对），复制为正确包名
dst = '/tmp/a01pkg/xiangrugu_datamgmt_patched'
if os.path.isdir(dst): shutil.rmtree(dst)
shutil.copytree('/tmp/a01pkg/srccheck', dst)
import xiangrugu_datamgmt_patched.contracts as C
print('MODULE_FILE:', C.__file__)
print('HAS_PK:', hasattr(C, 'PrimaryKey'))
s = C.contract_schema()
print('SCHEMA_JSON:')
print(json.dumps(s, ensure_ascii=False, indent=2, sort_keys=True))
