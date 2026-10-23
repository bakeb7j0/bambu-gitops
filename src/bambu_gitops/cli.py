"""Command line entry point for read-only conformance checks."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .conformance import report


def main(argv=None):
    p = argparse.ArgumentParser(prog="bambu-gitops")
    sub = p.add_subparsers(dest="command", required=True)
    v = sub.add_parser("validate", help="Validate an instance config repository (read-only)")
    v.add_argument("path", type=Path)
    args = p.parse_args(argv)
    result = report(args.path)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
