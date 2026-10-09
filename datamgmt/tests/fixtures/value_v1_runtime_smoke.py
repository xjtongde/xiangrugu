"""Synthetic installed-runtime smoke; stdin harness, not a source adapter."""
import json
import os
from xiangrugu_datamgmt import canonical as c
from xiangrugu_datamgmt.validate import ValueEvidence, ValueInput, compare_ordered

assert os.getuid() == 10001
assert "/workspace/" not in c.__file__
assert c.__file__.startswith("/usr/local/lib/python3.11/site-packages/")
schema = c.ValueSchema("1" * 64, (
    c.ValueColumn("2" * 64, "value", "text", True),
    c.ValueColumn(c.ROW_KEY, "__src_rownum", "bigint", False),
))
limits = c.ValueLimits()
assert c.encode_cell(schema.columns[0], None, limits=limits).hex() == "00"
assert c.encode_cell(schema.columns[0], "", limits=limits).hex() == "010000000000000000"
assert c.encode_cell(schema.columns[0], "\u2400", limits=limits).hex() == "010000000000000003e29080"
evidence = ValueEvidence("synthetic", "runtime-smoke", "3" * 64)
report = compare_ordered(
    schema, ValueInput(schema, iter((("", 1),)), evidence),
    ValueInput(schema, iter((("", 1),)), evidence), expected_count=1, limits=limits,
)
assert report.result == "comparison_equal"
assert report.source_sha256 == report.target_sha256
assert report.compared_fields == 2
print(json.dumps({"runtime_smoke": "passed", "uid": os.getuid(),
                  "module": c.__file__, "report": report.to_dict()}, sort_keys=True))
