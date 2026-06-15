from __future__ import annotations

from houmao.srv_ctrl.commands.agents import core as agents_core
from houmao.srv_ctrl.commands import managed_agents


def test_control_cli_kimi_process_allowlists_include_observed_names() -> None:
    assert agents_core._JOIN_SUPPORTED_PROCESSES["kimi"] == ("kimi-code", "kimi")  # noqa: SLF001
    assert managed_agents._SUPPORTED_LOCAL_TUI_PROCESSES["kimi"] == (  # noqa: SLF001
        "kimi-code",
        "kimi",
    )
