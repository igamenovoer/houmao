"""Prepare a pinned DSH reference and identify an isolated development executable.

This utility never launches an agent, loads credentials, or changes a personal DSH home.
Published package identity and source identity are recorded separately.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version


PROJECT = Path(__file__).resolve().parents[2]
SOURCE_REVISION = "39163dd30f703a79079e2d2446545cff3c453738"
SOURCE_URL = "https://github.com/deepseek-ai/deepseek-harness.git"
PREPARATION_OWNER = "houmao-dsh-development-v1"
SUPPORTED_VERSION_SPEC = ">=0.2.2rc1"


def _is_supported_dsh_version(raw: object) -> bool:
    """Return whether a version string meets the lower-bounded release/rc floor."""

    if not isinstance(raw, str) or not raw.strip():
        return False
    try:
        parsed = Version(raw.strip())
    except InvalidVersion:
        return False
    if parsed.is_devrelease or (parsed.pre is not None and parsed.pre[0] != "rc"):
        return False
    return SpecifierSet(SUPPORTED_VERSION_SPEC).contains(parsed, prereleases=True)


def _development_output(path: Path, permitted: Path) -> Path:
    """Keep generated development resources in ignored trees or outside the project."""

    path = path.expanduser().resolve()
    if path.is_relative_to(PROJECT) and not path.is_relative_to(permitted):
        raise ValueError(f"Select an output outside the project or under {permitted}")
    if path.is_relative_to(PROJECT):
        ignored = subprocess.run(
            ["git", "check-ignore", "--quiet", "--", str(path)], cwd=PROJECT, check=False
        )
        if ignored.returncode != 0:
            raise ValueError("Generated DSH resources must remain ignored by the project")
    return path


def _run(arguments: list[str], *, cwd: Path | None = None) -> str:
    """Run a preparation command without invoking a shell."""

    return subprocess.run(
        arguments, cwd=cwd, check=True, capture_output=True, text=True, timeout=900
    ).stdout.strip()


def verify_source(source: Path) -> dict[str, str]:
    """Verify the exact reference revision and refuse tracked source modifications."""

    revision = _run(["git", "rev-parse", "HEAD"], cwd=source)
    if revision != SOURCE_REVISION:
        raise ValueError(f"DSH source must be at {SOURCE_REVISION}; existing checkout is unchanged")
    if _run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=source):
        raise ValueError(
            "DSH source contains tracked modifications; existing checkout is unchanged"
        )
    package = json.loads((source / "apps/cli/package.json").read_text())
    if package.get("name") != "@deepseek-ai/dsh" or not isinstance(package.get("version"), str):
        raise ValueError("Pinned source does not contain the expected DSH package")
    return {"revision": revision, "version": package["version"], "path": str(source.resolve())}


def prepare_source(source: Path) -> dict[str, str]:
    """Clone a missing reference checkout, leaving every existing checkout untouched."""

    source = _development_output(source, PROJECT / "extern/orphan")
    if not source.exists():
        source.parent.mkdir(parents=True, exist_ok=True)
        _run(["git", "clone", "--no-checkout", SOURCE_URL, str(source)])
        _run(["git", "checkout", "--detach", SOURCE_REVISION], cwd=source)
    return verify_source(source)


def _sha256(path: Path) -> str:
    """Hash actual executable or package bytes."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _package_root(executable: Path) -> Path:
    """Find the selected executable's own DSH package without searching other installs."""

    for parent in executable.parents:
        metadata = parent / "package.json"
        if metadata.is_file():
            package = json.loads(metadata.read_text())
            if package.get("name") == "@deepseek-ai/dsh":
                return parent
    raise ValueError("Selected executable is not inside an identifiable @deepseek-ai/dsh package")


