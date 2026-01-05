"""
CLI for time ablation experiments.

Commands:
- generate: Generate offset datasets
- validate: Validate generated datasets
- sanity-check: Run quick comparison on sampled tasks
- run: Run full ablation experiment
- analyze: Analyze results
"""

import argparse
import json
import sys
from pathlib import Path

from loguru import logger


def get_cli_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Time ablation experiments for tau2-bench airline domain"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Generate command
    gen_parser = subparsers.add_parser(
        "generate", help="Generate offset datasets"
    )
    gen_parser.add_argument(
        "--offset-days",
        type=int,
        required=True,
        help="Number of days to offset (e.g., 365 for +1 year, -365 for -1 year)",
    )
    gen_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing datasets",
    )
    gen_parser.add_argument(
        "--show-samples",
        action="store_true",
        help="Show sample transformations after generation",
    )

    # Generate-all command
    gen_all_parser = subparsers.add_parser(
        "generate-all", help="Generate all default offset datasets"
    )
    gen_all_parser.add_argument(
        "--offsets",
        type=int,
        nargs="+",
        default=None,
        help="Offsets to generate (default: from config)",
    )
    gen_all_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing datasets",
    )

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate", help="Validate generated datasets"
    )
    validate_parser.add_argument(
        "--offset-days",
        type=int,
        required=True,
        help="Offset to validate",
    )

    # Validate-all command
    validate_all_parser = subparsers.add_parser(
        "validate-all", help="Validate all generated datasets"
    )

    # Sanity-check command
    sanity_parser = subparsers.add_parser(
        "sanity-check", help="Run quick sanity check on sampled tasks"
    )
    sanity_parser.add_argument(
        "--offsets",
        type=int,
        nargs="+",
        default=[0, 365],
        help="Offsets to compare (default: 0 365)",
    )
    sanity_parser.add_argument(
        "--num-tasks",
        type=int,
        default=5,
        help="Number of tasks to sample (default: 5)",
    )
    sanity_parser.add_argument(
        "--num-trials",
        type=int,
        default=1,
        help="Number of trials per task (default: 1)",
    )
    sanity_parser.add_argument(
        "--agent-llm",
        type=str,
        default="gpt-4.1",
        help="Agent LLM to use (default: gpt-4.1 for fast/cheap sanity check)",
    )
    sanity_parser.add_argument(
        "--agent-llm-args",
        type=str,
        default='{"temperature": 0.0}',
        help="JSON args for agent LLM",
    )

    # Run command
    run_parser = subparsers.add_parser(
        "run", help="Run full ablation experiment"
    )
    run_parser.add_argument(
        "--offsets",
        type=int,
        nargs="+",
        default=None,
        help="Offsets to run (default: from config)",
    )
    run_parser.add_argument(
        "--num-trials",
        type=int,
        default=None,
        help="Number of trials per offset (default: from config)",
    )
    run_parser.add_argument(
        "--num-tasks",
        type=int,
        default=None,
        help="Number of tasks to run (default: all)",
    )
    run_parser.add_argument(
        "--agent-llm",
        type=str,
        default=None,
        help="Agent LLM to use (default: from config)",
    )
    run_parser.add_argument(
        "--agent-llm-args",
        type=str,
        default=None,
        help="JSON args for agent LLM (default: from config)",
    )
    run_parser.add_argument(
        "--user-llm",
        type=str,
        default=None,
        help="User LLM to use (default: from config)",
    )
    run_parser.add_argument(
        "--max-concurrency",
        type=int,
        default=None,
        help="Max concurrent simulations (default: from config)",
    )
    run_parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed (default: from config)",
    )

    # Analyze command
    analyze_parser = subparsers.add_parser(
        "analyze", help="Analyze experiment results"
    )
    analyze_parser.add_argument(
        "--results-dir",
        type=str,
        default=None,
        help="Results directory (default: from config)",
    )

    # Plot command
    plot_parser = subparsers.add_parser(
        "plot", help="Generate results plot"
    )
    plot_parser.add_argument(
        "--results-dir",
        type=str,
        default=None,
        help="Results directory (default: from config)",
    )
    plot_parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="time_ablation_plot.png",
        help="Output file path (default: time_ablation_plot.png)",
    )

    # Heatmap command
    heatmap_parser = subparsers.add_parser(
        "heatmap", help="Generate task heatmap"
    )
    heatmap_parser.add_argument(
        "--results-dir",
        type=str,
        default=None,
        help="Results directory (default: from config)",
    )
    heatmap_parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="time_ablation_heatmap.png",
        help="Output file path (default: time_ablation_heatmap.png)",
    )

    # List command
    list_parser = subparsers.add_parser(
        "list", help="List generated offset domains"
    )

    return parser


