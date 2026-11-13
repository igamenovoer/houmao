"""Installed metadata discovery tests without importing unselected implementations."""

from __future__ import annotations

from importlib.metadata import Distribution, EntryPoint
from pathlib import Path
from uuid import uuid4

import pytest

from houmao.gateway.plugins import PluginLoadError, load_plugin_definition


def _distribution_entry(
    tmp_path: Path, *, distribution: str, name: str, value: str, version: str = "1.0"
) -> EntryPoint:
    """Build real independent entry-point metadata in a hermetic directory."""

    info = tmp_path / f"{distribution}-{version}.dist-info"
    info.mkdir()
    (info / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {distribution}\nVersion: {version}\n", encoding="utf-8"
    )
    (info / "entry_points.txt").write_text(
        f"[houmao.gateway_plugins]\n{name} = {value}\n", encoding="utf-8"
    )
    return next(iter(Distribution.at(info).entry_points))


def test_selected_only_real_distribution_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Discovery loads only the enabled package and returns its metadata identity."""

    module = f"external_plugin_{uuid4().hex}"
    marker = tmp_path / "unselected-imported"
    (tmp_path / f"{module}.py").write_text(
        "from pydantic import BaseModel, ConfigDict\n"
        "from houmao.gateway.plugins import PluginDefinition\n"
        "class Config(BaseModel):\n    model_config = ConfigDict(strict=True, extra='forbid')\n    account: str = 'example'\n"
        "definition = PluginDefinition(config_model=Config, "
        "binding_identity=lambda config: config.account, create=lambda context,config: None)\n",
        encoding="utf-8",
    )
    (tmp_path / f"{module}_unused.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).touch()\nraise RuntimeError('unused')\n",
        encoding="utf-8",
    )
    candidates = [
        _distribution_entry(
            tmp_path, distribution="chosen", name="chosen", value=f"{module}:definition"
        ),
        _distribution_entry(
            tmp_path, distribution="unused", name="unused", value=f"{module}_unused:definition"
        ),
    ]
    monkeypatch.syspath_prepend(str(tmp_path))
    loaded = load_plugin_definition("chosen", candidates=candidates)
    assert (loaded.distribution, loaded.distribution_version) == ("chosen", "1.0")
    assert loaded.definition.binding_identity(loaded.definition.config_model()) == "example"
    assert not marker.exists()


def test_missing_selected_implementation() -> None:
    """Missing installed metadata is a safe per-instance load error."""

    with pytest.raises(PluginLoadError) as error:
        load_plugin_definition("missing", candidates=[])
    assert error.value.error_code == "implementation_missing"


def test_duplicate_advertised_names_never_import(tmp_path: Path) -> None:
    """Every ambiguous package is rejected before executing an entry point."""

    candidates = [
        _distribution_entry(
            tmp_path, distribution="bravo", name="same", value="missing:definition"
        ),
        _distribution_entry(
            tmp_path, distribution="alpha", name="same", value="missing:definition"
        ),
    ]
    with pytest.raises(PluginLoadError) as error:
        load_plugin_definition("same", candidates=candidates)
    assert error.value.error_code == "implementation_ambiguous"
    assert error.value.distributions == ("alpha", "bravo")


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("raise RuntimeError('private-sentinel')", "implementation_load_failed"),
        ("definition = object()", "invalid_definition"),
        (
            "from pydantic import BaseModel\nfrom houmao.gateway.plugins import PluginDefinition\n"
            "definition = PluginDefinition(config_model=BaseModel,binding_identity=str,create=str,sdk_version=2)",
            "sdk_version_unsupported",
        ),
        (
            "from pydantic import BaseModel\nfrom houmao.gateway.plugins import PluginDefinition\n"
            "definition = PluginDefinition(config_model=BaseModel,binding_identity=str,create=str,sdk_version=1.0)",
            "sdk_version_unsupported",
        ),
        (
            "from houmao.gateway.plugins import PluginDefinition\n"
            "definition = PluginDefinition(config_model=dict,binding_identity=str,create=str)",
            "invalid_definition",
        ),
        (
            "from pydantic import BaseModel\nfrom houmao.gateway.plugins import PluginDefinition\n"
            "definition = PluginDefinition(config_model=BaseModel,binding_identity=str,create=str)",
            "invalid_definition",
        ),
    ],
)
def test_invalid_selected_definition_is_sanitized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str, expected: str
) -> None:
    """Author contract failures cannot leak arbitrary import exception content."""

    module = f"invalid_plugin_{uuid4().hex}"
    (tmp_path / f"{module}.py").write_text(body, encoding="utf-8")
    entry = _distribution_entry(
        tmp_path, distribution="broken", name="broken", value=f"{module}:definition"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    with pytest.raises(PluginLoadError) as error:
        load_plugin_definition("broken", candidates=[entry])
    assert error.value.error_code == expected
    assert "private-sentinel" not in str(error.value)
