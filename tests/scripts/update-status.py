#!/usr/bin/env python3
from __future__ import annotations

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
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


SENTINEL_BEGIN = "<!-- STATUS:BEGIN -->"
SENTINEL_END = "<!-- STATUS:END -->"

# Canonical column order; unknown OSes are appended alphabetically
OS_ORDER = [
    "ubuntu-24.04",
    "ubuntu-22.04",
    "debian-12",
    "debian-11",
    "fedora-39",
]

# Canonical row order; unknown providers are appended alphabetically
PROVIDER_ORDER = [
    "hetzner",
    "digitalocean",
    "vultr",
    "linode",
    "aws-lightsail",
    "ovh",
]

STATUS_ICONS = {
    "success": "✅",
    "failure": "❌",
}


def load_status(status_file: Path) -> dict:
    if status_file.exists():
        with open(status_file) as f:
            return json.load(f)
    return {"last_updated": "", "results": {}}


def save_status(status_file: Path, data: dict) -> None:
    status_file.parent.mkdir(parents=True, exist_ok=True)
    with open(status_file, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def load_results(results_dir: Path) -> list[dict]:
    results = []
    for path in results_dir.rglob("*.json"):
        try:
            with open(path) as f:
                results.append(json.load(f))
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: could not read {path}: {e}", file=sys.stderr)
    return results


def merge_results(existing: dict, new_results: list[dict], run_url_prefix: str) -> dict:
    for result in new_results:
        provider = result.get("provider", "")
        os_name = result.get("os", "")
        if not provider or not os_name:
            continue
        key = f"{provider}/{os_name}"
        entry = {
            "status": result.get("status", "failure"),
            "run_id": result.get("run_id", ""),
            "timestamp": result.get("timestamp", ""),
        }
        run_id = result.get("run_id", "")
        if run_url_prefix and run_id:
            entry["run_url"] = f"{run_url_prefix}/{run_id}"
        elif "run_url" in result:
            entry["run_url"] = result["run_url"]
        existing["results"][key] = entry
    existing["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return existing


def build_table(results: dict) -> str:
    all_providers = set()
    all_oses = set()
    for key in results:
        parts = key.split("/", 1)
        if len(parts) == 2:
            all_providers.add(parts[0])
            all_oses.add(parts[1])

    def sort_key_provider(p):
        try:
            return (PROVIDER_ORDER.index(p), p)
        except ValueError:
            return (len(PROVIDER_ORDER), p)

    def sort_key_os(o):
        try:
            return (OS_ORDER.index(o), o)
        except ValueError:
            return (len(OS_ORDER), o)

    providers = sorted(all_providers, key=sort_key_provider)
    oses = sorted(all_oses, key=sort_key_os)

    if not providers or not oses:
        return "*No test results yet.*\n"

    # Header row
    header = "| Provider | " + " | ".join(oses) + " |"
    separator = "|----------|" + "|".join([":---:"] * len(oses)) + "|"

    rows = [header, separator]
    for provider in providers:
        cells = []
        for os_name in oses:
            key = f"{provider}/{os_name}"
            entry = results.get(key)
            if entry is None:
                cells.append("⬜ n/a")
            else:
                icon = STATUS_ICONS.get(entry["status"], "❓")
                run_url = entry.get("run_url", "")
                if run_url:
                    cells.append(f"{icon} [run]({run_url})")
                else:
                    cells.append(icon)
        provider_label = provider.replace("-", " ").title()
        rows.append(f"| {provider_label} | " + " | ".join(cells) + " |")

    return "\n".join(rows) + "\n"


def build_status_block(results: dict, last_updated: str) -> str:
    try:
        dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
        date_str = dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        date_str = "unknown"

    table = build_table(results)

    lines = [
        SENTINEL_BEGIN,
        "## Automated Test Matrix",
        "",
        f"> Last updated: {date_str} · Runs every Monday and Thursday via CI.",
        "> Each cell links to the GitHub Actions run. Legend: ✅ pass · ❌ fail · ⬜ not tested",
        "",
        table,
        SENTINEL_END,
    ]
    return "\n".join(lines)


def update_readme(readme_path: Path, status_block: str) -> None:
    content = readme_path.read_text()

    begin_idx = content.find(SENTINEL_BEGIN)
    end_idx = content.find(SENTINEL_END)

    if begin_idx != -1 and end_idx != -1:
        new_content = content[:begin_idx] + status_block + content[end_idx + len(SENTINEL_END):]
    else:
        # Sentinels not found — append at end
        new_content = content.rstrip("\n") + "\n\n" + status_block + "\n"

    readme_path.write_text(new_content)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", required=True, type=Path)
    parser.add_argument("--status-file", required=True, type=Path)
    parser.add_argument("--readme", required=True, type=Path)
    parser.add_argument("--run-url-prefix", default="", type=str)
    args = parser.parse_args()

    print(f"Loading existing status from {args.status_file}")
    status = load_status(args.status_file)

    print(f"Loading new results from {args.results_dir}")
    new_results = load_results(args.results_dir)
    print(f"Found {len(new_results)} result file(s)")

    status = merge_results(status, new_results, args.run_url_prefix)
    save_status(args.status_file, status)
    print(f"Saved updated status to {args.status_file}")

    status_block = build_status_block(status["results"], status["last_updated"])
    update_readme(args.readme, status_block)
    print(f"Updated README at {args.readme}")


if __name__ == "__main__":
    main()