def cmd_generate(args):
    """Generate an offset dataset."""
    from experiments.time_ablation.generate_dataset import (
        generate_offset_dataset,
        print_sample_transformations,
    )

    if args.offset_days == 0:
        logger.error("Offset of 0 is the original dataset, no generation needed")
        return 1

    try:
        data_dir, src_dir = generate_offset_dataset(args.offset_days, force=args.force)
        logger.info(f"Generated dataset at:")
        logger.info(f"  Data: {data_dir}")
        logger.info(f"  Source: {src_dir}")

        if args.show_samples:
            print_sample_transformations(args.offset_days)

        return 0
    except FileExistsError as e:
        logger.error(str(e))
        return 1
    except Exception as e:
        logger.error(f"Failed to generate dataset: {e}")
        return 1


def cmd_generate_all(args):
    """Generate all default offset datasets."""
    from experiments.time_ablation.config import DEFAULT_OFFSETS
    from experiments.time_ablation.generate_dataset import generate_offset_dataset

    offsets = args.offsets or DEFAULT_OFFSETS
    offsets = [o for o in offsets if o != 0]  # Skip 0

    logger.info(f"Generating datasets for offsets: {offsets}")

    success = 0
    failed = 0
    for offset in offsets:
        try:
            generate_offset_dataset(offset, force=args.force)
            success += 1
        except FileExistsError:
            logger.warning(f"Offset {offset:+d}d already exists (use --force to overwrite)")
            failed += 1
        except Exception as e:
            logger.error(f"Failed to generate offset {offset:+d}d: {e}")
            failed += 1

    logger.info(f"Generation complete: {success} succeeded, {failed} failed")
    return 0 if failed == 0 else 1


def cmd_validate(args):
    """Validate a generated dataset."""
    from experiments.time_ablation.validate import (
        validate_offset_dataset,
        print_validation_report,
    )

    result = validate_offset_dataset(args.offset_days)
    print_validation_report(result, args.offset_days)

    return 0 if result.passed else 1


def cmd_validate_all(args):
    """Validate all generated datasets."""
    from experiments.time_ablation.domain_loader import list_generated_offset_domains
    from experiments.time_ablation.validate import (
        validate_offset_dataset,
        print_validation_report,
    )

    offsets = list_generated_offset_domains()

    if not offsets:
        logger.warning("No generated offset domains found")
        return 0

    logger.info(f"Validating {len(offsets)} offset domains: {offsets}")

    all_passed = True
    for offset in offsets:
        result = validate_offset_dataset(offset)
        print_validation_report(result, offset)
        if not result.passed:
            all_passed = False

    return 0 if all_passed else 1


def cmd_sanity_check(args):
    """Run a quick sanity check on sampled tasks."""
    from experiments.time_ablation.run_ablation import run_ablation_experiment

    logger.info(f"Running sanity check with offsets {args.offsets}")
    logger.info(f"  Tasks: {args.num_tasks}, Trials: {args.num_trials}")
    logger.info(f"  Agent LLM: {args.agent_llm}")

    agent_llm_args = json.loads(args.agent_llm_args)

    results = run_ablation_experiment(
        offsets=args.offsets,
        num_trials=args.num_trials,
        num_tasks=args.num_tasks,
        agent_llm=args.agent_llm,
        agent_llm_args=agent_llm_args,
    )

    # Print comparison
    print("\n" + "=" * 60)
    print("Sanity Check Results")
    print("=" * 60)

    for offset, result_file in results.items():
        from tau2.data_model.simulation import Results

        result = Results.load(result_file)
        avg_reward = sum(s.reward_info.reward for s in result.simulations) / len(
            result.simulations
        )
        print(f"\nOffset {offset:+d}d:")
        print(f"  Tasks: {len(result.tasks)}")
        print(f"  Simulations: {len(result.simulations)}")
        print(f"  Avg Reward: {avg_reward:.3f}")

    print("\n" + "=" * 60)
    return 0


