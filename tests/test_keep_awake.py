"""
Tests for utils.keep_awake: prevent_sleep / allow_sleep (Windows display wake lock).
"""
import pytest

from utils.keep_awake import prevent_sleep, allow_sleep


def test_prevent_sleep_no_raise():
    """prevent_sleep() does not raise (idempotent)."""
    prevent_sleep()
    prevent_sleep()


def test_allow_sleep_no_raise():
    """allow_sleep() does not raise (idempotent)."""
    allow_sleep()
    allow_sleep()


def test_prevent_then_allow_sleep():
    """prevent_sleep then allow_sleep runs without error (restore normal power behavior)."""
    prevent_sleep()
    allow_sleep()
