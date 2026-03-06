"""Unit tests for lane registry and configuration (Story 1.1)."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from openeinstein.campaigns.lanes import (
    LaneConfig,
    LaneRegistry,
    QueueMode,
    load_lane_config,
)


# ── LaneConfig model tests ──


def test_lane_config_defaults() -> None:
    cfg = LaneConfig(name="main")
    assert cfg.name == "main"
    assert cfg.max_concurrent == 4
    assert cfg.queue_mode == QueueMode.COLLECT


def test_lane_config_custom_values() -> None:
    cfg = LaneConfig(name="literature", max_concurrent=2, queue_mode=QueueMode.STEER)
    assert cfg.max_concurrent == 2
    assert cfg.queue_mode == QueueMode.STEER


def test_queue_mode_enum_values() -> None:
    assert QueueMode.COLLECT.value == "collect"
    assert QueueMode.FOLLOWUP.value == "followup"
    assert QueueMode.STEER.value == "steer"


# ── LaneRegistry basic tests ──


def test_lane_registry_from_configs() -> None:
    configs = {
        "main": LaneConfig(name="main", max_concurrent=2),
        "literature": LaneConfig(name="literature", max_concurrent=1),
    }
    registry = LaneRegistry(configs)
    assert set(registry.lane_names) == {"main", "literature"}


def test_acquire_and_release() -> None:
    configs = {"main": LaneConfig(name="main", max_concurrent=2)}
    registry = LaneRegistry(configs)

    registry.acquire("main")
    status = registry.lane_status()
    assert status["main"]["active"] == 1

    registry.release("main")
    status = registry.lane_status()
    assert status["main"]["active"] == 0


def test_acquire_unknown_lane_raises() -> None:
    registry = LaneRegistry({})
    with pytest.raises(KeyError, match="Unknown lane"):
        registry.acquire("nonexistent")


def test_release_unknown_lane_raises() -> None:
    registry = LaneRegistry({})
    with pytest.raises(KeyError, match="Unknown lane"):
        registry.release("nonexistent")


def test_release_without_acquire_raises() -> None:
    configs = {"main": LaneConfig(name="main", max_concurrent=2)}
    registry = LaneRegistry(configs)
    with pytest.raises(RuntimeError, match="release.*not acquired"):
        registry.release("main")


# ── Concurrency cap enforcement ──


def test_acquire_blocks_at_capacity() -> None:
    """Acquiring more than max_concurrent blocks the caller."""
    configs = {"main": LaneConfig(name="main", max_concurrent=1)}
    registry = LaneRegistry(configs)

    registry.acquire("main")

    blocked = threading.Event()
    acquired = threading.Event()

    def try_acquire() -> None:
        blocked.set()
        registry.acquire("main")
        acquired.set()

    t = threading.Thread(target=try_acquire, daemon=True)
    t.start()

    blocked.wait(timeout=1.0)
    time.sleep(0.05)
    assert not acquired.is_set(), "Second acquire should block"

    registry.release("main")
    acquired.wait(timeout=1.0)
    assert acquired.is_set(), "Second acquire should proceed after release"

    registry.release("main")
    t.join(timeout=1.0)


def test_concurrent_threads_respect_cap() -> None:
    """Thread count inside a lane never exceeds max_concurrent."""
    cap = 2
    configs = {"main": LaneConfig(name="main", max_concurrent=cap)}
    registry = LaneRegistry(configs)

    max_concurrent_observed = 0
    lock = threading.Lock()
    active = 0

    def worker() -> None:
        nonlocal active, max_concurrent_observed
        registry.acquire("main")
        with lock:
            active += 1
            if active > max_concurrent_observed:
                max_concurrent_observed = active
        time.sleep(0.02)
        with lock:
            active -= 1
        registry.release("main")

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    assert max_concurrent_observed <= cap


# ── Lane status ──


def test_lane_status_empty() -> None:
    configs = {"main": LaneConfig(name="main", max_concurrent=4)}
    registry = LaneRegistry(configs)
    status = registry.lane_status()
    assert status["main"]["active"] == 0
    assert status["main"]["max_concurrent"] == 4


def test_lane_status_with_active_steps() -> None:
    configs = {"main": LaneConfig(name="main", max_concurrent=4)}
    registry = LaneRegistry(configs)
    registry.acquire("main")
    registry.acquire("main")
    status = registry.lane_status()
    assert status["main"]["active"] == 2
    registry.release("main")
    registry.release("main")


# ── YAML config loading ──


def test_load_lane_config_valid(tmp_path: Path) -> None:
    config_file = tmp_path / "lanes.yaml"
    config_file.write_text(
        """\
lanes:
  main:
    max_concurrent: 4
    queue_mode: collect
  literature:
    max_concurrent: 2
    queue_mode: followup
  gating:
    max_concurrent: 2
    queue_mode: collect
""",
        encoding="utf-8",
    )
    configs = load_lane_config(config_file)
    assert "main" in configs
    assert configs["main"].max_concurrent == 4
    assert configs["literature"].queue_mode == QueueMode.FOLLOWUP
    assert configs["gating"].max_concurrent == 2


def test_load_lane_config_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_lane_config(tmp_path / "nonexistent.yaml")


def test_load_lane_config_malformed(tmp_path: Path) -> None:
    config_file = tmp_path / "lanes.yaml"
    config_file.write_text("not: valid: yaml: [", encoding="utf-8")
    with pytest.raises(Exception):
        load_lane_config(config_file)


def test_load_lane_config_missing_lanes_key(tmp_path: Path) -> None:
    config_file = tmp_path / "lanes.yaml"
    config_file.write_text("other_key: value\n", encoding="utf-8")
    with pytest.raises(ValueError, match="lanes"):
        load_lane_config(config_file)


# ── Import smoke test ──


def test_lane_registry_importable() -> None:
    from openeinstein.campaigns import LaneConfig, LaneRegistry

    assert LaneRegistry is not None
    assert LaneConfig is not None
