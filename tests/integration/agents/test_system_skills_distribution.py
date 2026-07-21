"""Distribution coverage for the complete static system-skill collection."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import zipfile


REPO_ROOT = Path(__file__).resolve().parents[3]
PUBLIC_NAMES = {
    "houmao-admin-welcome",
    "houmao-admin-entrypoint",
    "houmao-agent-entrypoint",
    "houmao-shared-routines",
    "houmao-agent-loop-pro",
    "houmao-agent-loop-lite",
}


def _strip_sdist_prefix(name: str) -> str:
    """Remove the generated source-distribution root directory."""

    parts = PurePosixPath(name).parts
    return PurePosixPath(*parts[1:]).as_posix() if len(parts) > 1 else ""


def _assert_static_collection(names: set[str], *, package_root: str) -> None:
    """Assert one archive contains complete roots, children, scripts, and assets."""

    public_prefix = f"{package_root}/agents/assets/system_skills/public"
    discovered = {
        PurePosixPath(name).parent.name
        for name in names
        if name.startswith(f"{public_prefix}/")
        and name.endswith("/SKILL.md")
        and len(PurePosixPath(name).relative_to(public_prefix).parts) == 2
    }
    assert discovered == PUBLIC_NAMES

    shared_prefix = f"{public_prefix}/houmao-shared-routines/subskills"
    children = {
        PurePosixPath(name).parent.name
        for name in names
        if name.startswith(f"{shared_prefix}/") and name.endswith("/SKILL-MAIN.md")
    }
    assert len(children) == 16
    assert not any(
        name.startswith(f"{package_root}/agents/assets/system_skills/protected/") for name in names
    )
    assert f"{public_prefix}/houmao-agent-loop-pro/scripts/scaffold.py" in names
    assert f"{public_prefix}/houmao-agent-loop-lite/scripts/scaffold.py" in names
    assert (
        f"{public_prefix}/houmao-agent-loop-pro/assets/scaffolds/execplan/manifest.toml.tmpl"
        in names
    )
    assert f"{public_prefix}/houmao-shared-routines/agents/openai.yaml" in names


def test_wheel_and_sdist_contain_complete_static_system_skills(tmp_path: Path) -> None:
    """Built artifacts preserve all static skill files and omit active composition sources."""

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--sdist",
            "--wheel",
            "--outdir",
            str(tmp_path),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stderr

    wheel_path = next(tmp_path.glob("*.whl"))
    sdist_path = next(tmp_path.glob("*.tar.gz"))
    with zipfile.ZipFile(wheel_path) as archive:
        wheel_names = set(archive.namelist())
    with tarfile.open(sdist_path, mode="r:gz") as archive:
        sdist_names = {_strip_sdist_prefix(name) for name in archive.getnames()}

    _assert_static_collection(wheel_names, package_root="houmao")
    _assert_static_collection(sdist_names, package_root="src/houmao")
