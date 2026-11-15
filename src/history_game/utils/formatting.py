"""Dependency-free formatting utilities for historical years and labels."""

from __future__ import annotations


def format_historical_year(year: int) -> str:
    """Format a signed non-zero integer year into BCE/CE notation."""
    if year < 0:
        return f"{abs(year)} BCE"
    return f"{year} CE"
