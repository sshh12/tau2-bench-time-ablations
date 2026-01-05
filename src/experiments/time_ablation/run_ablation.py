"""
Run ablation experiments with different date offsets.
"""

from pathlib import Path
from typing import Optional

from loguru import logger

from experiments.time_ablation.config import (
    DEFAULT_AGENT_LLM,
    DEFAULT_AGENT_LLM_ARGS,
    DEFAULT_MAX_CONCURRENCY,
    DEFAULT_MAX_ERRORS,
    DEFAULT_MAX_STEPS,
    DEFAULT_NUM_TRIALS,
    DEFAULT_OFFSETS,
    DEFAULT_SEED,
    DEFAULT_USER_LLM,
    DEFAULT_USER_LLM_ARGS,
    get_offset_domain_name,
    get_results_dir,
)
from experiments.time_ablation.domain_loader import (
    get_domain_for_offset,
    is_offset_domain_generated,
)
from tau2.run import RunConfig, run_domain


def make_run_config(
    offset_days: int,
    num_trials: int,
    num_tasks: Optional[int],
    agent_llm: str,
    agent_llm_args: dict,
    user_llm: str,
    user_llm_args: dict,
    max_steps: int,
    max_errors: int,
    max_concurrency: int,
    seed: int,
) -> RunConfig:
    """
    Create a RunConfig for an offset ablation experiment.

    Args:
        offset_days: Day offset (0 for baseline)
        num_trials: Number of trials per task
        num_tasks: Number of tasks (None for all)
        agent_llm: Agent LLM model string
        agent_llm_args: Agent LLM arguments
        user_llm: User simulator LLM
        user_llm_args: User simulator LLM arguments
        max_steps: Max steps per simulation
        max_errors: Max errors before termination
        max_concurrency: Max concurrent simulations
        seed: Random seed

    Returns:
        RunConfig for the experiment
    """
    domain = get_domain_for_offset(offset_days)
    results_dir = get_results_dir(offset_days)
    results_dir.mkdir(parents=True, exist_ok=True)

    # Build save path
    save_to = str(
        results_dir / f"{agent_llm}_{domain}_{num_trials}trials"
    )
    if num_tasks is not None:
        save_to += f"_{num_tasks}tasks"

    return RunConfig(
        domain=domain,
        agent="llm_agent",
        llm_agent=agent_llm,
        llm_args_agent=agent_llm_args,
        user="user_simulator",
        llm_user=user_llm,
        llm_args_user=user_llm_args,
        num_trials=num_trials,
        num_tasks=num_tasks,
        seed=seed,
        max_steps=max_steps,
        max_errors=max_errors,
        max_concurrency=max_concurrency,
        save_to=save_to,
    )


def run_ablation_experiment(
    offsets: Optional[list[int]] = None,
    num_trials: Optional[int] = None,
    num_tasks: Optional[int] = None,
    agent_llm: Optional[str] = None,
    agent_llm_args: Optional[dict] = None,
    user_llm: Optional[str] = None,
    user_llm_args: Optional[dict] = None,
    max_steps: Optional[int] = None,
    max_errors: Optional[int] = None,
    max_concurrency: Optional[int] = None,
    seed: Optional[int] = None,
) -> dict[int, Path]:
    """
    Run ablation experiments across multiple offsets.

    Args:
        offsets: List of day offsets to test
        num_trials: Number of trials per task
        num_tasks: Number of tasks (None for all)
        agent_llm: Agent LLM model string
        agent_llm_args: Agent LLM arguments
        user_llm: User simulator LLM
        user_llm_args: User LLM arguments
        max_steps: Max steps per simulation
        max_errors: Max errors before termination
        max_concurrency: Max concurrent simulations
        seed: Random seed

    Returns:
        Dictionary mapping offset -> result file path
    """
    # Use defaults from config if not specified
    offsets = offsets if offsets is not None else DEFAULT_OFFSETS
    num_trials = num_trials if num_trials is not None else DEFAULT_NUM_TRIALS
    agent_llm = agent_llm if agent_llm is not None else DEFAULT_AGENT_LLM
    agent_llm_args = agent_llm_args if agent_llm_args is not None else DEFAULT_AGENT_LLM_ARGS
    user_llm = user_llm if user_llm is not None else DEFAULT_USER_LLM
    user_llm_args = user_llm_args if user_llm_args is not None else DEFAULT_USER_LLM_ARGS
    max_steps = max_steps if max_steps is not None else DEFAULT_MAX_STEPS
    max_errors = max_errors if max_errors is not None else DEFAULT_MAX_ERRORS
    max_concurrency = max_concurrency if max_concurrency is not None else DEFAULT_MAX_CONCURRENCY
    seed = seed if seed is not None else DEFAULT_SEED

    # Validate that all offset domains exist
    for offset in offsets:
        if offset != 0 and not is_offset_domain_generated(offset):
            raise ValueError(
                f"Offset domain {offset:+d}d has not been generated. "
                f"Run: python -m experiments.time_ablation.cli generate --offset-days {offset}"
            )

    results = {}
    total = len(offsets)

    for i, offset in enumerate(offsets, 1):
        domain_name = get_offset_domain_name(offset)
        logger.info(f"[{i}/{total}] Running experiment for offset {offset:+d}d ({domain_name})")

        config = make_run_config(
            offset_days=offset,
            num_trials=num_trials,
            num_tasks=num_tasks,
            agent_llm=agent_llm,
            agent_llm_args=agent_llm_args,
            user_llm=user_llm,
            user_llm_args=user_llm_args,
            max_steps=max_steps,
            max_errors=max_errors,
            max_concurrency=max_concurrency,
            seed=seed,
        )

        logger.info(f"  Config: {config.save_to}")
        run_domain(config)

        result_file = Path(f"{config.save_to}.json")
        results[offset] = result_file
        logger.info(f"  Completed: {result_file}")

    return results


def run_single_offset(
    offset_days: int,
    num_trials: Optional[int] = None,
    num_tasks: Optional[int] = None,
    agent_llm: Optional[str] = None,
    agent_llm_args: Optional[dict] = None,
    **kwargs,
) -> Path:
    """
    Run experiment for a single offset.

    Convenience function for running just one offset.
    """
    results = run_ablation_experiment(
        offsets=[offset_days],
        num_trials=num_trials,
        num_tasks=num_tasks,
        agent_llm=agent_llm,
        agent_llm_args=agent_llm_args,
        **kwargs,
    )
    return results[offset_days]
