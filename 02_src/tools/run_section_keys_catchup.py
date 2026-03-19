#!/usr/bin/env python3
"""
Catch-up script for Task 011: L3 Parameters — section_keys[]

This script runs section_keys processing for specific jurisdictions or all jurisdictions.
It can be used to re-run the section_keys step if needed.

Usage:
    python -m tools.run_section_keys_catchup --all
    python -m tools.run_section_keys_catchup --jurisdictions "Великобритания" "Гонконг"
"""
import argparse
import sys
from pathlib import Path

# Ensure project src is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.section_keys import process_section_keys


def main():
    parser = argparse.ArgumentParser(
        description="Catch-up script for section_keys processing"
    )

    jgroup = parser.add_mutually_exclusive_group()
    jgroup.add_argument(
        "--all",
        action="store_true",
        default=False,
        help="Process all jurisdictions"
    )
    jgroup.add_argument(
        "--jurisdictions",
        nargs="+",
        metavar="NAME",
        help="Space-separated jurisdiction names to process"
    )

    args = parser.parse_args()

    if args.all:
        process_section_keys(jurisdictions=None)
    elif args.jurisdictions:
        process_section_keys(jurisdictions=args.jurisdictions)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
