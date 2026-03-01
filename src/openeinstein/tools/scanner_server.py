"""Numerical scanner MCP server for viability-region exploration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import matplotlib.pyplot as plt
import numpy as np
from pydantic import BaseModel, Field

from openeinstein.tools.tool_bus import ToolBusError
from openeinstein.tools.types import ToolSpec


class ScanGridArgs(BaseModel):
    expression: str
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    steps: int = Field(default=25, ge=3)
    threshold: float = 0.0


class ScanAdaptiveArgs(BaseModel):
    expression: str
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    initial_steps: int = Field(default=10, ge=3)
    refine_steps: int = Field(default=20, ge=3)
    threshold: float = 0.0
    top_k: int = Field(default=5, ge=1)


class FindBoundaryArgs(BaseModel):
    expression: str
    x_min: float
    x_max: float
    y_value: float = 0.0
    steps: int = Field(default=200, ge=10)
    threshold: float = 0.0


@dataclass
class ScanResult:
    values: np.ndarray
    x_values: np.ndarray
    y_values: np.ndarray


class ScannerMCPServer:
    """Grid/adaptive scanner with simple expression evaluation."""

    def __init__(self, workspace: str | Path = ".openeinstein/scans") -> None:
        self._workspace = Path(workspace)
        self._workspace.mkdir(parents=True, exist_ok=True)
        self._started = False

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def health_check(self) -> bool:
        return self._started

    def list_tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(name="scan_grid", description="Grid scan over x/y parameter space"),
            ToolSpec(name="scan_adaptive", description="Adaptive scan with refinement"),
            ToolSpec(name="find_boundary", description="Find approximate threshold boundary"),
            ToolSpec(name="capabilities", description="List scanner capabilities"),
        ]

    def call_tool(self, tool_name: str, args: dict[str, Any]) -> Any:
        if not self._started:
            raise ToolBusError("Scanner server not started")

        if tool_name == "scan_grid":
            grid_args = ScanGridArgs.model_validate(args)
            result = self._scan_grid(grid_args)
            viable_mask = result.values <= grid_args.threshold
            plot_path = self._plot(
                x_values=result.x_values,
                y_values=result.y_values,
                values=result.values,
                viable_mask=viable_mask,
                label=f"grid-{uuid4().hex[:8]}",
            )
            viable_points = int(np.count_nonzero(viable_mask))
            total_points = int(result.values.size)
            return {
                "viable_points": viable_points,
                "total_points": total_points,
                "viable_ratio": viable_points / total_points,
                "plot_path": str(plot_path),
            }

        if tool_name == "scan_adaptive":
            adaptive_args = ScanAdaptiveArgs.model_validate(args)
            coarse = self._scan_grid(
                ScanGridArgs(
                    expression=adaptive_args.expression,
                    x_min=adaptive_args.x_min,
                    x_max=adaptive_args.x_max,
                    y_min=adaptive_args.y_min,
                    y_max=adaptive_args.y_max,
                    steps=adaptive_args.initial_steps,
                    threshold=adaptive_args.threshold,
                )
            )
            flat_indices = np.argsort(coarse.values, axis=None)[: adaptive_args.top_k]
            candidates: list[tuple[float, float]] = []
            for index in flat_indices:
                i, j = np.unravel_index(index, coarse.values.shape)
                candidates.append((float(coarse.x_values[j]), float(coarse.y_values[i])))

            best = candidates[0]
            span_x = (adaptive_args.x_max - adaptive_args.x_min) / adaptive_args.initial_steps
            span_y = (adaptive_args.y_max - adaptive_args.y_min) / adaptive_args.initial_steps
            refined = self._scan_grid(
                ScanGridArgs(
                    expression=adaptive_args.expression,
                    x_min=best[0] - span_x,
                    x_max=best[0] + span_x,
                    y_min=best[1] - span_y,
                    y_max=best[1] + span_y,
                    steps=adaptive_args.refine_steps,
                    threshold=adaptive_args.threshold,
                )
            )
            viable_mask = refined.values <= adaptive_args.threshold
            plot_path = self._plot(
                x_values=refined.x_values,
                y_values=refined.y_values,
                values=refined.values,
                viable_mask=viable_mask,
                label=f"adaptive-{uuid4().hex[:8]}",
            )
            return {
                "seed_points": candidates,
                "best_value": float(np.min(refined.values)),
                "viable_points": int(np.count_nonzero(viable_mask)),
                "plot_path": str(plot_path),
            }

        if tool_name == "find_boundary":
            boundary_args = FindBoundaryArgs.model_validate(args)
            x_values = np.linspace(boundary_args.x_min, boundary_args.x_max, boundary_args.steps)
            values = [
                self._evaluate(boundary_args.expression, x=float(x), y=float(boundary_args.y_value))
                for x in x_values
            ]
            shifted = [value - boundary_args.threshold for value in values]
            boundaries: list[float] = []
            for idx in range(len(shifted) - 1):
                left = shifted[idx]
                right = shifted[idx + 1]
                if left == 0:
                    boundaries.append(float(x_values[idx]))
                elif left * right < 0:
                    boundaries.append(float((x_values[idx] + x_values[idx + 1]) / 2))
            return {"boundaries": boundaries, "count": len(boundaries)}

        if tool_name == "capabilities":
            return {
                "backend": "scanner",
                "capabilities": ["scan_grid", "scan_adaptive", "find_boundary", "plot_output"],
            }

        raise ToolBusError(f"Unknown scanner tool: {tool_name}")

    def _scan_grid(self, args: ScanGridArgs) -> ScanResult:
        x_values = np.linspace(args.x_min, args.x_max, args.steps)
        y_values = np.linspace(args.y_min, args.y_max, args.steps)
        values = np.zeros((args.steps, args.steps), dtype=float)
        for i, y in enumerate(y_values):
            for j, x in enumerate(x_values):
                values[i, j] = self._evaluate(args.expression, x=float(x), y=float(y))
        return ScanResult(values=values, x_values=x_values, y_values=y_values)

    @staticmethod
    def _evaluate(expression: str, *, x: float, y: float) -> float:
        namespace = {"x": x, "y": y, "np": np}
        try:
            value = eval(expression, {"__builtins__": {}}, namespace)  # noqa: S307
        except Exception as exc:
            raise ToolBusError(f"Expression evaluation failed: {exc}") from exc
        return float(value)

    def _plot(
        self,
        *,
        x_values: np.ndarray,
        y_values: np.ndarray,
        values: np.ndarray,
        viable_mask: np.ndarray,
        label: str,
    ) -> Path:
        fig, ax = plt.subplots(figsize=(5, 4))
        mesh = ax.imshow(
            values,
            extent=(x_values.min(), x_values.max(), y_values.min(), y_values.max()),
            origin="lower",
            aspect="auto",
        )
        fig.colorbar(mesh, ax=ax, label="value")
        ys, xs = np.where(viable_mask)
        if len(xs):
            ax.scatter(x_values[xs], y_values[ys], s=8, c="white", alpha=0.8)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_title("Scanner viability map")
        path = self._workspace / f"{label}.png"
        fig.tight_layout()
        fig.savefig(path)
        plt.close(fig)
        return path