def cmd_run(args):
    """Run full ablation experiment."""
    from experiments.time_ablation.config import (
        DEFAULT_OFFSETS,
        DEFAULT_NUM_TRIALS,
        DEFAULT_AGENT_LLM,
        DEFAULT_AGENT_LLM_ARGS,
        DEFAULT_USER_LLM,
        DEFAULT_MAX_CONCURRENCY,
        DEFAULT_SEED,
    )
    from experiments.time_ablation.run_ablation import run_ablation_experiment

    # Use defaults from config if not specified
    offsets = args.offsets or DEFAULT_OFFSETS
    num_trials = args.num_trials or DEFAULT_NUM_TRIALS
    agent_llm = args.agent_llm or DEFAULT_AGENT_LLM
    agent_llm_args = (
        json.loads(args.agent_llm_args) if args.agent_llm_args else DEFAULT_AGENT_LLM_ARGS
    )
    user_llm = args.user_llm or DEFAULT_USER_LLM
    max_concurrency = args.max_concurrency or DEFAULT_MAX_CONCURRENCY
    seed = args.seed or DEFAULT_SEED

    logger.info(f"Running ablation experiment")
    logger.info(f"  Offsets: {offsets}")
    logger.info(f"  Trials: {num_trials}")
    logger.info(f"  Agent LLM: {agent_llm}")
    logger.info(f"  Tasks: {args.num_tasks or 'all'}")

    results = run_ablation_experiment(
        offsets=offsets,
        num_trials=num_trials,
        num_tasks=args.num_tasks,
        agent_llm=agent_llm,
        agent_llm_args=agent_llm_args,
        user_llm=user_llm,
        max_concurrency=max_concurrency,
        seed=seed,
    )

    logger.info(f"Experiment complete. Results saved to:")
    for offset, result_file in results.items():
        logger.info(f"  Offset {offset:+d}d: {result_file}")

    return 0


def cmd_analyze(args):
    """Analyze experiment results."""
    from experiments.time_ablation.config import RESULTS_BASE_DIR
    from experiments.time_ablation.analyze import analyze_time_ablation_results

    results_dir = Path(args.results_dir) if args.results_dir else RESULTS_BASE_DIR

    if not results_dir.exists():
        logger.error(f"Results directory does not exist: {results_dir}")
        return 1

    analyze_time_ablation_results(results_dir)
    return 0


def cmd_plot(args):
    """Generate results plot."""
    from experiments.time_ablation.config import RESULTS_BASE_DIR
    from experiments.time_ablation.plot import generate_time_ablation_plot

    results_dir = Path(args.results_dir) if args.results_dir else RESULTS_BASE_DIR
    output_file = Path(args.output)

    if not results_dir.exists():
        logger.error(f"Results directory does not exist: {results_dir}")
        return 1

    try:
        output_path = generate_time_ablation_plot(results_dir, output_file)
        logger.info(f"Plot saved to {output_path}")
        return 0
    except ImportError as e:
        logger.error(str(e))
        return 1
    except ValueError as e:
        logger.error(str(e))
        return 1


def cmd_heatmap(args):
    """Generate task heatmap."""
    from experiments.time_ablation.config import RESULTS_BASE_DIR
    from experiments.time_ablation.plot import generate_task_heatmap

    results_dir = Path(args.results_dir) if args.results_dir else RESULTS_BASE_DIR
    output_file = Path(args.output)

    if not results_dir.exists():
        logger.error(f"Results directory does not exist: {results_dir}")
        return 1

    try:
        output_path = generate_task_heatmap(results_dir, output_file)
        logger.info(f"Heatmap saved to {output_path}")
        return 0
    except ImportError as e:
        logger.error(str(e))
        return 1
    except ValueError as e:
        logger.error(str(e))
        return 1


def cmd_list(args):
    """List generated offset domains."""
    from experiments.time_ablation.domain_loader import list_generated_offset_domains
    from experiments.time_ablation.config import get_offset_data_dir, get_offset_src_dir

    offsets = list_generated_offset_domains()

    print("\nGenerated Offset Domains:")
    print("=" * 60)

    if not offsets:
        print("  No offset domains generated yet.")
        print("  Run: python -m experiments.time_ablation.cli generate --offset-days 365")
    else:
        for offset in offsets:
            data_dir = get_offset_data_dir(offset)
            src_dir = get_offset_src_dir(offset)
            print(f"\n  Offset: {offset:+d}d")
            print(f"    Data: {data_dir}")
            print(f"    Source: {src_dir}")

    print("\n" + "=" * 60)
    return 0


def main():
    """Main entry point."""
    parser = get_cli_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    # Dispatch to command handler
    commands = {
        "generate": cmd_generate,
        "generate-all": cmd_generate_all,
        "validate": cmd_validate,
        "validate-all": cmd_validate_all,
        "sanity-check": cmd_sanity_check,
        "run": cmd_run,
        "analyze": cmd_analyze,
        "plot": cmd_plot,
        "heatmap": cmd_heatmap,
        "list": cmd_list,
    }

    handler = commands.get(args.command)
    if handler is None:
        logger.error(f"Unknown command: {args.command}")
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
