"""Unit tests for the ``houmao.srv_ctrl.commands.output`` module."""

from __future__ import annotations

import json
import os
from typing import Any
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner
from pydantic import BaseModel

from houmao.srv_ctrl.commands.output import (
    PRINT_STYLE_ENV_VAR,
    OutputContext,
    PrintStyle,
    emit,
    output_options,
    resolve_print_style,
)


# ---------------------------------------------------------------------------
# resolve_print_style
# ---------------------------------------------------------------------------


class TestResolvePrintStyle:
    """Tests for ``resolve_print_style()``."""

    def test_default_is_plain(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            assert resolve_print_style(None) == "plain"

    @pytest.mark.parametrize("style", ["plain", "json", "fancy"])
    def test_explicit_flag_wins(self, style: PrintStyle) -> None:
        with patch.dict(os.environ, {PRINT_STYLE_ENV_VAR: "json"}):
            assert resolve_print_style(style) == style

    @pytest.mark.parametrize("style", ["plain", "json", "fancy"])
    def test_env_var_used_when_no_flag(self, style: PrintStyle) -> None:
        with patch.dict(os.environ, {PRINT_STYLE_ENV_VAR: style}):
            assert resolve_print_style(None) == style

    def test_env_var_case_insensitive(self) -> None:
        with patch.dict(os.environ, {PRINT_STYLE_ENV_VAR: "JSON"}):
            assert resolve_print_style(None) == "json"

    def test_invalid_env_var_falls_back_to_plain(self) -> None:
        with patch.dict(os.environ, {PRINT_STYLE_ENV_VAR: "rainbow"}):
            assert resolve_print_style(None) == "plain"

    def test_invalid_explicit_falls_back_to_env(self) -> None:
        with patch.dict(os.environ, {PRINT_STYLE_ENV_VAR: "fancy"}):
            assert resolve_print_style("banana") == "fancy"


# ---------------------------------------------------------------------------
# Generic plain renderer
# ---------------------------------------------------------------------------


class TestRenderPlain:
    """Tests for the generic plain-text rendering path."""

    def _capture_plain(self, payload: object) -> str:
        ctx = OutputContext(style="plain")
        runner = CliRunner()

        @click.command()
        @click.pass_context
        def _cmd(click_ctx: click.Context) -> None:
            click_ctx.ensure_object(dict)
            click_ctx.obj["output"] = ctx
            emit(payload)

        result = runner.invoke(_cmd)
        assert result.exit_code == 0, result.output
        return result.output

    def test_flat_dict(self) -> None:
        out = self._capture_plain({"name": "alice", "age": 30})
        assert "name" in out
        assert "alice" in out
        assert "age" in out
        assert "30" in out

    def test_single_list_key_renders_table(self) -> None:
        out = self._capture_plain({"agents": [{"id": "a1", "status": "running"}]})
        assert "agents" in out
        assert "a1" in out
        assert "running" in out

    def test_none_renders_dash(self) -> None:
        out = self._capture_plain({"val": None})
        assert "-" in out

    def test_bool_renders_yes_no(self) -> None:
        out = self._capture_plain({"active": True, "paused": False})
        assert "yes" in out
        assert "no" in out


# ---------------------------------------------------------------------------
# Generic JSON renderer
# ---------------------------------------------------------------------------


class TestRenderJson:
    """Tests for the generic JSON rendering path."""

    def _capture_json(self, payload: object) -> dict[str, Any]:
        ctx = OutputContext(style="json")
        runner = CliRunner()

        @click.command()
        @click.pass_context
        def _cmd(click_ctx: click.Context) -> None:
            click_ctx.ensure_object(dict)
            click_ctx.obj["output"] = ctx
            emit(payload)

        result = runner.invoke(_cmd)
        assert result.exit_code == 0, result.output
        return json.loads(result.output)

    def test_dict_roundtrip(self) -> None:
        data = {"key": "value", "count": 42}
        parsed = self._capture_json(data)
        assert parsed == data

    def test_pydantic_model_serialized(self) -> None:
        class _Model(BaseModel):
            name: str
            count: int

        parsed = self._capture_json(_Model(name="test", count=7))
        assert parsed == {"name": "test", "count": 7}


# ---------------------------------------------------------------------------
# Generic fancy renderer (smoke test)
# ---------------------------------------------------------------------------


class TestRenderFancy:
    """Smoke test: fancy renderer runs without error."""

    def _capture_fancy(self, payload: object) -> str:
        ctx = OutputContext(style="fancy")
        runner = CliRunner()

        @click.command()
        @click.pass_context
        def _cmd(click_ctx: click.Context) -> None:
            click_ctx.ensure_object(dict)
            click_ctx.obj["output"] = ctx
            emit(payload)

        result = runner.invoke(_cmd)
        assert result.exit_code == 0, result.output
        return result.output

    def test_dict_no_crash(self) -> None:
        out = self._capture_fancy({"name": "alice", "role": "admin"})
        assert "alice" in out

    def test_list_of_dicts_no_crash(self) -> None:
        out = self._capture_fancy({"items": [{"id": 1}, {"id": 2}]})
        assert out  # non-empty


# ---------------------------------------------------------------------------
# emit() dispatch
# ---------------------------------------------------------------------------


class TestEmitDispatch:
    """Tests that ``emit()`` routes to the correct renderer."""

    def test_custom_plain_renderer(self) -> None:
        called: list[object] = []

        def _plain(payload: object) -> None:
            called.append(payload)
            click.echo("PLAIN_CUSTOM")

        ctx = OutputContext(style="plain")
        runner = CliRunner()

        @click.command()
        @click.pass_context
        def _cmd(click_ctx: click.Context) -> None:
            click_ctx.ensure_object(dict)
            click_ctx.obj["output"] = ctx
            emit({"x": 1}, plain_renderer=_plain)

        result = runner.invoke(_cmd)
        assert result.exit_code == 0
        assert "PLAIN_CUSTOM" in result.output
        assert len(called) == 1

    def test_custom_fancy_renderer(self) -> None:
        called: list[object] = []

        def _fancy(payload: object) -> None:
            called.append(payload)
            click.echo("FANCY_CUSTOM")

        ctx = OutputContext(style="fancy")
        runner = CliRunner()

        @click.command()
        @click.pass_context
        def _cmd(click_ctx: click.Context) -> None:
            click_ctx.ensure_object(dict)
            click_ctx.obj["output"] = ctx
            emit({"x": 1}, fancy_renderer=_fancy)

        result = runner.invoke(_cmd)
        assert result.exit_code == 0
        assert "FANCY_CUSTOM" in result.output
        assert len(called) == 1

    def test_json_ignores_custom_renderers(self) -> None:
        """JSON mode always uses the standard JSON renderer."""
        ctx = OutputContext(style="json")
        runner = CliRunner()

        @click.command()
        @click.pass_context
        def _cmd(click_ctx: click.Context) -> None:
            click_ctx.ensure_object(dict)
            click_ctx.obj["output"] = ctx
            emit({"x": 1}, plain_renderer=lambda _: None, fancy_renderer=lambda _: None)

        result = runner.invoke(_cmd)
        parsed = json.loads(result.output)
        assert parsed == {"x": 1}

    def test_fallback_without_click_context(self) -> None:
        """When called outside a click context, emit() defaults to plain."""
        runner = CliRunner()

        @click.command()
        def _cmd() -> None:
            # No obj["output"] set — should fall back gracefully
            emit({"status": "ok"})

        result = runner.invoke(_cmd)
        assert result.exit_code == 0
        assert "status" in result.output


# ---------------------------------------------------------------------------
# CLI integration: --print-json flag
# ---------------------------------------------------------------------------


class TestPrintJsonFlag:
    """Integration test: ``--print-json`` produces parseable JSON."""

    def test_print_json_flag(self) -> None:
        runner = CliRunner()

        @click.group()
        @output_options
        @click.pass_context
        def root(ctx: click.Context, print_style: str | None) -> None:
            ctx.ensure_object(dict)
            ctx.obj["output"] = OutputContext(style=resolve_print_style(print_style))

        @root.command()
        def show() -> None:
            emit({"answer": 42})

        result = runner.invoke(root, ["--print-json", "show"])
        assert result.exit_code == 0, result.output
        parsed = json.loads(result.output)
        assert parsed == {"answer": 42}

    def test_default_is_plain(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HOUMAO_CLI_PRINT_STYLE", raising=False)
        runner = CliRunner()

        @click.group()
        @output_options
        @click.pass_context
        def root(ctx: click.Context, print_style: str | None) -> None:
            ctx.ensure_object(dict)
            ctx.obj["output"] = OutputContext(style=resolve_print_style(print_style))

        @root.command()
        def show() -> None:
            emit({"answer": 42})

        result = runner.invoke(root, ["show"])
        assert result.exit_code == 0
        # Should NOT be JSON
        with pytest.raises(json.JSONDecodeError):
            json.loads(result.output)
        assert "answer" in result.output
        assert "42" in result.output
