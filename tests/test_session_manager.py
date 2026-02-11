"""
Tests for session management: course config, run building, navigation.
"""
import json
from pathlib import Path

import pytest

from core.session_manager import (
    SessionManager,
    load_course_config,
    build_course_run,
)


def test_load_course_config_missing_file(tmp_path):
    """Missing config file returns empty presets."""
    path = tmp_path / "nonexistent.json"
    assert not path.exists()
    config = load_course_config(path)
    assert config == {"course_presets": []}


def test_load_course_config_valid(tmp_path):
    """Valid JSON with course_presets loads correctly."""
    path = tmp_path / "session_configs.json"
    path.write_text(
        json.dumps({
            "course_presets": [
                {"duration_minutes": 10, "phases": [{"name": "WarmUp", "duration_seconds_per_image": 30, "count": 2}]},
            ]
        }),
        encoding="utf-8",
    )
    config = load_course_config(path)
    assert len(config["course_presets"]) == 1
    assert config["course_presets"][0]["duration_minutes"] == 10
    assert config["course_presets"][0]["phases"][0]["count"] == 2


def test_build_course_run_matching_preset():
    """Run is built with correct counts and durations per phase."""
    presets = [
        {
            "duration_minutes": 10,
            "phases": [
                {"name": "WarmUp", "duration_seconds_per_image": 30, "count": 2},
                {"name": "Gesture", "duration_seconds_per_image": 60, "count": 1},
            ],
        },
    ]
    image_ids = ["a", "b", "c"]
    run = build_course_run(image_ids, presets, 10)
    assert len(run) == 3
    assert run[0][1] == 30
    assert run[1][1] == 30
    assert run[2][1] == 60
    assert {r[0] for r in run} <= {"a", "b", "c"}


def test_build_course_run_no_preset():
    """Unknown duration returns empty run."""
    presets = [{"duration_minutes": 10, "phases": []}]
    run = build_course_run(["a", "b"], presets, 25)
    assert run == []


def test_build_course_run_empty_images():
    """Empty image list returns empty run."""
    presets = [{"duration_minutes": 10, "phases": [{"name": "W", "duration_seconds_per_image": 30, "count": 1}]}]
    run = build_course_run([], presets, 10)
    assert run == []


def test_session_manager_start_course():
    """SessionManager starts course and reports progress."""
    config_path = Path(__file__).resolve().parent.parent / "gui" / "ressources" / "session_configs.json"
    course_config = load_course_config(config_path) if config_path.exists() else {"course_presets": []}
    if not course_config.get("course_presets"):
        pytest.skip("session_configs.json not found")

    mgr = SessionManager()
    image_ids = [f"img_{i}" for i in range(20)]
    ok = mgr.start_session(
        image_ids=image_ids,
        session_type="Course",
        course_duration_minutes=10,
        window_mode="FullScreen",
        course_config=course_config,
    )
    assert ok is True
    assert mgr.get_current_image_id() is not None
    assert mgr.get_current_duration() in (30, 60, 150, 300, 600)
    cur, total, dur = mgr.get_session_progress()
    assert cur == 1
    assert total == 5 + 2 + 1 + 1  # 10 min preset: Warm-up, Gesture, Short pose, Anatomy
    assert dur == mgr.get_current_duration()

    # Advance to end
    while mgr.advance_image():
        pass
    assert mgr.get_current_image_id() is None
    mgr.end_session()
    assert mgr.get_current_image_id() is None


def test_session_manager_constant_interval():
    """SessionManager starts constant-interval run."""
    mgr = SessionManager()
    image_ids = ["a", "b", "c"]
    ok = mgr.start_session(
        image_ids=image_ids,
        session_type="Constant interval",
        interval_seconds=60,
        window_mode="FullScreen",
    )
    assert ok is True
    assert mgr.get_current_duration() == 60
    cur, total, _ = mgr.get_session_progress()
    assert cur == 1
    assert total == 3
    assert mgr.advance_image() is True
    assert mgr.previous_image() is True
    mgr.previous_image()  # at first
    assert mgr.previous_image() is False
