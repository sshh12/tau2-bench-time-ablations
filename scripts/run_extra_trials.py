#!/usr/bin/env python3
"""
Run 2 additional trials (4 and 5) for all offsets.

Strategy:
1. Rename existing *_3trials.json → *_5trials.json
2. Run with --num-trials 5 (framework will skip existing trials 0-2)
3. Result: same file now has 5 trials
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ALL_OFFSETS = [-36500, -3650, -1825, -1460, -1095, -730, -365, 0, 365, 730, 1095, 1460, 1825, 3650, 36500]

def find_results_file(offset: int) -> Path:
    """Find the 3trials results file for a given offset."""
    base_dir = Path("data/simulations/time_ablation")

    # Check subdirectories
    if offset == 0:
        patterns = [
            base_dir / "offset_p0d" / "*_airline_3trials.json",
            base_dir / "*_airline_3trials.json",
        ]
    elif offset > 0:
        patterns = [
            base_dir / f"offset_p{offset}d" / f"*_airline_offset_p{offset}d_3trials.json",
            base_dir / f"offset_p{offset}d.json",
        ]
    else:
        patterns = [
            base_dir / f"offset_n{abs(offset)}d" / f"*_airline_offset_n{abs(offset)}d_3trials.json",
            base_dir / f"offset_n{abs(offset)}d.json",
        ]

    for pattern in patterns:
        if "*" in str(pattern):
            matches = list(pattern.parent.glob(pattern.name))
            if matches:
                return matches[0]
        elif pattern.exists():
            return pattern

    raise FileNotFoundError(f"No results file found for offset {offset}")

def rename_to_5trials(src: Path) -> Path:
    """Rename 3trials file to 5trials."""
    if "3trials" in src.name:
        dst = src.parent / src.name.replace("3trials", "5trials")
    else:
        # Files like offset_n36500d.json - need to move to subdir with proper name
        if src.name.startswith("offset_n"):
            offset_str = src.stem  # e.g., "offset_n36500d"
            dst = src.parent / offset_str / f"claude-sonnet-4-5-20250929_airline_{offset_str}_5trials.json"
        elif src.name.startswith("offset_p"):
            offset_str = src.stem
            dst = src.parent / offset_str / f"claude-sonnet-4-5-20250929_airline_{offset_str}_5trials.json"
        else:
            raise ValueError(f"Unexpected filename: {src}")

    return dst

def main():
    parser = argparse.ArgumentParser(description="Run 2 extra trials for all offsets")
    parser.add_argument("--offsets", type=int, nargs="+", default=ALL_OFFSETS,
                        help="Specific offsets to process (default: all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without doing it")
    parser.add_argument("--rename-only", action="store_true",
                        help="Only rename files, don't run experiments")
    args = parser.parse_args()

    print("=" * 70)
    print("ADD TRIALS 4 AND 5 TO EXISTING RESULTS")
    print("=" * 70)
    print()

    # Step 1: Find and rename files
    print("Step 1: Renaming files from 3trials → 5trials")
    print("-" * 50)

    renames = []
    for offset in args.offsets:
        try:
            src = find_results_file(offset)
            dst = rename_to_5trials(src)

            # Update num_trials in the info
            with open(src) as f:
                data = json.load(f)
            current_trials = data["info"]["num_trials"]

            if current_trials >= 5:
                print(f"  Offset {offset:+6d}d: Already has {current_trials} trials, skipping")
                continue

            renames.append((offset, src, dst, data))
            print(f"  Offset {offset:+6d}d: {src.name} → {dst.name}")

        except FileNotFoundError as e:
            print(f"  Offset {offset:+6d}d: NOT FOUND - {e}")

    if not renames:
        print("\nNo files to process!")
        return

    if args.dry_run:
        print("\n[DRY RUN] Would rename and run experiments for above files")
        return

    print()
    response = input("Proceed with rename? (y/n) ").strip().lower()
    if response != "y":
        print("Aborted")
        return

    # Do the renames
    for offset, src, dst, data in renames:
        # Update num_trials
        data["info"]["num_trials"] = 5

        # Create destination directory if needed
        dst.parent.mkdir(parents=True, exist_ok=True)

        # Write to new location
        with open(dst, "w") as f:
            json.dump(data, f, indent=2)

        # Remove old file if different location
        if src != dst:
            src.unlink()

        print(f"  Renamed: {src} → {dst}")

    if args.rename_only:
        print("\nFiles renamed. Run experiments manually with:")
        print("  python -m experiments.time_ablation.cli run --num-trials 5 ...")
        return

    # Step 2: Run experiments
    print()
    print("Step 2: Running experiments (trials 4 and 5)")
    print("-" * 50)

    for offset in args.offsets:
        print(f"\n>>> Offset {offset:+d}d")
        cmd = [
            "python", "-m", "experiments.time_ablation.cli", "run",
            "--offsets", str(offset),
            "--num-trials", "5",
            "--agent-llm", "claude-sonnet-4-5-20250929",
        ]
        print(f"    Running: {' '.join(cmd)}")

        # Run with auto-confirmation
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        # Send 'y' for any prompts
        stdout, _ = proc.communicate(input="y\ny\ny\n", timeout=7200)  # 2hr timeout

        # Show relevant output
        for line in stdout.split("\n"):
            if any(x in line for x in ["Running", "Skipping", "Completed", "Error", "trial"]):
                print(f"    {line}")

        if proc.returncode != 0:
            print(f"    WARNING: Process exited with code {proc.returncode}")

    print()
    print("Done! Run analysis with:")
    print("  python -m experiments.time_ablation.cli analyze")

if __name__ == "__main__":
    main()
