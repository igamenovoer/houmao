"""Test DSH development preparation without network or personal runtime state."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType

import pytest


def _module() -> ModuleType:
    """Load the development utility independently of product package imports."""

    path = Path(__file__).resolve().parents[4] / "tools/dsh/prepare.py"
    spec = importlib.util.spec_from_file_location("dsh_prepare", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(source: Path, *arguments: str) -> str:
    """Operate only on the disposable repository selected by the test."""

    return subprocess.check_output(["git", "-C", str(source), *arguments], text=True).strip()


def _source(tmp_path: Path, module: ModuleType, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a local reference with a known package and revision."""

    source = tmp_path / "source"
    package = source / "apps/cli/package.json"
    package.parent.mkdir(parents=True)
    package.write_text(json.dumps({"name": "@deepseek-ai/dsh", "version": "1.2.3"}))
    _git(source, "init", "-q")
    _git(source, "add", ".")
    _git(
        source,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.test",
        "commit",
        "-qm",
        "fixture",
    )
    monkeypatch.setattr(module, "SOURCE_REVISION", _git(source, "rev-parse", "HEAD"))
    monkeypatch.setattr(module, "SOURCE_URL", str(source))
    return source


def _runtime(tmp_path: Path, version: str = "1.2.3") -> Path:
    """Create a synthetic package whose executable checks its isolated environment."""

    package = tmp_path / "runtime/node_modules/@deepseek-ai/dsh"
    (package / "lib").mkdir(parents=True)
    (package / "package.json").write_text(
        json.dumps({"name": "@deepseek-ai/dsh", "version": version})
    )
    executable = package / "lib/bin.js"
    executable.write_text(
        f"#!{sys.executable}\n"
        "import os\n"
        "from pathlib import Path\n"
        "assert 'DEEPSEEK_API_KEY' not in os.environ\n"
        "assert Path(os.environ['DSH_HOME']).parent == Path.cwd()\n"
        "assert os.environ['DSH_HOME'] != os.environ['DSH_AGENTS_HOME']\n"
        f"print({version!r})\n"
    )
    executable.chmod(0o755)
    return executable


def test_source_clone_is_pinned_and_repeatable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Clone a local reference and preserve an existing pinned checkout on repeat."""

    module = _module()
    _source(tmp_path, module, monkeypatch)
    output = tmp_path / "reference"
    first = module.prepare_source(output)
    assert first == module.prepare_source(output)
    assert first["revision"] == module.SOURCE_REVISION
    assert first["version"] == "1.2.3"


def test_existing_source_modifications_are_not_reset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Refuse a modified checkout without rewriting its tracked content."""

    module = _module()
    source = _source(tmp_path, module, monkeypatch)
    package = source / "apps/cli/package.json"
    package.write_text("modified\n")
    with pytest.raises(ValueError, match="tracked modifications"):
        module.prepare_source(source)
    assert package.read_text() == "modified\n"


def test_existing_source_revision_is_not_changed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Refuse a different revision rather than checking out the requested reference."""

    module = _module()
    source = _source(tmp_path, module, monkeypatch)
    previous = _git(source, "rev-parse", "HEAD")
    monkeypatch.setattr(module, "SOURCE_REVISION", "0" * 40)
    with pytest.raises(ValueError, match="existing checkout is unchanged"):
        module.prepare_source(source)
    assert _git(source, "rev-parse", "HEAD") == previous


def test_runtime_inventory_is_isolated_and_detects_code_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Identify actual package bytes while excluding ambient model credentials."""

    module = _module()
    source = _source(tmp_path, module, monkeypatch)
    executable = _runtime(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "synthetic-private-value")
    first = module.inspect_runtime(source, executable)
    (executable.parent / "another.js").write_text("export const changed = true;\n")
    second = module.inspect_runtime(source, executable)
    assert first["reported_version"] == "1.2.3"
    assert first["runtime_source_revision"] is None
    assert first["executable_sha256"] == second["executable_sha256"]
    assert first["dsh_package_code_sha256"] != second["dsh_package_code_sha256"]
    assert "synthetic-private-value" not in json.dumps(first)


def test_runtime_version_mismatch_is_explicit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Do not qualify an older executable from a matching tool name alone."""

    module = _module()
    source = _source(tmp_path, module, monkeypatch)
    with pytest.raises(ValueError, match="differs from pinned source"):
        module.inspect_runtime(source, _runtime(tmp_path, version="0.9.0"))


def test_foreign_runtime_directory_is_not_modified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep an existing developer installation outside helper ownership untouched."""

    module = _module()
    source = _source(tmp_path, module, monkeypatch)
    root = tmp_path / "personal-install"
    root.mkdir()
    original = root / "package.json"
    original.write_text('{"private": true}\n')
    with pytest.raises(ValueError, match="not owned by this helper"):
        module.prepare_runtime(source, root)
    assert original.read_text() == '{"private": true}\n'


def test_runtime_root_cannot_be_generated_in_product_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject package installations under tracked product paths before mutation."""

    module = _module()
    source = _source(tmp_path, module, monkeypatch)
    with pytest.raises(ValueError, match="outside the project"):
        module.prepare_runtime(source, module.PROJECT / "src/generated-dsh")
