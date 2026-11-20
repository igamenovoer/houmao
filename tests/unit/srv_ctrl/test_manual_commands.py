"""CLI contracts for the packaged operator manual."""

from __future__ import annotations

import json
import re
import socket
import subprocess
from importlib.resources import files
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from houmao.srv_ctrl.commands import managed_agents, manual, project
from houmao.srv_ctrl.commands.main import cli


def _forbid_operation(*_args: object, **_kwargs: object) -> None:
    """Fail if a read invokes an operational entry point."""

    pytest.fail("Reading the manual must only use local packaged content")


@pytest.fixture
def offline_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """Set up an empty home and workdir with operational entry points guarded."""

    home = tmp_path / "home"
    workdir = tmp_path / "workdir"
    home.mkdir()
    workdir.mkdir()
    monkeypatch.chdir(workdir)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(home / ".local" / "state"))
    monkeypatch.delenv("HOUMAO_CLI_PRINT_STYLE", raising=False)
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("TMUX_PANE", raising=False)
    monkeypatch.setattr(project, "resolve_project_aware_local_roots", _forbid_operation)
    monkeypatch.setattr(project, "bootstrap_project_overlay_at_root", _forbid_operation)
    monkeypatch.setattr(managed_agents, "resolve_managed_agent_target", _forbid_operation)
    monkeypatch.setattr(subprocess, "Popen", _forbid_operation)
    monkeypatch.setattr(socket.socket, "connect", _forbid_operation)
    monkeypatch.setattr(click, "echo_via_pager", _forbid_operation)
    return home, workdir


def _manual_references(content: str) -> set[tuple[str, ...]]:
    """Collect copyable command paths from a manual index."""

    references = re.findall(r"`houmao-mgr (manual(?: [a-z-]+)*)`", content)
    return {tuple(reference.split()) for reference in references}


def test_all_manual_documents_match_registered_navigation(
    offline_workspace: tuple[Path, Path],
) -> None:
    runner = CliRunner()
    resources = files("houmao.srv_ctrl").joinpath("assets", "manual")
    manual_path = ("manual",)
    documents = {manual_path: resources.joinpath("index.md")}
    for catalog_name, catalog in manual.manual_group.commands.items():
        assert isinstance(catalog, click.Group)
        catalog_path = (*manual_path, catalog_name)
        documents[catalog_path] = resources.joinpath(catalog_name, "index.md")
        for page_name in catalog.commands:
            documents[(*catalog_path, page_name)] = resources.joinpath(
                catalog_name, f"{page_name}.md"
            )

    assert len(documents) == 23
    for path, resource in documents.items():
        result = runner.invoke(cli, list(path))
        assert result.exit_code == 0, result.output
        assert result.output == resource.read_text(encoding="utf-8")
        if resource.name == "index.md":
            references = _manual_references(result.output)
            assert references <= documents.keys()
            children = {candidate for candidate in documents if candidate[:-1] == path}
            listed_children = {ref for ref in references if len(ref) == len(path) + 1}
            assert listed_children == children

    for directory in offline_workspace:
        assert list(directory.iterdir()) == []


@pytest.mark.parametrize("path", [[], ["start"], ["start", "first-agent"]])
def test_manual_help_uses_click_without_loading_documents(
    path: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(manual, "files", _forbid_operation)
    result = CliRunner().invoke(cli, ["manual", *path, "--help"])
    assert result.exit_code == 0, result.output
    assert "Usage: houmao-mgr manual" in result.output
    assert "--help" in result.output


@pytest.mark.parametrize("path", [["unknown"], ["start", "unknown"]])
def test_unknown_manual_command_uses_click_error(
    path: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(manual, "files", _forbid_operation)
    result = CliRunner().invoke(cli, ["manual", *path])
    assert result.exit_code == 2
    assert "No such command 'unknown'." in result.output


def test_missing_manual_document_reports_the_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(manual, "files", lambda _package: tmp_path)
    result = CliRunner().invoke(cli, ["manual", "start", "first-agent"])
    assert result.exit_code == 1
    assert "Manual document for `houmao-mgr manual start first-agent` is unavailable." in (
        result.output
    )


def test_manual_respects_root_output_styles(
    offline_workspace: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = CliRunner()
    path = ["manual", "coordinate", "team"]
    monkeypatch.setenv("HOUMAO_CLI_PRINT_STYLE", "json")

    structured = runner.invoke(cli, path)
    plain = runner.invoke(cli, ["--print-plain", *path])
    fancy = runner.invoke(cli, ["--print-fancy", *path])
    for result in (structured, plain, fancy):
        assert result.exit_code == 0, result.output
    assert json.loads(structured.output) == {"path": path, "content": plain.output}
    assert plain.output.startswith("# Coordinate a Builder and Reviewer\n")
    assert "Coordinate a Builder and Reviewer" in fancy.output
    assert "# Coordinate a Builder and Reviewer" not in fancy.output
