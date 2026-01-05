"""
Domain loader for offset airline domains.

Dynamically registers offset domains in the tau2 registry.
"""

import importlib
from pathlib import Path
from typing import Optional

from loguru import logger

from experiments.time_ablation.config import (
    get_offset_data_dir,
    get_offset_domain_name,
    get_offset_src_dir,
)
from tau2.registry import registry


def is_offset_domain_generated(offset_days: int) -> bool:
    """Check if an offset domain has been generated."""
    if offset_days == 0:
        return True  # Original domain always exists

    data_dir = get_offset_data_dir(offset_days)
    src_dir = get_offset_src_dir(offset_days)

    # Check for required files
    required_data_files = ["db.json", "tasks.json", "policy.md"]
    required_src_files = ["__init__.py", "tools.py", "environment.py"]

    for f in required_data_files:
        if not (data_dir / f).exists():
            return False

    for f in required_src_files:
        if not (src_dir / f).exists():
            return False

    return True


def register_offset_domain(offset_days: int) -> str:
    """
    Register an offset domain in the tau2 registry.

    Args:
        offset_days: Number of days offset (0 for original)

    Returns:
        The domain name that was registered

    Raises:
        ValueError: If the domain has not been generated
    """
    domain_name = get_offset_domain_name(offset_days)

    # Check if already registered
    if domain_name in registry.get_domains():
        logger.debug(f"Domain {domain_name} already registered")
        return domain_name

    # Original domain is already registered
    if offset_days == 0:
        return "airline"

    # Check if domain is generated
    if not is_offset_domain_generated(offset_days):
        raise ValueError(
            f"Offset domain {domain_name} has not been generated. "
            f"Run: python -m experiments.time_ablation.cli generate --offset-days {offset_days}"
        )

    # Dynamically import the generated module
    try:
        module = importlib.import_module(f"tau2.domains.{domain_name}.environment")
        get_environment = module.get_environment
        get_tasks = module.get_tasks
        get_tasks_split = module.get_tasks_split
    except ImportError as e:
        raise ImportError(
            f"Failed to import offset domain module: {domain_name}. "
            f"Make sure the domain was generated correctly. Error: {e}"
        )

    # Register the domain
    logger.info(f"Registering offset domain: {domain_name}")
    registry.register_domain(get_environment, domain_name)
    registry.register_tasks(get_tasks, domain_name, get_task_splits=get_tasks_split)

    return domain_name


def register_all_offset_domains(offsets: list[int]) -> dict[int, str]:
    """
    Register multiple offset domains.

    Args:
        offsets: List of day offsets to register

    Returns:
        Dictionary mapping offset -> domain_name
    """
    result = {}
    for offset in offsets:
        try:
            domain_name = register_offset_domain(offset)
            result[offset] = domain_name
        except Exception as e:
            logger.error(f"Failed to register offset {offset}: {e}")
            raise
    return result


def get_domain_for_offset(offset_days: int) -> str:
    """
    Get the domain name for a given offset, registering it if needed.

    Args:
        offset_days: Number of days offset

    Returns:
        The domain name to use
    """
    return register_offset_domain(offset_days)


def list_generated_offset_domains() -> list[int]:
    """
    List all generated offset domains.

    Returns:
        List of offset values that have been generated
    """
    from experiments.time_ablation.config import OFFSET_DATA_DIR
    import re

    generated = []
    for path in OFFSET_DATA_DIR.iterdir():
        if path.is_dir() and path.name.startswith("airline_offset_"):
            # Parse offset from directory name
            # Format: airline_offset_p365d or airline_offset_n365d
            match = re.match(r"airline_offset_([pn])(\d+)d", path.name)
            if match:
                sign = 1 if match.group(1) == "p" else -1
                offset = sign * int(match.group(2))
                if is_offset_domain_generated(offset):
                    generated.append(offset)

    return sorted(generated)
