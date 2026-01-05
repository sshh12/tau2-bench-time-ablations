"""
Dataset generator for time ablation experiments.

Generates offset datasets by transforming dates in:
- db.json (flight dates, timestamps, DOBs)
- tasks.json (instructions, evaluation criteria)
- policy.md (current time)
- tools.py (hardcoded datetime, fixed one-stop bug)
- environment.py (data paths)
"""

import json
import re
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

from loguru import logger

from experiments.time_ablation.config import (
    AIRLINE_BASE_YEAR,
    AIRLINE_CURRENT_DATETIME,
    AIRLINE_DATA_DIR,
    AIRLINE_SRC_DIR,
    get_offset_data_dir,
    get_offset_domain_name,
    get_offset_src_dir,
)
from experiments.time_ablation.date_utils import (
    offset_all_dates_in_text,
    offset_iso_date,
    offset_iso_timestamp,
)


def transform_db(db_data: dict, days: int) -> dict:
    """
    Transform all dates in db.json.

    Transforms:
    - User DOBs
    - Passenger DOBs
    - Flight date keys
    - Timestamps in flight status objects
    - Reservation created_at timestamps
    """
    result = deepcopy(db_data)

    # Transform users
    if "users" in result:
        for user_id, user in result["users"].items():
            if "dob" in user and user["dob"]:
                user["dob"] = offset_iso_date(user["dob"], days)
            # Transform passengers in user
            if "passengers" in user:
                for passenger in user["passengers"]:
                    if "dob" in passenger and passenger["dob"]:
                        passenger["dob"] = offset_iso_date(passenger["dob"], days)

    # Transform flights - need to rebuild date keys
    if "flights" in result:
        for flight_number, flight in result["flights"].items():
            if "dates" in flight:
                new_dates = {}
                for date_key, status in flight["dates"].items():
                    # Transform the date key
                    new_date_key = offset_iso_date(date_key, days)
                    # Transform timestamps within the status
                    new_status = _transform_flight_status(status, days)
                    new_dates[new_date_key] = new_status
                flight["dates"] = new_dates

    # Transform reservations
    if "reservations" in result:
        for res_id, reservation in result["reservations"].items():
            if "created_at" in reservation and reservation["created_at"]:
                reservation["created_at"] = offset_iso_timestamp(
                    reservation["created_at"], days
                )
            # Transform flights in reservation
            if "flights" in reservation:
                for flight in reservation["flights"]:
                    if "date" in flight and flight["date"]:
                        flight["date"] = offset_iso_date(flight["date"], days)
            # Transform passengers in reservation
            if "passengers" in reservation:
                for passenger in reservation["passengers"]:
                    if "dob" in passenger and passenger["dob"]:
                        passenger["dob"] = offset_iso_date(passenger["dob"], days)

    return result


def _transform_flight_status(status: dict, days: int) -> dict:
    """Transform timestamps within a flight status object."""
    result = deepcopy(status)

    # List of timestamp fields to transform
    timestamp_fields = [
        "actual_departure_time_est",
        "actual_arrival_time_est",
        "estimated_departure_time_est",
        "estimated_arrival_time_est",
    ]

    for field in timestamp_fields:
        if field in result and result[field]:
            result[field] = offset_iso_timestamp(result[field], days)

    return result


