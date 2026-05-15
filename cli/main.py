"""Minimal JSON command-line entry point for AutoLabeler."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from cli.inspect import (
    run_list_runs_command,
    run_product_labels_command,
    run_tree_command,
)
from cli.sample import run_sample_command
from cli.scan import run_scan_command


def run(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    parser = argparse.ArgumentParser(prog="auto-yolo-label")
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan_parser = subparsers.add_parser("scan")
    scan_parser.add_argument("request_json")
    sample_parser = subparsers.add_parser("sample")
    sample_parser.add_argument("request_json")
    inspect_parser = subparsers.add_parser("inspect")
    inspect_subparsers = inspect_parser.add_subparsers(
        dest="inspect_command", required=True
    )
    inspect_list_parser = inspect_subparsers.add_parser("list-runs")
    inspect_list_parser.add_argument("request_json")
    inspect_tree_parser = inspect_subparsers.add_parser("run-tree")
    inspect_tree_parser.add_argument("request_json")
    inspect_labels_parser = inspect_subparsers.add_parser("product-labels")
    inspect_labels_parser.add_argument("request_json")
    args = parser.parse_args(argv)

    if args.command == "scan":
        return run_scan_command(Path(args.request_json))
    if args.command == "sample":
        return run_sample_command(Path(args.request_json))
    if args.command == "inspect":
        if args.inspect_command == "list-runs":
            return run_list_runs_command(Path(args.request_json))
        if args.inspect_command == "run-tree":
            return run_tree_command(Path(args.request_json))
        if args.inspect_command == "product-labels":
            return run_product_labels_command(Path(args.request_json))
    raise AssertionError(f"Unhandled command: {args.command}")


def main() -> None:
    """Run the CLI as a Python module."""
    raise SystemExit(run())


if __name__ == "__main__":
    main()
