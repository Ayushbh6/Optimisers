"""Deterministic date and random helpers used by demonstration generation."""

from __future__ import annotations

from datetime import date, timedelta
import hashlib
import random


def stream(seed: int, name: str) -> random.Random:
    """Return an independent deterministic random stream."""
    digest = hashlib.sha256(f"{seed}:{name}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def add_workdays(value: date, workdays: int) -> date:
    """Move forward by a number of Monday-to-Friday working days."""
    result = value
    if workdays < 0:
        raise ValueError("workdays must be non-negative")
    remaining = workdays
    while remaining:
        result += timedelta(days=1)
        if result.weekday() < 5:
            remaining -= 1
    return result


def date_range(start: date, end: date):
    """Yield every calendar day in a closed interval."""
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def stable_fraction(seed: int, key: str) -> float:
    """Return a reproducible fraction independent of call ordering."""
    digest = hashlib.sha256(f"{seed}:{key}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64
