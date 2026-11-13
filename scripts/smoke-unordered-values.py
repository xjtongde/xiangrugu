"""Synthetic-only check of the packaged unordered comparator, without pytest."""
import argparse
import json
from pathlib import Path

from xiangrugu_datamgmt.unordered_values import UnorderedColumn, UnorderedSchema, UnorderedLimits
from xiangrugu_datamgmt.unordered_validate import UnorderedInput, UnorderedEvidence, compare_unordered


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check synthetic values only; no source or database access")
    parser.add_argument("--scratch-parent", type=Path, required=True)
    args = parser.parse_args(argv)
    schema = UnorderedSchema("b"*64, (UnorderedColumn(0, "a"*64, "text", True),))
    def inp(values, name):
        return UnorderedInput(schema, iter(values), UnorderedEvidence("synthetic", name, "1"*64))
    try:
        equal = compare_unordered(schema, inp([("",), (None,), ("",)], "source"),
            inp([(None,), ("",), ("",)], "target"), limits=UnorderedLimits(),
            scratch_parent=args.scratch_parent).to_dict()
        missing = compare_unordered(schema, inp([("",), (None,), ("",)], "source"),
            inp([(None,), ("",)], "target"), limits=UnorderedLimits(),
            scratch_parent=args.scratch_parent).to_dict()
        if (equal["result"] != "comparison_equal" or not equal["cleanup_complete"]
                or missing["result"] != "comparison_failed" or not missing["cleanup_complete"]
                or missing["missing_rows"] != 1 or missing["difference_patterns"] != 1):
            raise ValueError("smoke_failed")
        import xiangrugu_datamgmt.unordered_validate as module
        print(json.dumps({"equal": equal["result"], "missing": missing["result"],
                          "module_path": module.__file__, "source_count": equal["source_count"],
                          "missing_rows": missing["missing_rows"]}))
        return 0
    except Exception:
        print(json.dumps({"result": "smoke_failed"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
