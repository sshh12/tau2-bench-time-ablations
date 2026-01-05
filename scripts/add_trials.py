#!/usr/bin/env python3
"""
Add trials 4 and 5 to existing 3-trial results.

This script runs only the NEW trials (3 and 4, 0-indexed) for each offset,
then merges them into the existing results files.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# All offsets to process
ALL_OFFSETS = [-36500, -3650, -1825, -1460, -1095, -730, -365, 0, 365, 730, 1095, 1460, 1825, 3650, 36500]

def find_results_file(offset: int) -> Path:
    """Find the results file for a given offset."""
    base_dir = Path("data/simulations/time_ablation")

    if offset == 0:
        subdir = base_dir / "offset_p0d"
        pattern = "*_airline_3trials.json"
    elif offset > 0:
        subdir = base_dir / f"offset_p{offset}d"
        pattern = f"*_airline_offset_p{offset}d_3trials.json"
    else:
        subdir = base_dir / f"offset_n{abs(offset)}d"
        pattern = f"*_airline_offset_n{abs(offset)}d_3trials.json"

    # Try subdirectory first
    if subdir.exists():
        files = list(subdir.glob(pattern))
        if files:
            return files[0]

    # Try root directory
    if offset == 0:
        files = list(base_dir.glob("*_airline_3trials.json"))
    elif offset > 0:
        files = list(base_dir.glob(f"offset_p{offset}d.json"))
    else:
        files = list(base_dir.glob(f"offset_n{abs(offset)}d.json"))

    if files:
        return files[0]

    raise FileNotFoundError(f"No results file found for offset {offset}")

def get_offset_status():
    """Get status of each offset's results."""
    print("Current status of results files:")
    print("-" * 60)

    for offset in ALL_OFFSETS:
        try:
            f = find_results_file(offset)
            with open(f) as fp:
                data = json.load(fp)
            n_sims = len(data["simulations"])
            n_trials = data["info"]["num_trials"]
            n_tasks = len(set(s["task_id"] for s in data["simulations"]))
            actual_trials = max(s["trial"] for s in data["simulations"]) + 1
            print(f"  Offset {offset:+6d}d: {n_sims} sims ({n_tasks} tasks × {actual_trials} trials) - {f.name}")
        except FileNotFoundError:
            print(f"  Offset {offset:+6d}d: NOT FOUND")
    print()

def main():
    parser = argparse.ArgumentParser(description="Add extra trials to existing results")
    parser.add_argument("--status", action="store_true", help="Just show status of existing results")
    parser.add_argument("--offsets", type=int, nargs="+", default=ALL_OFFSETS, help="Offsets to process")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without doing it")
    args = parser.parse_args()

    if args.status:
        get_offset_status()
        return

    print("To add trials 4 and 5 to existing results, run:")
    print()
    print("  # For each offset, this will resume with 5 trials (skipping existing 0-2)")
    print("  yes y | python -m experiments.time_ablation.cli run \\")
    print("      --offsets <offset> --num-trials 5 --agent-llm claude-sonnet-4-5-20250929")
    print()
    print("The framework automatically skips completed (trial, task_id, seed) combinations.")
    print()

    get_offset_status()

    if args.dry_run:
        print("Dry run - would process these offsets:", args.offsets)
        return

    print("Run the script in scripts/run_extra_trials.sh to execute.")

if __name__ == "__main__":
    main()
