"""
Generate plots for time ablation experiment results.
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Optional

import numpy as np
from loguru import logger


def generate_time_ablation_plot(
    results_dir: Path,
    output_file: Optional[Path] = None,
) -> Path:
    """
    Generate a plot showing Pass^3 and per-trial average scores by date offset.

    Args:
        results_dir: Directory containing offset subdirectories with results
        output_file: Output file path (default: time_ablation_plot.png in current dir)

    Returns:
        Path to the generated plot
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise ImportError("matplotlib is required for plotting. Install with: pip install matplotlib")

    if output_file is None:
        output_file = Path("time_ablation_plot.png")

    # Collect data from results
    results = []
    for offset_dir in results_dir.iterdir():
        if not offset_dir.is_dir():
            continue

        # Parse offset from dirname
        dirname = offset_dir.name
        if not dirname.startswith("offset_"):
            continue

        offset_str = dirname.replace("offset_", "")
        if offset_str.startswith("p"):
            offset = int(offset_str[1:-1])
        elif offset_str.startswith("n"):
            offset = -int(offset_str[1:-1])
        else:
            continue

        # Load results from JSON files
        for json_file in offset_dir.glob("*.json"):
            try:
                with open(json_file) as f:
                    data = json.load(f)

                # Group simulations by task and trial
                task_results = defaultdict(list)
                trial_rewards = defaultdict(list)

                for sim in data["simulations"]:
                    task_id = sim["task_id"]
                    trial = sim["trial"]
                    reward = sim["reward_info"]["reward"]
                    task_results[task_id].append(reward)
                    trial_rewards[trial].append(reward)

                num_tasks = len(task_results)
                if num_tasks == 0:
                    continue

                # Pass^3: all trials pass for a task
                pass_k = (
                    sum(
                        1
                        for rewards in task_results.values()
                        if all(r >= 1.0 for r in rewards)
                    )
                    / num_tasks
                    * 100
                )

                # Average reward per trial
                trial_avg_rewards = [
                    sum(trial_rewards[t]) / len(trial_rewards[t]) * 100
                    for t in sorted(trial_rewards.keys())
                ]

                results.append(
                    {
                        "offset": offset,
                        "pass_k": pass_k,
                        "trial_avg_rewards": trial_avg_rewards,
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to load {json_file}: {e}")

    if not results:
        raise ValueError(f"No results found in {results_dir}")

    # Sort by offset
    results.sort(key=lambda x: x["offset"])

    offsets = [r["offset"] for r in results]
    pass_k_values = [r["pass_k"] for r in results]

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))

    # Plot individual trial scores - small, subtle
    for r in results:
        offset = r["offset"]
        for trial_idx, avg in enumerate(r["trial_avg_rewards"]):
            jitter = (trial_idx - 1) * 30
            ax.scatter(
                offset + jitter, avg, alpha=0.5, s=40, c="steelblue", zorder=3
            )

    # Add one label for legend
    ax.scatter([], [], alpha=0.5, s=40, c="steelblue", label="Trial Avg")

    # Plot Pass^3 line
    ax.plot(
        offsets,
        pass_k_values,
        "o-",
        color="darkred",
        linewidth=2.5,
        markersize=10,
        label="Pass^3 (%)",
        zorder=5,
    )

    # Mark baseline if present
    if 0 in offsets:
        baseline_idx = offsets.index(0)
        ax.axvline(x=0, color="gray", linestyle="--", alpha=0.4)
        ax.scatter(
            [0],
            [pass_k_values[baseline_idx]],
            color="darkred",
            s=180,
            zorder=6,
            edgecolors="gold",
            linewidths=2,
        )

    # Labels
    ax.set_xlabel("Offset (days)", fontsize=11)
    ax.set_ylabel("Score (%)", fontsize=11)
    ax.set_title(
        "Time Ablation: Pass^3 and Per-Trial Average Scores\n"
        "(Claude Sonnet 4.5, 3 trials, 50 tasks, airline domain)",
        fontsize=13,
    )

    # X-axis labels with years
    year_labels = {
        -1825: "2019\n(-5y)",
        -730: "2022\n(-2y)",
        -365: "2023\n(-1y)",
        0: "2024\n(baseline)",
        365: "2025\n(+1y)",
        730: "2026\n(+2y)",
        1825: "2029\n(+5y)",
    }
    ax.set_xticks(offsets)
    ax.set_xticklabels([year_labels.get(o, str(o)) for o in offsets])

    # Set y-axis limits with some padding
    y_min = min(min(pass_k_values), min(min(r["trial_avg_rewards"]) for r in results))
    y_max = max(max(pass_k_values), max(max(r["trial_avg_rewards"]) for r in results))
    ax.set_ylim(y_min - 5, y_max + 5)

    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right")

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    plt.close()

    return output_file


