"""Command-line entry points for distributor demonstration data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .audit import audit_scenario
from .config import default_config
from .generator import build_development_suite, generate_scenario
from .snapshot import export_csv


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate", help="Generate one development scenario")
    generate.add_argument("--family", default="supplier_disruption")
    generate.add_argument("--seed", type=int, default=1101)
    generate.add_argument("--output", type=Path, required=True)
    validate = sub.add_parser("validate", help="Audit existing scenario databases")
    validate.add_argument("--operational", type=Path, required=True)
    validate.add_argument("--evaluator", type=Path)
    export = sub.add_parser("export", help="Export a dated operational CSV snapshot")
    export.add_argument("--operational", type=Path, required=True)
    export.add_argument("--as-of", required=True)
    export.add_argument("--phase", choices=("end_of_day", "before_ordering"), default="end_of_day")
    export.add_argument("--output", type=Path, required=True)
    suite = sub.add_parser("suite", help="Build the 18-scenario development report")
    suite.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "generate":
        result = generate_scenario(default_config(args.family, args.seed), args.output)
    elif args.command == "validate":
        result = audit_scenario(args.operational, args.evaluator)
    elif args.command == "export":
        files = export_csv(args.operational, args.output, args.as_of, phase=args.phase)
        result = {"files_written": [str(path) for path in files]}
    else:
        result = build_development_suite(args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    if result.get("passed") is False or result.get("all_passed") is False:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
