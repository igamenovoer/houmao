from __future__ import annotations

from click.testing import CliRunner

from houmao.srv_ctrl.commands.main import cli


def test_internals_help_omits_command_templates() -> None:
    """Internals help does not advertise the retired command-template surface."""

    result = CliRunner().invoke(cli, ["internals", "--help"])

    assert result.exit_code == 0, result.output
    assert "config-drafts" in result.output
    assert "command-templates" not in result.output


def test_command_templates_group_is_unavailable() -> None:
    """The retired command-template group fails as an unknown command."""

    result = CliRunner().invoke(cli, ["internals", "command-templates", "list"])

    assert result.exit_code != 0
    assert "No such command" in result.output
