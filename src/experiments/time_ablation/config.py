"""
Configuration for time ablation experiments.

All defaults can be overridden via CLI arguments.
Edit this file to change default experiment parameters.
"""

from pathlib import Path

from tau2.utils.utils import DATA_DIR

# =============================================================================
# Experiment Parameters - Modify these for different runs
# =============================================================================

# Day offsets to test (in days)
# -365 = 1 year in the past
# +365 = 1 year in the future
# +1825 = 5 years in the future (365 * 5)
DEFAULT_OFFSETS = [-365, 0, 365, 1825]

# Number of trials per offset
DEFAULT_NUM_TRIALS = 3

# Agent LLM configuration
DEFAULT_AGENT_LLM = "claude-sonnet-4-20250514"
DEFAULT_AGENT_LLM_ARGS = {}

# User simulator LLM
DEFAULT_USER_LLM = "gpt-4.1"
DEFAULT_USER_LLM_ARGS = {"temperature": 0.0}

# =============================================================================
# Run Parameters
# =============================================================================

DEFAULT_MAX_STEPS = 200
DEFAULT_MAX_ERRORS = 10
DEFAULT_MAX_CONCURRENCY = 5
DEFAULT_SEED = 42

# =============================================================================
# Directory Paths
# =============================================================================

# Base directory for results
RESULTS_BASE_DIR = DATA_DIR / "simulations" / "time_ablation"

# Base directory for generated offset datasets
OFFSET_DATA_DIR = DATA_DIR / "tau2" / "domains"

# Source domain directory
AIRLINE_DATA_DIR = DATA_DIR / "tau2" / "domains" / "airline"

# Source code directory for airline domain
SRC_DIR = Path(__file__).parents[2]  # src/
AIRLINE_SRC_DIR = SRC_DIR / "tau2" / "domains" / "airline"

# =============================================================================
# Domain Configuration
# =============================================================================

# The base year for the airline domain (dates are relative to this)
AIRLINE_BASE_YEAR = 2024

# The "current" datetime in the airline domain
AIRLINE_CURRENT_DATETIME = "2024-05-15T15:00:00"

# Files to transform in the data directory
DATA_FILES_TO_TRANSFORM = [
    "db.json",
    "tasks.json",
    "policy.md",
    "split_tasks.json",
]

# Files to copy/generate in the source directory
SRC_FILES_TO_GENERATE = [
    "tools.py",
    "environment.py",
    "data_model.py",
    "user_tools.py",
    "__init__.py",
]


def get_offset_domain_name(offset_days: int) -> str:
    """Get the domain name for a given offset.

    Uses 'p' for positive and 'n' for negative to avoid invalid Python identifiers.
    Examples: airline_offset_p365d, airline_offset_n365d
    """
    if offset_days == 0:
        return "airline"
    sign = "p" if offset_days > 0 else "n"
    return f"airline_offset_{sign}{abs(offset_days)}d"


def get_offset_data_dir(offset_days: int) -> Path:
    """Get the data directory for a given offset."""
    return OFFSET_DATA_DIR / get_offset_domain_name(offset_days)


def get_offset_src_dir(offset_days: int) -> Path:
    """Get the source directory for a given offset."""
    return SRC_DIR / "tau2" / "domains" / get_offset_domain_name(offset_days)


def get_results_dir(offset_days: int) -> Path:
    """Get the results directory for a given offset."""
    sign = "p" if offset_days >= 0 else "n"
    suffix = f"offset_{sign}{abs(offset_days)}d"
    return RESULTS_BASE_DIR / suffix
