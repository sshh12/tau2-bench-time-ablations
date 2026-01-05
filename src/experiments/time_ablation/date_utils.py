"""
Date transformation utilities for time ablation experiments.

Handles offsetting dates in various formats:
- YYYY-MM-DD (ISO date)
- YYYY-MM-DDTHH:MM:SS (ISO timestamp)
- Month DD (text date, e.g., "May 26")
- Month DD YYYY (text date with year, e.g., "May 12 2024")
"""

import re
from datetime import datetime, timedelta
from typing import Optional

# All month names for regex pattern matching
MONTH_NAMES = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

# Short month names
MONTH_NAMES_SHORT = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]

# Month name to number mapping
MONTH_TO_NUM = {name: i + 1 for i, name in enumerate(MONTH_NAMES)}
MONTH_TO_NUM.update({name: i + 1 for i, name in enumerate(MONTH_NAMES_SHORT)})

# Number to month name mapping
NUM_TO_MONTH = {i + 1: name for i, name in enumerate(MONTH_NAMES)}


def offset_iso_date(date_str: str, days: int) -> str:
    """
    Transform an ISO date string (YYYY-MM-DD) by the given offset in days.

    Args:
        date_str: Date string in YYYY-MM-DD format
        days: Number of days to offset (positive for future, negative for past)

    Returns:
        Transformed date string in YYYY-MM-DD format

    Examples:
        >>> offset_iso_date("2024-05-15", 365)
        '2025-05-15'
        >>> offset_iso_date("2024-05-15", -365)
        '2023-05-15'
        >>> offset_iso_date("2024-05-31", 1)
        '2024-06-01'
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    new_dt = dt + timedelta(days=days)
    return new_dt.strftime("%Y-%m-%d")


def offset_iso_timestamp(ts_str: str, days: int) -> str:
    """
    Transform an ISO timestamp string (YYYY-MM-DDTHH:MM:SS) by the given offset in days.

    Args:
        ts_str: Timestamp string in YYYY-MM-DDTHH:MM:SS format
        days: Number of days to offset (positive for future, negative for past)

    Returns:
        Transformed timestamp string in YYYY-MM-DDTHH:MM:SS format

    Examples:
        >>> offset_iso_timestamp("2024-05-15T15:00:00", 365)
        '2025-05-15T15:00:00'
        >>> offset_iso_timestamp("2024-05-31T23:59:59", 1)
        '2024-06-01T23:59:59'
    """
    dt = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S")
    new_dt = dt + timedelta(days=days)
    return new_dt.strftime("%Y-%m-%dT%H:%M:%S")


def _offset_text_date_match(match: re.Match, days: int, base_year: int) -> str:
    """
    Helper to transform a matched text date.

    Args:
        match: Regex match object with groups (month_name, day, optional_year)
        days: Number of days to offset
        base_year: Default year to use if not specified in the match

    Returns:
        Transformed text date string
    """
    month_name = match.group(1)
    day = int(match.group(2))
    year_str = match.group(3)

    # Determine if we have a year in the original
    has_year = year_str is not None and year_str.strip()
    year = int(year_str.strip()) if has_year else base_year

    # Get month number
    month_num = MONTH_TO_NUM.get(month_name)
    if month_num is None:
        # Return original if month not recognized
        return match.group(0)

    # Create datetime and offset
    try:
        dt = datetime(year, month_num, day)
        new_dt = dt + timedelta(days=days)

        # Reconstruct the text date
        new_month_name = NUM_TO_MONTH[new_dt.month]
        if has_year:
            return f"{new_month_name} {new_dt.day} {new_dt.year}"
        else:
            return f"{new_month_name} {new_dt.day}"
    except ValueError:
        # Invalid date (e.g., Feb 30), return original
        return match.group(0)


def offset_text_dates(text: str, days: int, base_year: int = 2024) -> str:
    """
    Find and replace text dates in the format "Month DD" or "Month DD YYYY".

    Args:
        text: Text containing dates to transform
        days: Number of days to offset (positive for future, negative for past)
        base_year: Default year to use for dates without year specified

    Returns:
        Text with all dates transformed

    Examples:
        >>> offset_text_dates("Flight on May 26", 365, base_year=2024)
        'Flight on May 26'  # Year not shown, month/day unchanged for +365
        >>> offset_text_dates("May 12 2024", 365, base_year=2024)
        'May 12 2025'
        >>> offset_text_dates("Book for May 31", 1, base_year=2024)
        'Book for June 1'
    """
    # Build regex pattern for all month names (full and short)
    all_months = "|".join(MONTH_NAMES + MONTH_NAMES_SHORT)
    # Pattern: Month name, space(s), day number, optional (space(s) + year)
    pattern = rf"\b({all_months})\s+(\d{{1,2}})(?:\s+(\d{{4}}))?\b"

    def replace_match(match: re.Match) -> str:
        return _offset_text_date_match(match, days, base_year)

    return re.sub(pattern, replace_match, text)


def offset_all_dates_in_text(text: str, days: int, base_year: int = 2024) -> str:
    """
    Find and replace ALL date formats in text:
    - YYYY-MM-DD
    - YYYY-MM-DDTHH:MM:SS
    - Month DD
    - Month DD YYYY

    Args:
        text: Text containing dates to transform
        days: Number of days to offset
        base_year: Default year for text dates without year

    Returns:
        Text with all dates transformed
    """
    # First handle ISO timestamps (must come before ISO dates to avoid partial matches)
    iso_ts_pattern = r"\b(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})\b"

    def replace_iso_ts(match: re.Match) -> str:
        ts_str = f"{match.group(1)}T{match.group(2)}"
        return offset_iso_timestamp(ts_str, days)

    text = re.sub(iso_ts_pattern, replace_iso_ts, text)

    # Then handle ISO dates
    iso_date_pattern = r"\b(\d{4}-\d{2}-\d{2})\b"

    def replace_iso_date(match: re.Match) -> str:
        return offset_iso_date(match.group(1), days)

    text = re.sub(iso_date_pattern, replace_iso_date, text)

    # Finally handle text dates
    text = offset_text_dates(text, days, base_year)

    return text


def validate_date_offset(original: str, transformed: str, days: int) -> bool:
    """
    Validate that a date was correctly offset.

    Args:
        original: Original date string
        transformed: Transformed date string
        days: Expected offset in days

    Returns:
        True if transformation is correct, False otherwise
    """
    try:
        # Try ISO date
        orig_dt = datetime.strptime(original, "%Y-%m-%d")
        trans_dt = datetime.strptime(transformed, "%Y-%m-%d")
        return (trans_dt - orig_dt).days == days
    except ValueError:
        pass

    try:
        # Try ISO timestamp
        orig_dt = datetime.strptime(original, "%Y-%m-%dT%H:%M:%S")
        trans_dt = datetime.strptime(transformed, "%Y-%m-%dT%H:%M:%S")
        return (trans_dt - orig_dt).days == days
    except ValueError:
        pass

    return False


def get_offset_suffix(days: int) -> str:
    """
    Get a human-readable suffix for the offset.

    Args:
        days: Number of days offset

    Returns:
        Suffix string like '+365d' or '-365d'

    Examples:
        >>> get_offset_suffix(365)
        '+365d'
        >>> get_offset_suffix(-365)
        '-365d'
        >>> get_offset_suffix(0)
        '+0d'
    """
    return f"{days:+d}d"
