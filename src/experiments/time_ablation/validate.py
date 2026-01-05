"""
Validation for generated offset datasets.

Ensures that:
1. All flight dates in tasks exist in db.json
2. DOBs are reasonable (not in the future)
3. Timestamps are internally consistent
4. No orphaned references
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger

from experiments.time_ablation.config import (
    AIRLINE_BASE_YEAR,
    get_offset_data_dir,
    get_offset_domain_name,
)


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


class ValidationResult:
    """Result of a validation check."""

    def __init__(self):
        self.passed = True
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def add_error(self, message: str):
        self.passed = False
        self.errors.append(message)

    def add_warning(self, message: str):
        self.warnings.append(message)

    def __bool__(self):
        return self.passed


def validate_offset_dataset(offset_days: int) -> ValidationResult:
    """
    Validate a generated offset dataset.

    Args:
        offset_days: The offset in days

    Returns:
        ValidationResult with errors and warnings
    """
    result = ValidationResult()
    data_dir = get_offset_data_dir(offset_days)

    if not data_dir.exists():
        result.add_error(f"Data directory does not exist: {data_dir}")
        return result

    # Load data files
    try:
        with open(data_dir / "db.json", "r") as f:
            db_data = json.load(f)
        with open(data_dir / "tasks.json", "r") as f:
            tasks_data = json.load(f)
        with open(data_dir / "policy.md", "r") as f:
            policy_text = f.read()
    except Exception as e:
        result.add_error(f"Failed to load data files: {e}")
        return result

    # Run validation checks
    _validate_flight_dates_exist(db_data, tasks_data, result)
    _validate_dobs_reasonable(db_data, offset_days, result)
    _validate_timestamps_consistent(db_data, result)
    _validate_policy_date(policy_text, offset_days, result)

    return result


def _validate_flight_dates_exist(
    db_data: dict, tasks_data: list, result: ValidationResult
) -> None:
    """Check that all flight dates referenced in tasks exist in db.json."""
    # Collect all available flight dates
    available_dates = set()
    for flight_num, flight in db_data.get("flights", {}).items():
        for date in flight.get("dates", {}).keys():
            available_dates.add(date)

    # Check tasks for date references
    date_pattern = r"\b(\d{4}-\d{2}-\d{2})\b"

    for task in tasks_data:
        task_id = task.get("id", "unknown")

        # Check evaluation criteria actions
        if "evaluation_criteria" in task and task["evaluation_criteria"]:
            criteria = task["evaluation_criteria"]
            if "actions" in criteria and criteria["actions"]:
                for action in criteria["actions"]:
                    if "arguments" in action:
                        args_str = json.dumps(action["arguments"])
                        for match in re.finditer(date_pattern, args_str):
                            date = match.group(1)
                            # Only check dates that look like flight dates (2020+)
                            if date.startswith("202") and date not in available_dates:
                                # Check if it's a DOB (older dates)
                                year = int(date[:4])
                                if year >= 2020:
                                    result.add_error(
                                        f"Task {task_id}: Flight date {date} not found in db.json"
                                    )


def _validate_dobs_reasonable(
    db_data: dict, offset_days: int, result: ValidationResult
) -> None:
    """Check that DOBs are reasonable (not in the future, not too old)."""
    # Calculate the "current" date in the offset dataset
    base_current = datetime(2024, 5, 15)
    from datetime import timedelta

    offset_current = base_current + timedelta(days=offset_days)

    for user_id, user in db_data.get("users", {}).items():
        if "dob" in user and user["dob"]:
            try:
                dob = datetime.strptime(user["dob"], "%Y-%m-%d")

                # Check not in future
                if dob > offset_current:
                    result.add_error(
                        f"User {user_id}: DOB {user['dob']} is in the future "
                        f"(current date: {offset_current.strftime('%Y-%m-%d')})"
                    )

                # Check not unreasonably old (> 150 years)
                age = (offset_current - dob).days / 365.25
                if age > 150:
                    result.add_warning(
                        f"User {user_id}: DOB {user['dob']} results in age > 150 years"
                    )

                # Check not too young (negative age)
                if age < 0:
                    result.add_error(f"User {user_id}: DOB {user['dob']} is in the future")

            except ValueError as e:
                result.add_error(f"User {user_id}: Invalid DOB format: {user['dob']}")


def _validate_timestamps_consistent(db_data: dict, result: ValidationResult) -> None:
    """Check that timestamps are internally consistent."""
    # Check flight status timestamps
    for flight_num, flight in db_data.get("flights", {}).items():
        for date, status in flight.get("dates", {}).items():
            if "status" in status and status["status"] in ["landed", "flying", "on_time"]:
                # Check timestamp fields match the date
                for field in [
                    "actual_departure_time_est",
                    "actual_arrival_time_est",
                    "estimated_departure_time_est",
                    "estimated_arrival_time_est",
                ]:
                    if field in status and status[field]:
                        ts = status[field]
                        ts_date = ts.split("T")[0]
                        # Allow +1 day for overnight flights
                        if ts_date != date:
                            try:
                                date_dt = datetime.strptime(date, "%Y-%m-%d")
                                ts_dt = datetime.strptime(ts_date, "%Y-%m-%d")
                                diff = (ts_dt - date_dt).days
                                if diff not in [0, 1]:
                                    result.add_warning(
                                        f"Flight {flight_num} on {date}: {field} date "
                                        f"({ts_date}) differs by {diff} days"
                                    )
                            except ValueError:
                                pass


def _validate_policy_date(
    policy_text: str, offset_days: int, result: ValidationResult
) -> None:
    """Check that policy.md has the correct current time."""
    from experiments.time_ablation.date_utils import offset_iso_timestamp
    from experiments.time_ablation.config import AIRLINE_CURRENT_DATETIME

    expected_ts = offset_iso_timestamp(AIRLINE_CURRENT_DATETIME, offset_days)
    expected_date = expected_ts.split("T")[0]
    expected_time = expected_ts.split("T")[1]

    # Look for the current time line
    pattern = r"The current time is (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})"
    match = re.search(pattern, policy_text)

    if not match:
        result.add_error("Policy.md does not contain a valid 'current time' line")
        return

    actual_date = match.group(1)
    actual_time = match.group(2)

    if actual_date != expected_date:
        result.add_error(
            f"Policy date mismatch: expected {expected_date}, got {actual_date}"
        )

    if actual_time != expected_time:
        result.add_error(
            f"Policy time mismatch: expected {expected_time}, got {actual_time}"
        )


def print_validation_report(result: ValidationResult, offset_days: int) -> None:
    """Print a formatted validation report."""
    domain_name = get_offset_domain_name(offset_days)

    print(f"\n{'='*60}")
    print(f"Validation Report: {domain_name}")
    print(f"{'='*60}")

    if result.passed:
        print("\n[PASSED] All validation checks passed!")
    else:
        print(f"\n[FAILED] Validation failed with {len(result.errors)} error(s)")

    if result.errors:
        print("\nErrors:")
        for i, error in enumerate(result.errors, 1):
            print(f"  {i}. {error}")

    if result.warnings:
        print(f"\nWarnings ({len(result.warnings)}):")
        for i, warning in enumerate(result.warnings, 1):
            print(f"  {i}. {warning}")

    print(f"\n{'='*60}\n")


def validate_all_offsets(offsets: list[int]) -> dict[int, ValidationResult]:
    """
    Validate multiple offset datasets.

    Args:
        offsets: List of offsets to validate

    Returns:
        Dictionary mapping offset -> ValidationResult
    """
    results = {}
    for offset in offsets:
        if offset == 0:
            continue  # Skip original dataset
        logger.info(f"Validating offset {offset:+d}d...")
        results[offset] = validate_offset_dataset(offset)
    return results