def generate_task_heatmap(
    results_dir: Path,
    output_file: Optional[Path] = None,
) -> Path:
    """
    Generate a heatmap showing pass rate for each task across date offsets.

    Args:
        results_dir: Directory containing offset subdirectories with results
        output_file: Output file path (default: time_ablation_heatmap.png)

    Returns:
        Path to the generated plot
    """
    try:
        import matplotlib.pyplot as plt
        from matplotlib.colors import LinearSegmentedColormap
    except ImportError:
        raise ImportError(
            "matplotlib is required for plotting. Install with: pip install matplotlib"
        )

    if output_file is None:
        output_file = Path("time_ablation_heatmap.png")

    # Collect data: task_id -> offset -> pass_rate
    task_data = defaultdict(dict)
    offsets_found = set()

    for offset_dir in results_dir.iterdir():
        if not offset_dir.is_dir():
            continue

        dirname = offset_dir.name
        if not dirname.startswith("offset_"):
            continue

        offset_str = dirname.replace("offset_", "")
        if offset_str.startswith("p"):
            offset = int(offset_str[1:-1])
        elif offset_str.startswith("n"):
            offset = -int(offset_str[1:-1])
        else:
            continue

        offsets_found.add(offset)

        for json_file in offset_dir.glob("*.json"):
            try:
                with open(json_file) as f:
                    data = json.load(f)

                task_results = defaultdict(list)
                for sim in data["simulations"]:
                    task_id = sim["task_id"]
                    reward = sim["reward_info"]["reward"]
                    task_results[task_id].append(reward)

                for task_id, rewards in task_results.items():
                    pass_rate = sum(1 for r in rewards if r >= 1.0) / len(rewards)
                    task_data[task_id][offset] = pass_rate
            except Exception as e:
                logger.warning(f"Failed to load {json_file}: {e}")

    if not task_data:
        raise ValueError(f"No results found in {results_dir}")

    # Sort offsets and tasks
    offsets = sorted(offsets_found)
    task_ids = sorted(task_data.keys(), key=lambda x: int(x))

    # Create matrix
    matrix = np.zeros((len(task_ids), len(offsets)))
    for i, task_id in enumerate(task_ids):
        for j, offset in enumerate(offsets):
            matrix[i, j] = task_data[task_id].get(offset, 0)

    # Sort tasks by baseline performance, then by overall performance
    baseline_idx = offsets.index(0) if 0 in offsets else 0
    task_order = sorted(
        range(len(task_ids)),
        key=lambda i: (matrix[i, baseline_idx], matrix[i].mean()),
        reverse=True,
    )
    matrix_sorted = matrix[task_order]
    task_ids_sorted = [task_ids[i] for i in task_order]

    # Transpose for horizontal layout (offsets on y-axis, tasks on x-axis)
    matrix_transposed = matrix_sorted.T

    # Create figure (wide and short)
    fig, ax = plt.subplots(figsize=(16, 5))

    # Custom colormap: red (fail) -> yellow (partial) -> green (pass)
    colors = ["#d73027", "#fee08b", "#1a9850"]
    cmap = LinearSegmentedColormap.from_list("pass_fail", colors)

    im = ax.imshow(matrix_transposed, cmap=cmap, aspect="auto", vmin=0, vmax=1)

    # Labels
    year_labels = {
        -1825: "2019 (-5y)",
        -730: "2022 (-2y)",
        -365: "2023 (-1y)",
        0: "2024 (base)",
        365: "2025 (+1y)",
        730: "2026 (+2y)",
        1825: "2029 (+5y)",
    }
    ax.set_yticks(range(len(offsets)))
    ax.set_yticklabels([year_labels.get(o, str(o)) for o in offsets], fontsize=9)
    ax.set_xticks(range(len(task_ids_sorted)))
    ax.set_xticklabels([f"{tid}" for tid in task_ids_sorted], fontsize=7, rotation=90)

    ax.set_ylabel("Date Offset", fontsize=11)
    ax.set_xlabel("Task ID (sorted by baseline performance →)", fontsize=11)
    ax.set_title(
        "Task Pass Rate Heatmap by Date Offset  (Green=3/3 pass, Yellow=partial, Red=0/3 pass)",
        fontsize=12,
    )

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, shrink=0.8, orientation="vertical")
    cbar.set_label("Pass Rate", fontsize=10)
    cbar.set_ticks([0, 0.33, 0.67, 1.0])
    cbar.set_ticklabels(["0/3", "1/3", "2/3", "3/3"])

    # Highlight baseline row
    if 0 in offsets:
        baseline_y = offsets.index(0)
        ax.axhline(y=baseline_y - 0.5, color="black", linewidth=2, linestyle="-")
        ax.axhline(y=baseline_y + 0.5, color="black", linewidth=2, linestyle="-")

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    plt.close()

    return output_file
