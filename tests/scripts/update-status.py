#!/usr/bin/env python3
"""
Merges per-combination test result JSON files into tests/STATUS.json,
then regenerates the status table section in README.md between sentinel
comments <!-- STATUS:BEGIN --> and <!-- STATUS:END -->.

Usage:
    update-status.py --results-dir <dir> --status-file <path> --readme <path>
                     [--run-url-prefix <url>]
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import textwrap
from typing import cast, TypedDict

SENTINEL_BEGIN = "<!-- STATUS:BEGIN -->"
SENTINEL_END = "<!-- STATUS:END -->"
STATUS_ICONS = {
    "success": "✅",
    "failure": "❌",
}
STATUS_BLOCK_TEMPLATE = textwrap.dedent(f"""\
    {{sentinel_begin}}

    {{table}}

    > Last updated: {{last_updated}}
    >
    > Each cell links to the GitHub Actions run.
    > 
    > Legend: 
    > - {STATUS_ICONS["success"]} pass
    > - {STATUS_ICONS["failure"]} fail
    > - ⬜ not tested

    {{sentinel_end}}""")


class Result(TypedDict):
    provider: str
    os: str
    status: str
    run_id: str
    run_url: str
    timestamp: str


class Status(TypedDict):
    last_updated: str
    results: dict[str, Result]


def load_results_from_files(results_dir_path: "Path") -> "list[Result]":
    results: list[Result] = []

    if not results_dir_path.exists():
        print(f"Warning: results directory {results_dir_path!r} does not exist", file=sys.stderr)
        return results

    for path in results_dir_path.rglob("*.json"):
        try:
            with open(path) as f:
                result = cast("Result", json.load(f))
                results.append(result)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: could not read {path}: {e}", file=sys.stderr)

    return results


def load_status_from_file(status_file_path: "Path") -> "Status":
    try:
        with open(status_file_path) as f:
            return cast("Status", json.load(f))
    except FileNotFoundError:
        return {"last_updated": "", "results": {}}


def merge_results(
    status: "Status",
    new_results: "list[Result]",
    run_url_prefix: str,
) -> "Status":
    for result in new_results:
        provider = result.get("provider", "")
        os_name = result.get("os", "")

        # Skip malformed results
        if not provider or not os_name:
            print(
                f"Warning: skipping result with missing provider or OS name: {result}",
                file=sys.stderr,
            )
            continue

        key = f"{provider}/{os_name}"

        partial_result = {
            "status": result.get("status", "failure"),
            "run_id": result.get("run_id", ""),
            "timestamp": result.get("timestamp", ""),
        }

        run_id = result.get("run_id", "")

        if run_url_prefix and run_id:
            partial_result["run_url"] = f"{run_url_prefix}/{run_id}"
        elif "run_url" in result:
            partial_result["run_url"] = result["run_url"]

        result = Result(**partial_result)

        status["results"][key] = result

    status["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return status


def save_status(status_file_path: "Path", status: "Status") -> None:
    status_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(status_file_path, "w") as f:
        json.dump(status, f, indent=2)
        f.write("\n")


def build_table(status: "Status") -> str:
    all_providers: set[str] = set()
    all_oses: set[str] = set()

    for key in status["results"]:
        parts = key.split("/", 1)
        if len(parts) == 2:
            all_providers.add(parts[0])
            all_oses.add(parts[1])

    if not all_providers or not all_oses:
        return "*No test results yet.*\n"

    providers = sorted(all_providers)
    oses = sorted(all_oses)

    # Header row
    header = "| Provider | " + " | ".join(oses) + " |"
    separator = "|----------|" + "|".join([":---:"] * len(oses)) + "|"

    rows = [header, separator]

    for provider in providers:
        cells: list[str] = []
        for os_name in oses:
            key = f"{provider}/{os_name}"
            result = status["results"].get(key)
            if result is None:
                cells.append("⬜ n/a")
            else:
                icon = STATUS_ICONS.get(result["status"], "❓")
                run_url = result.get("run_url", "")
                if run_url:
                    cells.append(f"{icon} [run]({run_url})")
                else:
                    cells.append(icon)
        provider_label = provider.replace("-", " ").title()

        rows.append(f"| {provider_label} | " + " | ".join(cells) + " |")

    return "\n".join(rows) + "\n"


def build_status_block(status: "Status") -> str:
    try:
        dt = datetime.fromisoformat(status["last_updated"].replace("Z", "+00:00"))
        date_str = dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        date_str = "unknown"

    table = build_table(status)

    return STATUS_BLOCK_TEMPLATE.format(
        last_updated=date_str,
        table=table,
        sentinel_begin=SENTINEL_BEGIN,
        sentinel_end=SENTINEL_END,
    )


def update_readme(readme_path: "Path", status_block: str) -> None:
    content = readme_path.read_text()

    begin_idx = content.find(SENTINEL_BEGIN)
    end_idx = content.find(SENTINEL_END)

    if begin_idx != -1 and end_idx != -1:
        new_content = (
            content[:begin_idx] + status_block + content[end_idx + len(SENTINEL_END) :]
        )
    else:
        # Sentinels not found — append at end
        new_content = content.rstrip("\n") + "\n\n" + status_block + "\n"

    readme_path.write_text(new_content)


def setup_parser() -> "argparse.ArgumentParser":
    parser = argparse.ArgumentParser(description=__doc__)
    for path_arg in ["results-dir", "status-file", "readme"]:
        parser.add_argument(f"--{path_arg}", required=True, type=Path)
    parser.add_argument("--run-url-prefix", default="", type=str)
    return parser


def main() -> None:
    args = setup_parser().parse_args()
    status_file_path = cast("Path", args.status_file)
    results_dir = cast("Path", args.results_dir)
    readme_path = cast("Path", args.readme)
    run_url_prefix = cast("str", args.run_url_prefix)

    print(f"Loading new results from {results_dir}")
    new_results = load_results_from_files(results_dir)
    print(f"Found {len(new_results)} result file(s)")

    print(f"Loading existing status from {status_file_path}")
    status = load_status_from_file(status_file_path)
    status = merge_results(status, new_results, run_url_prefix)

    save_status(status_file_path, status)
    print(f"Saved updated status to {status_file_path}: {json.dumps(status, indent=2)}")

    status_block = build_status_block(status)
    update_readme(readme_path, status_block)
    print(f"Updated README at {readme_path}")


if __name__ == "__main__":
    main()
