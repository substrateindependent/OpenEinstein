"""Tests for Tool Sandbox Profiles & Registry (Story 4.2)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from openeinstein.security.core import ToolSandboxProfile, ToolProfileRegistry


# --- ToolSandboxProfile model tests ---


class TestToolSandboxProfile:
    def test_minimal_defaults(self) -> None:
        """Profile with no explicit permissions defaults to deny-all."""
        profile = ToolSandboxProfile(tool_name_pattern="*")
        assert profile.allow_network is False
        assert profile.allow_fs_write is False
        assert profile.allow_shell is False
        assert profile.max_tokens_per_call is None
        assert profile.max_calls_per_run is None

    def test_explicit_permissions(self) -> None:
        profile = ToolSandboxProfile(
            tool_name_pattern="arxiv_*",
            allow_network=True,
            allow_fs_write=False,
            allow_shell=False,
            max_tokens_per_call=5000,
            max_calls_per_run=10,
        )
        assert profile.tool_name_pattern == "arxiv_*"
        assert profile.allow_network is True
        assert profile.max_tokens_per_call == 5000
        assert profile.max_calls_per_run == 10

    def test_preset_field(self) -> None:
        profile = ToolSandboxProfile(
            tool_name_pattern="*",
            preset="minimal",
        )
        assert profile.preset == "minimal"

    def test_inherits_field(self) -> None:
        profile = ToolSandboxProfile(
            tool_name_pattern="*",
            inherits="minimal",
        )
        assert profile.inherits == "minimal"


# --- Deny-wins merge logic ---


class TestDenyWinsMerge:
    def test_deny_overrides_allow(self) -> None:
        """When merging profiles, any deny (False) overrides allow (True)."""
        base = ToolSandboxProfile(
            tool_name_pattern="*",
            allow_network=True,
            allow_fs_write=True,
            allow_shell=True,
        )
        overlay = ToolSandboxProfile(
            tool_name_pattern="restricted_*",
            allow_network=False,
            allow_fs_write=True,
            allow_shell=False,
        )
        merged = ToolProfileRegistry.merge_profiles(base, overlay)
        assert merged.allow_network is False  # deny wins
        assert merged.allow_fs_write is True  # both allow
        assert merged.allow_shell is False  # deny wins

    def test_merge_uses_overlay_pattern(self) -> None:
        base = ToolSandboxProfile(tool_name_pattern="*")
        overlay = ToolSandboxProfile(tool_name_pattern="special_*")
        merged = ToolProfileRegistry.merge_profiles(base, overlay)
        assert merged.tool_name_pattern == "special_*"

    def test_merge_takes_stricter_limits(self) -> None:
        """Merge should pick the lower (stricter) numeric limit."""
        base = ToolSandboxProfile(
            tool_name_pattern="*",
            max_tokens_per_call=10000,
            max_calls_per_run=50,
        )
        overlay = ToolSandboxProfile(
            tool_name_pattern="*",
            max_tokens_per_call=5000,
            max_calls_per_run=100,
        )
        merged = ToolProfileRegistry.merge_profiles(base, overlay)
        assert merged.max_tokens_per_call == 5000  # lower wins
        assert merged.max_calls_per_run == 50  # lower wins

    def test_merge_none_limit_treated_as_unlimited(self) -> None:
        base = ToolSandboxProfile(tool_name_pattern="*", max_tokens_per_call=None)
        overlay = ToolSandboxProfile(tool_name_pattern="*", max_tokens_per_call=5000)
        merged = ToolProfileRegistry.merge_profiles(base, overlay)
        assert merged.max_tokens_per_call == 5000  # concrete wins over None


# --- ToolProfileRegistry ---


class TestToolProfileRegistry:
    def test_builtin_presets_exist(self) -> None:
        """Registry ships with minimal, research, full presets."""
        registry = ToolProfileRegistry()
        minimal = registry.get_preset("minimal")
        research = registry.get_preset("research")
        full = registry.get_preset("full")

        # minimal: all denied
        assert minimal.allow_network is False
        assert minimal.allow_fs_write is False
        assert minimal.allow_shell is False

        # research: network allowed
        assert research.allow_network is True
        assert research.allow_fs_write is False
        assert research.allow_shell is False

        # full: all allowed
        assert full.allow_network is True
        assert full.allow_fs_write is True
        assert full.allow_shell is True

    def test_unknown_tool_falls_back_to_minimal(self) -> None:
        """Tools with no matching profile get the minimal preset."""
        registry = ToolProfileRegistry()
        profile = registry.get_profile("completely_unknown_tool")
        assert profile.allow_network is False
        assert profile.allow_fs_write is False
        assert profile.allow_shell is False

    def test_glob_matching(self) -> None:
        """Profile with glob pattern matches tool names."""
        registry = ToolProfileRegistry()
        registry.register_profile(
            ToolSandboxProfile(
                tool_name_pattern="arxiv_*",
                allow_network=True,
            )
        )
        profile = registry.get_profile("arxiv_search")
        assert profile.allow_network is True

        # Non-matching tool should still get minimal
        profile2 = registry.get_profile("shell_exec")
        assert profile2.allow_network is False

    def test_exact_name_beats_glob(self) -> None:
        """Exact tool name match has priority over glob patterns."""
        registry = ToolProfileRegistry()
        registry.register_profile(
            ToolSandboxProfile(tool_name_pattern="arxiv_*", allow_network=True)
        )
        registry.register_profile(
            ToolSandboxProfile(
                tool_name_pattern="arxiv_search",
                allow_network=False,  # override for this specific tool
            )
        )
        profile = registry.get_profile("arxiv_search")
        assert profile.allow_network is False  # exact match wins

    def test_preset_inheritance(self) -> None:
        """Profile inheriting from a preset gets base permissions merged."""
        registry = ToolProfileRegistry()
        registry.register_profile(
            ToolSandboxProfile(
                tool_name_pattern="lit_*",
                inherits="research",
                max_tokens_per_call=8000,
            )
        )
        profile = registry.get_profile("lit_search")
        # Inherits from research: network=True, fs_write=False, shell=False
        assert profile.allow_network is True
        assert profile.allow_fs_write is False
        assert profile.max_tokens_per_call == 8000

    def test_circular_inheritance_detected(self) -> None:
        """Circular preset inheritance raises error."""
        registry = ToolProfileRegistry()
        # Create custom presets that form a cycle
        registry.register_preset(
            "preset_a",
            ToolSandboxProfile(tool_name_pattern="*", inherits="preset_b"),
        )
        registry.register_preset(
            "preset_b",
            ToolSandboxProfile(tool_name_pattern="*", inherits="preset_a"),
        )
        registry.register_profile(
            ToolSandboxProfile(tool_name_pattern="cyclic_tool", inherits="preset_a")
        )
        with pytest.raises(ValueError, match="[Cc]ircular"):
            registry.get_profile("cyclic_tool")


# --- YAML loading ---


class TestYAMLLoading:
    def test_load_from_yaml(self, tmp_path: Path) -> None:
        yaml_content = textwrap.dedent("""\
            presets:
              minimal:
                allow_network: false
                allow_fs_write: false
                allow_shell: false
              research:
                inherits: minimal
                allow_network: true
              full:
                allow_network: true
                allow_fs_write: true
                allow_shell: true

            profiles:
              - tool_name_pattern: "arxiv_*"
                inherits: research
                max_tokens_per_call: 5000
              - tool_name_pattern: "shell_exec"
                inherits: full
                allow_shell: true
        """)
        yaml_file = tmp_path / "tool-profiles.yaml"
        yaml_file.write_text(yaml_content)

        registry = ToolProfileRegistry.from_yaml(yaml_file)

        # arxiv_search matches arxiv_* → inherits research (network=True)
        profile = registry.get_profile("arxiv_search")
        assert profile.allow_network is True
        assert profile.allow_fs_write is False
        assert profile.max_tokens_per_call == 5000

        # shell_exec matches exact → inherits full
        profile2 = registry.get_profile("shell_exec")
        assert profile2.allow_shell is True
        assert profile2.allow_network is True

    def test_empty_yaml_loads_with_defaults(self, tmp_path: Path) -> None:
        """Empty YAML file loads with builtin presets."""
        yaml_file = tmp_path / "tool-profiles.yaml"
        yaml_file.write_text("")

        registry = ToolProfileRegistry.from_yaml(yaml_file)
        # Should still have builtin presets
        profile = registry.get_profile("any_tool")
        assert profile.allow_network is False  # minimal fallback

    def test_malformed_yaml_raises(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "tool-profiles.yaml"
        yaml_file.write_text("{{invalid yaml: [")

        with pytest.raises(Exception):
            ToolProfileRegistry.from_yaml(yaml_file)

    def test_missing_yaml_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            ToolProfileRegistry.from_yaml(Path("/nonexistent/tool-profiles.yaml"))


# --- Integration wiring ---


class TestIntegrationWiring:
    def test_importable_from_security(self) -> None:
        """Verify public exports from the security package."""
        from openeinstein.security import ToolSandboxProfile, ToolProfileRegistry  # noqa: F401

    def test_get_profile_resolves_with_inheritance(self) -> None:
        """Full round-trip: register preset, register profile, get_profile resolves."""
        registry = ToolProfileRegistry()
        registry.register_profile(
            ToolSandboxProfile(
                tool_name_pattern="compute_*",
                inherits="research",
                max_calls_per_run=20,
            )
        )
        result = registry.get_profile("compute_integral")
        assert result.allow_network is True  # from research
        assert result.allow_fs_write is False  # research inherits minimal
        assert result.max_calls_per_run == 20
