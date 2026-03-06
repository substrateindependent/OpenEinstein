"""Lane registry for concurrent campaign step dispatch.

Each lane represents a named concurrency slot with a configurable
semaphore cap and a queue mode that governs mid-run message handling.
"""

from __future__ import annotations

import enum
import threading
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class QueueMode(str, enum.Enum):
    """Governs how mid-run messages are handled in a lane."""

    COLLECT = "collect"
    FOLLOWUP = "followup"
    STEER = "steer"


class LaneConfig(BaseModel):
    """Configuration for a single concurrency lane."""

    name: str
    max_concurrent: int = Field(default=4, ge=1)
    queue_mode: QueueMode = QueueMode.COLLECT


class _LaneState:
    """Internal per-lane state with a counting semaphore."""

    __slots__ = ("config", "_semaphore", "_active", "_lock")

    def __init__(self, config: LaneConfig) -> None:
        self.config = config
        self._semaphore = threading.Semaphore(config.max_concurrent)
        self._active: int = 0
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Block until a slot is available, then occupy it."""
        self._semaphore.acquire()
        with self._lock:
            self._active += 1

    def release(self) -> None:
        """Release a slot. Raises RuntimeError if none are acquired."""
        with self._lock:
            if self._active <= 0:
                raise RuntimeError(
                    f"Cannot release lane '{self.config.name}': not acquired"
                )
            self._active -= 1
        self._semaphore.release()

    @property
    def active(self) -> int:
        with self._lock:
            return self._active


class LaneRegistry:
    """Registry of named concurrency lanes with semaphore-based caps."""

    def __init__(self, configs: dict[str, LaneConfig]) -> None:
        self._lanes: dict[str, _LaneState] = {
            name: _LaneState(cfg) for name, cfg in configs.items()
        }

    @property
    def lane_names(self) -> list[str]:
        return list(self._lanes.keys())

    def acquire(self, lane_name: str) -> None:
        """Acquire a concurrency slot in the named lane (blocks if full)."""
        state = self._lanes.get(lane_name)
        if state is None:
            raise KeyError(f"Unknown lane: {lane_name!r}")
        state.acquire()

    def release(self, lane_name: str) -> None:
        """Release a concurrency slot in the named lane."""
        state = self._lanes.get(lane_name)
        if state is None:
            raise KeyError(f"Unknown lane: {lane_name!r}")
        state.release()

    def lane_status(self) -> dict[str, dict[str, Any]]:
        """Return per-lane status with active count and max_concurrent."""
        return {
            name: {
                "active": state.active,
                "max_concurrent": state.config.max_concurrent,
                "queue_mode": state.config.queue_mode.value,
            }
            for name, state in self._lanes.items()
        }


def load_lane_config(path: Path) -> dict[str, LaneConfig]:
    """Load lane configuration from a YAML file.

    Expected format::

        lanes:
          main:
            max_concurrent: 4
            queue_mode: collect
          literature:
            max_concurrent: 2
            queue_mode: followup

    Raises:
        FileNotFoundError: if *path* does not exist.
        ValueError: if the YAML lacks a ``lanes`` top-level key.
    """
    if not path.exists():
        raise FileNotFoundError(f"Lane config file not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(raw, dict) or "lanes" not in raw:
        raise ValueError(
            f"Lane config must contain a top-level 'lanes' key: {path}"
        )

    lanes_raw = raw["lanes"]
    configs: dict[str, LaneConfig] = {}
    for name, entry in lanes_raw.items():
        configs[name] = LaneConfig(
            name=name,
            max_concurrent=entry.get("max_concurrent", 4),
            queue_mode=QueueMode(entry.get("queue_mode", "collect")),
        )
    return configs