def transform_tasks(tasks_data: list, days: int) -> list:
    """
    Transform all dates in tasks.json.

    Transforms:
    - Text dates in instructions (user_scenario.instructions.*)
    - ISO dates in evaluation criteria (actions, nl_assertions)
    """
    result = deepcopy(tasks_data)

    for task in result:
        # Transform user_scenario instructions (text dates)
        if "user_scenario" in task and task["user_scenario"]:
            scenario = task["user_scenario"]
            if "instructions" in scenario and scenario["instructions"]:
                instructions = scenario["instructions"]
                for key in [
                    "task_instructions",
                    "reason_for_call",
                    "known_info",
                    "unknown_info",
                ]:
                    if key in instructions and instructions[key]:
                        instructions[key] = offset_all_dates_in_text(
                            instructions[key], days, AIRLINE_BASE_YEAR
                        )

        # Transform evaluation_criteria
        if "evaluation_criteria" in task and task["evaluation_criteria"]:
            criteria = task["evaluation_criteria"]

            # Transform actions
            if "actions" in criteria and criteria["actions"]:
                for action in criteria["actions"]:
                    if "arguments" in action and action["arguments"]:
                        _transform_action_arguments(action["arguments"], days)

            # Transform nl_assertions (text)
            if "nl_assertions" in criteria and criteria["nl_assertions"]:
                criteria["nl_assertions"] = [
                    offset_all_dates_in_text(assertion, days, AIRLINE_BASE_YEAR)
                    for assertion in criteria["nl_assertions"]
                ]

            # Transform communicate_info
            if "communicate_info" in criteria and criteria["communicate_info"]:
                for comm in criteria["communicate_info"]:
                    if "value" in comm and isinstance(comm["value"], str):
                        comm["value"] = offset_all_dates_in_text(
                            comm["value"], days, AIRLINE_BASE_YEAR
                        )

        # Transform description if present
        if "description" in task and task["description"]:
            desc = task["description"]
            if "purpose" in desc and desc["purpose"]:
                desc["purpose"] = offset_all_dates_in_text(
                    desc["purpose"], days, AIRLINE_BASE_YEAR
                )
            if "notes" in desc and desc["notes"]:
                desc["notes"] = offset_all_dates_in_text(
                    desc["notes"], days, AIRLINE_BASE_YEAR
                )

    return result


def _transform_action_arguments(arguments: dict, days: int) -> None:
    """Transform dates in action arguments (in place)."""
    for key, value in arguments.items():
        if isinstance(value, str):
            # Check if it looks like an ISO date
            if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
                arguments[key] = offset_iso_date(value, days)
            elif re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$", value):
                arguments[key] = offset_iso_timestamp(value, days)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    _transform_action_arguments(item, days)
                elif isinstance(item, str):
                    if re.match(r"^\d{4}-\d{2}-\d{2}$", item):
                        value[i] = offset_iso_date(item, days)
        elif isinstance(value, dict):
            _transform_action_arguments(value, days)


def transform_policy(policy_text: str, days: int) -> str:
    """
    Transform the current time in policy.md.

    The policy contains a line like:
    "The current time is 2024-05-15 15:00:00 EST."
    """
    # Transform the specific datetime format in the policy
    # Pattern: "The current time is YYYY-MM-DD HH:MM:SS EST."
    pattern = r"(The current time is )(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})( EST\.)"

    def replace_datetime(match: re.Match) -> str:
        date_str = match.group(2)
        time_str = match.group(3)
        ts_str = f"{date_str}T{time_str}"
        new_ts = offset_iso_timestamp(ts_str, days)
        new_date, new_time = new_ts.split("T")
        return f"{match.group(1)}{new_date} {new_time}{match.group(4)}"

    return re.sub(pattern, replace_datetime, policy_text)


def generate_tools_py(days: int) -> str:
    """
    Generate tools.py with:
    1. Updated _get_datetime() returning the offset datetime
    2. Fixed one-stop flight date logic (no hardcoded "2024-05-")
    """
    # Read the original tools.py
    tools_path = AIRLINE_SRC_DIR / "tools.py"
    with open(tools_path, "r") as f:
        content = f.read()

    # Calculate the new datetime
    new_datetime = offset_iso_timestamp(AIRLINE_CURRENT_DATETIME, days)

    # Replace _get_datetime return value
    # Original: return "2024-05-15T15:00:00"
    pattern_datetime = r'(def _get_datetime\(self\) -> str:.*?return ")[^"]+(")'
    content = re.sub(
        pattern_datetime,
        rf"\g<1>{new_datetime}\2",
        content,
        flags=re.DOTALL,
    )

    # The one-stop flight bug has already been fixed in the original tools.py
    # No replacement needed - the code now uses proper date arithmetic

    return content


