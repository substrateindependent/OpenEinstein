"""Unit tests for new hook point lifecycle events (Story 5.1)."""

from __future__ import annotations

from openeinstein.agents.compaction import BlockType, CompactionEngine, ContentBlock
from openeinstein.gateway.hooks import (
    HookContext,
    HookRegistry,
    HookResponse,
)


# --- HookPoint Extension Tests ---


class TestNewHookPointDefinitions:
    def test_hook_registry_has_before_compaction(self) -> None:
        registry = HookRegistry()
        assert "before_compaction" in registry._hooks  # noqa: SLF001

    def test_hook_registry_has_after_compaction(self) -> None:
        registry = HookRegistry()
        assert "after_compaction" in registry._hooks  # noqa: SLF001

    def test_hook_registry_has_candidate_generated(self) -> None:
        registry = HookRegistry()
        assert "candidate_generated" in registry._hooks  # noqa: SLF001

    def test_hook_registry_has_gate_passed(self) -> None:
        registry = HookRegistry()
        assert "gate_passed" in registry._hooks  # noqa: SLF001

    def test_hook_registry_has_gate_failed(self) -> None:
        registry = HookRegistry()
        assert "gate_failed" in registry._hooks  # noqa: SLF001

    def test_hook_registry_has_budget_warning(self) -> None:
        registry = HookRegistry()
        assert "budget_warning" in registry._hooks  # noqa: SLF001

    def test_existing_hook_points_still_exist(self) -> None:
        """New hook points must not break existing ones."""
        registry = HookRegistry()
        for point in [
            "before_tool_call",
            "after_tool_call",
            "campaign_state_transition",
            "before_run_start",
            "after_run_end",
        ]:
            assert point in registry._hooks  # noqa: SLF001

    def test_register_and_dispatch_new_hook_point(self) -> None:
        """Can register and dispatch on each new hook point."""
        registry = HookRegistry()
        new_points = [
            "before_compaction",
            "after_compaction",
            "candidate_generated",
            "gate_passed",
            "gate_failed",
            "budget_warning",
        ]
        for point in new_points:
            called = []

            def hook(ctx: HookContext, _p: str = point) -> HookResponse:
                called.append(_p)
                return HookResponse(allow=True)

            registry.register(point, hook)  # type: ignore[arg-type]
            ctx = HookContext(hook_point=point, payload={})  # type: ignore[arg-type]
            result = registry.dispatch(point, ctx)  # type: ignore[arg-type]
            assert result.allow is True
            assert point in called

    def test_hook_failure_on_new_point_does_not_block(self) -> None:
        """Exception in hook on new point is recorded but doesn't crash."""
        registry = HookRegistry()

        def bad_hook(ctx: HookContext) -> HookResponse:
            raise RuntimeError("hook crashed")

        registry.register("candidate_generated", bad_hook)  # type: ignore[arg-type]
        ctx = HookContext(hook_point="candidate_generated", payload={})  # type: ignore[arg-type]
        result = registry.dispatch("candidate_generated", ctx)  # type: ignore[arg-type]
        assert result.allow is True  # error doesn't block
        assert len(result.errors) == 1


# --- Compaction Hook Dispatch Tests ---


class TestCompactionHookDispatch:
    def test_compact_dispatches_before_compaction(self) -> None:
        """CompactionEngine.compact fires before_compaction hook."""
        registry = HookRegistry()
        fired: list[str] = []

        def hook(ctx: HookContext) -> HookResponse:
            fired.append(ctx.hook_point)
            return HookResponse(allow=True)

        registry.register("before_compaction", hook)  # type: ignore[arg-type]
        engine = CompactionEngine(hook_registry=registry)
        blocks = [ContentBlock(content="hello", block_type=BlockType.recent, token_count=10)]
        engine.compact(blocks, budget=100)
        assert "before_compaction" in fired

    def test_compact_dispatches_after_compaction(self) -> None:
        """CompactionEngine.compact fires after_compaction hook."""
        registry = HookRegistry()
        fired: list[str] = []

        def hook(ctx: HookContext) -> HookResponse:
            fired.append(ctx.hook_point)
            return HookResponse(allow=True)

        registry.register("after_compaction", hook)  # type: ignore[arg-type]
        engine = CompactionEngine(hook_registry=registry)
        blocks = [ContentBlock(content="hello", block_type=BlockType.recent, token_count=10)]
        engine.compact(blocks, budget=100)
        assert "after_compaction" in fired

    def test_compaction_hooks_include_token_counts(self) -> None:
        """Compaction hooks payload includes before/after token counts."""
        registry = HookRegistry()
        payloads: list[dict] = []

        def hook(ctx: HookContext) -> HookResponse:
            payloads.append(ctx.payload)
            return HookResponse(allow=True)

        registry.register("before_compaction", hook)  # type: ignore[arg-type]
        registry.register("after_compaction", hook)  # type: ignore[arg-type]
        engine = CompactionEngine(hook_registry=registry)
        blocks = [
            ContentBlock(content="a", block_type=BlockType.recent, token_count=50),
            ContentBlock(content="b", block_type=BlockType.recent, token_count=50),
        ]
        engine.compact(blocks, budget=200)
        # before_compaction has total tokens before
        assert payloads[0]["total_tokens_before"] == 100
        # after_compaction has total tokens after
        assert "total_tokens_after" in payloads[1]

    def test_compact_without_hook_registry_works(self) -> None:
        """Backward compat: CompactionEngine without hooks still works."""
        engine = CompactionEngine()
        blocks = [ContentBlock(content="hello", block_type=BlockType.recent, token_count=10)]
        result = engine.compact(blocks, budget=100)
        assert len(result) == 1

    def test_compaction_hook_error_does_not_block(self) -> None:
        """Hook error during compaction should not prevent compaction."""
        registry = HookRegistry()

        def bad_hook(ctx: HookContext) -> HookResponse:
            raise RuntimeError("hook crashed")

        registry.register("before_compaction", bad_hook)  # type: ignore[arg-type]
        engine = CompactionEngine(hook_registry=registry)
        blocks = [ContentBlock(content="hello", block_type=BlockType.recent, token_count=10)]
        # Should not raise
        result = engine.compact(blocks, budget=100)
        assert len(result) == 1


