from __future__ import annotations

from pathlib import Path

import pytest

from houmao.srv_ctrl.commands.runtime_artifacts import materialize_delegated_launch


def test_materialize_delegated_launch_rejects_retired_old_server_artifacts(
    tmp_path: Path,
) -> None:
    with pytest.raises(RuntimeError, match="houmao_server_rest.*retired"):
        materialize_delegated_launch(
            runtime_root=tmp_path,
            api_base_url="http://127.0.0.1:9889",
            session_name="cao-gpu",
            terminal_id="abcd1234",
            tmux_window_name="developer-1",
            provider="codex",
            agent_profile="gpu-kernel-coder",
            working_directory=tmp_path,
        )