def generate_environment_py(offset_days: int) -> str:
    """Generate environment.py for the offset domain."""
    domain_name = get_offset_domain_name(offset_days)

    return f'''# Generated offset domain: {domain_name}
# Offset: {offset_days:+d} days from original airline domain

from pathlib import Path
from typing import Optional

from tau2.data_model.tasks import Task
from tau2.domains.{domain_name}.data_model import FlightDB
from tau2.domains.{domain_name}.tools import AirlineTools
from tau2.domains.{domain_name}.utils import (
    AIRLINE_DB_PATH,
    AIRLINE_POLICY_PATH,
    AIRLINE_TASK_SET_PATH,
)
from tau2.environment.environment import Environment
from tau2.utils import load_file


def get_environment(
    db: Optional[FlightDB] = None,
    solo_mode: bool = False,
) -> Environment:
    if solo_mode:
        raise ValueError("Airline domain does not support solo mode")
    if db is None:
        db = FlightDB.load(AIRLINE_DB_PATH)
    tools = AirlineTools(db)
    with open(AIRLINE_POLICY_PATH, "r") as fp:
        policy = fp.read()
    return Environment(
        domain_name="{domain_name}",
        policy=policy,
        tools=tools,
    )


def get_tasks(task_split_name: Optional[str] = "base") -> list[Task]:
    tasks = load_file(AIRLINE_TASK_SET_PATH)
    tasks = [Task.model_validate(task) for task in tasks]
    if task_split_name is None:
        return tasks
    task_splits = get_tasks_split()
    if task_split_name not in task_splits:
        raise ValueError(
            f"Invalid task split name: {{task_split_name}}. Valid splits are: {{task_splits.keys()}}"
        )
    return [task for task in tasks if task.id in task_splits[task_split_name]]


def get_tasks_split() -> dict[str, list[str]]:
    split_file = (
        Path(AIRLINE_TASK_SET_PATH).parent
        / f"split_{{Path(AIRLINE_TASK_SET_PATH).stem}}.json"
    )
    return load_file(split_file)
'''


def generate_utils_py(offset_days: int) -> str:
    """Generate utils.py for the offset domain."""
    domain_name = get_offset_domain_name(offset_days)

    return f'''# Generated offset domain: {domain_name}
from tau2.utils.utils import DATA_DIR

AIRLINE_DATA_DIR = DATA_DIR / "tau2" / "domains" / "{domain_name}"
AIRLINE_DB_PATH = AIRLINE_DATA_DIR / "db.json"
AIRLINE_POLICY_PATH = AIRLINE_DATA_DIR / "policy.md"
AIRLINE_TASK_SET_PATH = AIRLINE_DATA_DIR / "tasks.json"
'''


def generate_init_py(offset_days: int) -> str:
    """Generate __init__.py for the offset domain."""
    domain_name = get_offset_domain_name(offset_days)
    return f'''# Generated offset domain: {domain_name}
# Offset: {offset_days:+d} days from original airline domain
'''


def generate_offset_dataset(offset_days: int, force: bool = False) -> tuple[Path, Path]:
    """
    Generate a complete offset dataset.

    Args:
        offset_days: Number of days to offset
        force: If True, overwrite existing directories

    Returns:
        Tuple of (data_dir, src_dir) paths
    """
    if offset_days == 0:
        raise ValueError("Offset of 0 is the original dataset, no generation needed")

    data_dir = get_offset_data_dir(offset_days)
    src_dir = get_offset_src_dir(offset_days)

    # Check if directories exist
    if data_dir.exists() and not force:
        raise FileExistsError(
            f"Data directory already exists: {data_dir}. Use force=True to overwrite."
        )
    if src_dir.exists() and not force:
        raise FileExistsError(
            f"Source directory already exists: {src_dir}. Use force=True to overwrite."
        )

    logger.info(f"Generating offset dataset for {offset_days:+d} days")
    logger.info(f"  Data directory: {data_dir}")
    logger.info(f"  Source directory: {src_dir}")

    # Create directories
    data_dir.mkdir(parents=True, exist_ok=True)
    src_dir.mkdir(parents=True, exist_ok=True)

    # Transform and write data files
    _generate_data_files(offset_days, data_dir)

    # Generate source files
    _generate_src_files(offset_days, src_dir)

    logger.info(f"Successfully generated offset dataset for {offset_days:+d} days")
    return data_dir, src_dir