def inspect_runtime(source: Path, executable: Path) -> dict[str, Any]:
    """Check source/package versions and hash the actual installed DSH code.

    A matching package version does not establish that npm bytes were built from
    the source revision. Native conformance tests must qualify the recorded build.
    """

    reference = verify_source(source)
    executable = executable.expanduser().resolve(strict=True)
    package_root = _package_root(executable)
    package = json.loads((package_root / "package.json").read_text())
    package_version = package.get("version")
    if not _is_supported_dsh_version(package_version):
        raise ValueError(
            f"Installed DSH {package_version} does not satisfy {SUPPORTED_VERSION_SPEC} "
            "(release or rc only; alpha/beta/dev unsupported)"
        )
    with tempfile.TemporaryDirectory(prefix="houmao-dsh-version-") as temporary:
        private = Path(temporary)
        environment = {
            "PATH": os.environ.get("PATH", os.defpath),
            "DSH_HOME": str(private / "home"),
            "DSH_AGENTS_HOME": str(private / "agents"),
        }
        version = subprocess.run(
            [str(executable), "--version"],
            cwd=private,
            env=environment,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout.strip()
    if version != package_version:
        raise ValueError("DSH executable version differs from its package metadata")
    inventory: list[dict[str, str]] = []
    digest = hashlib.sha256()
    for entry in sorted(package_root.parent.iterdir()):
        metadata = entry / "package.json"
        if not metadata.is_file():
            continue
        info = json.loads(metadata.read_text())
        if not str(info.get("name", "")).startswith("@deepseek-ai/"):
            continue
        inventory.append({"name": info["name"], "version": info["version"]})
        files = [metadata, *sorted((entry / "lib").rglob("*.js"))]
        for path in files:
            digest.update(str(path.relative_to(package_root.parent)).encode())
            digest.update(b"\0")
            digest.update(bytes.fromhex(_sha256(path)))
    return {
        "schema_version": 1,
        "source": reference,
        "executable": str(executable),
        "executable_sha256": _sha256(executable),
        "package_version": package["version"],
        "reported_version": version,
        "package_inventory": inventory,
        "dsh_package_code_sha256": digest.hexdigest(),
        "runtime_source_revision": None,
        "provenance": "Published npm package; source commit is not attested by package metadata",
        "qualification": "Build identified; native conformance and provider qualification required",
    }


def prepare_runtime(source: Path, runtime_root: Path, installer: str = "bun") -> dict[str, Any]:
    """Install the exact source package version into a helper-owned development root."""

    if installer not in {"bun", "npm"}:
        raise ValueError("Select bun or npm explicitly as the runtime package installer")
    reference = verify_source(source)
    runtime_root = _development_output(runtime_root, PROJECT / "tmp")
    marker = runtime_root / "houmao-preparation.json"
    expected = {"owner": PREPARATION_OWNER, "source_revision": SOURCE_REVISION}
    if runtime_root.exists() and any(runtime_root.iterdir()):
        if not marker.is_file() or json.loads(marker.read_text()) != expected:
            raise ValueError("Runtime root is not owned by this helper; select a fresh directory")
    runtime_root.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps(expected, indent=2) + "\n")
    package = {
        "name": "houmao-dsh-development-runtime",
        "private": True,
        "dependencies": {"@deepseek-ai/dsh": reference["version"]},
    }
    (runtime_root / "package.json").write_text(json.dumps(package, indent=2) + "\n")
    if installer == "bun":
        _run(["bun", "install", "--cwd", str(runtime_root)])
    else:
        _run(["npm", "install", "--prefix", str(runtime_root), "--no-audit", "--no-fund"])
    receipt = inspect_runtime(source, runtime_root / "node_modules/.bin/dsh")
    lock = runtime_root / ("bun.lock" if installer == "bun" else "package-lock.json")
    receipt["package_lock_sha256"] = _sha256(lock) if lock.is_file() else None
    receipt["installation"] = f"isolated-{installer}-install"
    (runtime_root / "build.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main() -> None:
    """Prepare or inspect development resources and print only non-secret provenance."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=PROJECT / "extern/orphan/deepseek-harness")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("source", help="Clone a missing pinned reference or verify an existing one")
    runtime = commands.add_parser(
        "runtime", help="Install an isolated version-matching npm runtime"
    )
    runtime.add_argument("--root", type=Path, default=PROJECT / "tmp/dsh/runtime")
    runtime.add_argument("--installer", choices=("bun", "npm"), default="bun")
    inspect = commands.add_parser("inspect", help="Verify and identify an installed DSH executable")
    inspect.add_argument("--executable", type=Path, default=Path(shutil.which("dsh") or "dsh"))
    arguments = parser.parse_args()
    try:
        if arguments.command == "source":
            result: dict[str, Any] = prepare_source(arguments.source)
        elif arguments.command == "runtime":
            result = prepare_runtime(arguments.source, arguments.root, arguments.installer)
        else:
            result = inspect_runtime(arguments.source, arguments.executable)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(1, f"DSH preparation failed: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