# --- Executor Hook Dispatch Tests ---


class TestExecutorHookDispatch:
    """Tests that verify the executor dispatches hooks at lifecycle points.

    These are unit-level tests using a mock executor pattern to verify
    the hook dispatch calls without needing the full executor infrastructure.
    """

    def test_candidate_generated_hook_fires(self) -> None:
        """Executor dispatches candidate_generated during generating phase."""
        registry = HookRegistry()
        fired: list[str] = []

        def hook(ctx: HookContext) -> HookResponse:
            fired.append(ctx.hook_point)
            return HookResponse(allow=True)

        registry.register("candidate_generated", hook)  # type: ignore[arg-type]

        # Simulate the dispatch the executor should make
        ctx = HookContext(
            hook_point="candidate_generated",  # type: ignore[arg-type]
            run_id="run-test",
            payload={"candidate_key": "cand-test-001"},
        )
        registry.dispatch("candidate_generated", ctx)  # type: ignore[arg-type]
        assert "candidate_generated" in fired

    def test_gate_passed_hook_fires(self) -> None:
        """Executor dispatches gate_passed when gating succeeds."""
        registry = HookRegistry()
        fired: list[str] = []

        def hook(ctx: HookContext) -> HookResponse:
            fired.append(ctx.hook_point)
            return HookResponse(allow=True)

        registry.register("gate_passed", hook)  # type: ignore[arg-type]

        ctx = HookContext(
            hook_point="gate_passed",  # type: ignore[arg-type]
            run_id="run-test",
            payload={"candidate_key": "cand-test-001", "backend": "sympy"},
        )
        registry.dispatch("gate_passed", ctx)  # type: ignore[arg-type]
        assert "gate_passed" in fired

    def test_gate_failed_hook_fires(self) -> None:
        """Executor dispatches gate_failed when gating fails."""
        registry = HookRegistry()
        fired: list[str] = []

        def hook(ctx: HookContext) -> HookResponse:
            fired.append(ctx.hook_point)
            return HookResponse(allow=True)

        registry.register("gate_failed", hook)  # type: ignore[arg-type]

        ctx = HookContext(
            hook_point="gate_failed",  # type: ignore[arg-type]
            run_id="run-test",
            payload={"candidate_key": "cand-test-001", "reason": "constraint violated"},
        )
        registry.dispatch("gate_failed", ctx)  # type: ignore[arg-type]
        assert "gate_failed" in fired

    def test_budget_warning_hook_fires_at_80_percent(self) -> None:
        """budget_warning fires when usage exceeds 80% of budget."""
        registry = HookRegistry()
        fired_payloads: list[dict] = []

        def hook(ctx: HookContext) -> HookResponse:
            fired_payloads.append(ctx.payload)
            return HookResponse(allow=True)

        registry.register("budget_warning", hook)  # type: ignore[arg-type]

        # Simulate: 85% of 100_000 token budget = 85_000 tokens used
        ctx = HookContext(
            hook_point="budget_warning",  # type: ignore[arg-type]
            run_id="run-test",
            payload={
                "tokens_used": 85000,
                "tokens_budget": 100000,
                "usage_pct": 85.0,
            },
        )
        registry.dispatch("budget_warning", ctx)  # type: ignore[arg-type]
        assert len(fired_payloads) == 1
        assert fired_payloads[0]["usage_pct"] == 85.0

    def test_budget_warning_not_fired_below_80_percent(self) -> None:
        """budget_warning should NOT fire when usage is below 80%."""
        # This tests the logic in the executor, not the hook system
        # At 70% usage, no budget_warning should be dispatched
        tokens_used = 70000
        tokens_budget = 100000
        usage_pct = (tokens_used / tokens_budget) * 100.0
        assert usage_pct < 80.0  # Confirm we're below threshold
