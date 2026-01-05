"""
Analyze time ablation experiment results.

Generates comparison reports and statistics across different date offsets.
"""

import re
from pathlib import Path
from typing import Optional

from loguru import logger

from tau2.data_model.simulation import Results
from tau2.metrics.agent_metrics import compute_metrics


def parse_offset_from_path(path: Path) -> Optional[int]:
    """
    Parse the offset value from a results directory path.

    Expected format: .../offset_p365d/ or .../offset_n365d/
    """
    match = re.search(r"offset_([pn])(\d+)d", str(path))
    if match:
        sign = 1 if match.group(1) == "p" else -1
        return sign * int(match.group(2))
    return None


def load_results_by_offset(results_dir: Path) -> dict[int, list[Results]]:
    """
    Load all results from a directory, organized by offset.

    Args:
        results_dir: Base results directory

    Returns:
        Dictionary mapping offset -> list of Results objects
    """
    results_by_offset = {}

    for offset_dir in results_dir.iterdir():
        if not offset_dir.is_dir():
            continue

        offset = parse_offset_from_path(offset_dir)
        if offset is None:
            continue

        results_by_offset[offset] = []

        for json_file in offset_dir.glob("*.json"):
            try:
                result = Results.load(json_file)
                results_by_offset[offset].append(result)
            except Exception as e:
                logger.warning(f"Failed to load {json_file}: {e}")

    return results_by_offset


def compute_metrics_for_results(results: Results) -> dict:
    """
    Compute metrics for a single Results object.

    Returns:
        Dictionary with metric values
    """
    if not results.simulations:
        return {"error": "No simulations"}

    num_trials = results.info.num_trials if results.info else 1
    metrics = compute_metrics(results)

    # Additional statistics
    rewards = [s.reward_info.reward for s in results.simulations]
    successful = sum(1 for r in rewards if r > 0.99)

    return {
        "num_tasks": len(results.tasks) if results.tasks else 0,
        "num_simulations": len(results.simulations),
        "num_trials": num_trials,
        "avg_reward": metrics.avg_reward,
        "pass_at_1": metrics.pass_hat_ks.get(1, 0.0),
        "success_rate": successful / len(rewards) if rewards else 0,
        "avg_agent_cost": metrics.avg_agent_cost,
        "rewards_min": min(rewards) if rewards else 0,
        "rewards_max": max(rewards) if rewards else 0,
        "agent_llm": results.info.agent_info.llm if results.info else "unknown",
    }


def analyze_time_ablation_results(results_dir: Path) -> None:
    """
    Analyze and print time ablation results.

    Args:
        results_dir: Directory containing offset subdirectories with results
    """
    results_by_offset = load_results_by_offset(results_dir)

    if not results_by_offset:
        logger.warning(f"No results found in {results_dir}")
        return

    print("\n" + "=" * 80)
    print("TIME ABLATION EXPERIMENT RESULTS")
    print("=" * 80)
    print(f"\nResults directory: {results_dir}")
    print(f"Offsets found: {sorted(results_by_offset.keys())}")

    # Compute and display metrics for each offset
    metrics_by_offset = {}
    for offset in sorted(results_by_offset.keys()):
        results_list = results_by_offset[offset]
        print(f"\n{'-'*40}")
        print(f"Offset: {offset:+d} days")
        print(f"{'-'*40}")

        if not results_list:
            print("  No results files found")
            continue

        # Aggregate metrics across all result files for this offset
        all_metrics = []
        for results in results_list:
            metrics = compute_metrics_for_results(results)
            all_metrics.append(metrics)
            print(f"\n  File: {results.info.agent_info.llm if results.info else 'unknown'}")
            print(f"    Tasks: {metrics['num_tasks']}")
            print(f"    Simulations: {metrics['num_simulations']}")
            print(f"    Trials: {metrics['num_trials']}")
            print(f"    Avg Reward: {metrics['avg_reward']:.4f}")
            print(f"    Pass@1: {metrics['pass_at_1']:.4f}")
            print(f"    Success Rate: {metrics['success_rate']:.2%}")
            print(f"    Avg Cost: ${metrics['avg_agent_cost']:.4f}")

        metrics_by_offset[offset] = all_metrics

    # Summary comparison
    print("\n" + "=" * 80)
    print("SUMMARY COMPARISON")
    print("=" * 80)

    # Create comparison table
    print(f"\n{'Offset':>12} {'Avg Reward':>12} {'Pass@1':>10} {'Success%':>10} {'Avg Cost':>10}")
    print("-" * 56)

    for offset in sorted(metrics_by_offset.keys()):
        metrics_list = metrics_by_offset[offset]
        if not metrics_list:
            continue

        # Average across all result files
        avg_reward = sum(m["avg_reward"] for m in metrics_list) / len(metrics_list)
        avg_pass1 = sum(m["pass_at_1"] for m in metrics_list) / len(metrics_list)
        avg_success = sum(m["success_rate"] for m in metrics_list) / len(metrics_list)
        avg_cost = sum(m["avg_agent_cost"] for m in metrics_list) / len(metrics_list)

        print(
            f"{offset:>+12}d {avg_reward:>12.4f} {avg_pass1:>10.4f} "
            f"{avg_success:>9.2%} ${avg_cost:>9.4f}"
        )

    print("\n" + "=" * 80)

    # Statistical comparison (baseline vs offsets)
    if 0 in metrics_by_offset and len(metrics_by_offset) > 1:
        baseline_metrics = metrics_by_offset[0]
        if baseline_metrics:
            baseline_avg = sum(m["avg_reward"] for m in baseline_metrics) / len(
                baseline_metrics
            )

            print("\nCOMPARISON TO BASELINE (offset=0)")
            print("-" * 40)

            for offset in sorted(metrics_by_offset.keys()):
                if offset == 0:
                    continue

                metrics_list = metrics_by_offset[offset]
                if not metrics_list:
                    continue

                offset_avg = sum(m["avg_reward"] for m in metrics_list) / len(
                    metrics_list
                )
                diff = offset_avg - baseline_avg
                pct_diff = (diff / baseline_avg * 100) if baseline_avg > 0 else 0

                direction = "+" if diff >= 0 else ""
                print(
                    f"  Offset {offset:+d}d: {direction}{diff:.4f} ({direction}{pct_diff:.1f}%)"
                )

    print("\n" + "=" * 80 + "\n")


def export_metrics_csv(results_dir: Path, output_file: Path) -> None:
    """
    Export metrics to a CSV file for further analysis.

    Args:
        results_dir: Directory containing results
        output_file: Output CSV file path
    """
    import csv

    results_by_offset = load_results_by_offset(results_dir)

    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "offset",
                "agent_llm",
                "num_tasks",
                "num_simulations",
                "num_trials",
                "avg_reward",
                "pass_at_1",
                "success_rate",
                "avg_agent_cost",
            ]
        )

        for offset in sorted(results_by_offset.keys()):
            for results in results_by_offset[offset]:
                metrics = compute_metrics_for_results(results)
                writer.writerow(
                    [
                        offset,
                        metrics.get("agent_llm", "unknown"),
                        metrics.get("num_tasks", 0),
                        metrics.get("num_simulations", 0),
                        metrics.get("num_trials", 0),
                        metrics.get("avg_reward", 0),
                        metrics.get("pass_at_1", 0),
                        metrics.get("success_rate", 0),
                        metrics.get("avg_agent_cost", 0),
                    ]
                )

    logger.info(f"Exported metrics to {output_file}")