def _generate_data_files(offset_days: int, data_dir: Path) -> None:
    """Generate transformed data files."""
    # Transform db.json
    logger.info("  Transforming db.json...")
    with open(AIRLINE_DATA_DIR / "db.json", "r") as f:
        db_data = json.load(f)
    transformed_db = transform_db(db_data, offset_days)
    with open(data_dir / "db.json", "w") as f:
        json.dump(transformed_db, f, indent=4)

    # Transform tasks.json
    logger.info("  Transforming tasks.json...")
    with open(AIRLINE_DATA_DIR / "tasks.json", "r") as f:
        tasks_data = json.load(f)
    transformed_tasks = transform_tasks(tasks_data, offset_days)
    with open(data_dir / "tasks.json", "w") as f:
        json.dump(transformed_tasks, f, indent=4)

    # Transform policy.md
    logger.info("  Transforming policy.md...")
    with open(AIRLINE_DATA_DIR / "policy.md", "r") as f:
        policy_text = f.read()
    transformed_policy = transform_policy(policy_text, offset_days)
    with open(data_dir / "policy.md", "w") as f:
        f.write(transformed_policy)

    # Copy split_tasks.json (no transformation needed, just task IDs)
    logger.info("  Copying split_tasks.json...")
    shutil.copy(AIRLINE_DATA_DIR / "split_tasks.json", data_dir / "split_tasks.json")


def _generate_src_files(offset_days: int, src_dir: Path) -> None:
    """Generate source files for the offset domain."""
    # Generate __init__.py
    logger.info("  Generating __init__.py...")
    with open(src_dir / "__init__.py", "w") as f:
        f.write(generate_init_py(offset_days))

    # Generate tools.py with fixed bugs and updated datetime
    logger.info("  Generating tools.py...")
    with open(src_dir / "tools.py", "w") as f:
        f.write(generate_tools_py(offset_days))

    # Generate environment.py
    logger.info("  Generating environment.py...")
    with open(src_dir / "environment.py", "w") as f:
        f.write(generate_environment_py(offset_days))

    # Generate utils.py
    logger.info("  Generating utils.py...")
    with open(src_dir / "utils.py", "w") as f:
        f.write(generate_utils_py(offset_days))

    # Copy data_model.py (no changes needed)
    logger.info("  Copying data_model.py...")
    shutil.copy(AIRLINE_SRC_DIR / "data_model.py", src_dir / "data_model.py")

    # Copy user_tools.py if it exists
    user_tools_path = AIRLINE_SRC_DIR / "user_tools.py"
    if user_tools_path.exists():
        logger.info("  Copying user_tools.py...")
        shutil.copy(user_tools_path, src_dir / "user_tools.py")


def print_sample_transformations(offset_days: int, num_samples: int = 3) -> None:
    """Print sample transformations for verification."""
    logger.info(f"\nSample transformations for offset {offset_days:+d} days:")

    # Sample db transformation
    with open(AIRLINE_DATA_DIR / "db.json", "r") as f:
        db_data = json.load(f)

    # Show a few flight date transformations
    logger.info("\nFlight date keys (first 3 flights, first 3 dates each):")
    for i, (flight_num, flight) in enumerate(db_data.get("flights", {}).items()):
        if i >= num_samples:
            break
        dates = list(flight.get("dates", {}).keys())[:num_samples]
        transformed_dates = [offset_iso_date(d, offset_days) for d in dates]
        logger.info(f"  {flight_num}: {dates} -> {transformed_dates}")

    # Sample policy transformation
    with open(AIRLINE_DATA_DIR / "policy.md", "r") as f:
        policy_text = f.read()
    original_time = "2024-05-15 15:00:00"
    transformed_time = offset_iso_timestamp("2024-05-15T15:00:00", offset_days).replace(
        "T", " "
    )
    logger.info(f"\nPolicy current time: {original_time} -> {transformed_time}")
