#!/usr/bin/env python3
"""Shared primitives for CUMCM mechanical gates."""

from __future__ import annotations

import re
from datetime import datetime, timezone


INSTANT_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


def parse_instant(value: object) -> datetime | None:
    """Return one UTC instant; reject dates, naive times, and invalid offsets."""
    if not isinstance(value, str) or INSTANT_PATTERN.fullmatch(value) is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def strictly_increasing(values: object) -> bool:
    """Require a non-empty sequence of distinct, chronologically increasing instants."""
    if not isinstance(values, list) or not values:
        return False
    parsed = [parse_instant(value) for value in values]
    return (
        all(value is not None for value in parsed)
        and all(left < right for left, right in zip(parsed, parsed[1:]))
    )


def instant_equal(left: object, right: object) -> bool:
    left_value = parse_instant(left)
    right_value = parse_instant(right)
    return (
        left_value is not None
        and right_value is not None
        and left_value == right_value
    )


def instant_after(left: object, right: object) -> bool:
    left_value = parse_instant(left)
    right_value = parse_instant(right)
    return (
        left_value is not None
        and right_value is not None
        and left_value > right_value
    )


def instant_not_before(left: object, right: object) -> bool:
    left_value = parse_instant(left)
    right_value = parse_instant(right)
    return (
        left_value is not None
        and right_value is not None
        and left_value >= right_value
    )
