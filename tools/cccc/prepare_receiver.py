"""Prepare a reproducible patched CCCC source tree outside the project checkout."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any


PROJECT = Path(__file__).resolve().parents[2]
DEPENDENCY = PROJECT / "extern/tracked/cccc-receiver"


def _git(source: Path, *arguments: str) -> str:
    """Run Git with structured arguments, returning bounded setup diagnostics."""

    result = subprocess.run(
        ["git", "-C", str(source), *arguments], capture_output=True, text=True, check=False
    )
    if result.returncode:
        raise RuntimeError("CCCC source preparation failed: " + result.stderr[-1000:])
    return result.stdout


def prepare(output: Path, *, manifest_path: Path | None = None) -> dict[str, Any]:
    """Materialize a pinned source and tracked patches without changing the reference."""

    manifest_path = manifest_path or DEPENDENCY / "upstream.json"
    manifest = json.loads(manifest_path.read_text())
    revision = manifest["revision"]
    protocol_version = manifest.get("protocol_version")
    if not isinstance(revision, str) or not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("The receiver dependency requires a complete upstream commit")
    output = output.expanduser().resolve()
    if output.is_relative_to(PROJECT):
        raise ValueError("Prepared source must be outside the project checkout")
    patches = [(manifest_path.parent / item).resolve() for item in manifest["patches"]]
    if any(not patch.is_relative_to(manifest_path.parent.resolve()) for patch in patches):
        raise ValueError("Patch paths must remain within the tracked dependency")
    digest = hashlib.sha256()
    digest.update(revision.encode())
    for patch in patches:
        digest.update(patch.read_bytes())
    selection = digest.hexdigest()
    receipt = output.parent / (output.name + ".receipt.json")
    if output.exists():
        if not receipt.exists():
            raise ValueError(
                "Existing source lacks a preparation receipt; select a fresh directory"
            )
        previous: dict[str, Any] = json.loads(receipt.read_text())
        actual = hashlib.sha256(_git(output, "diff", "--binary", "HEAD").encode()).hexdigest()
        if (
            previous.get("selection") != selection
            or previous.get("protocol_version") != protocol_version
            or previous.get("diff_sha256") != actual
            or _git(output, "rev-parse", "HEAD").strip() != revision
            or _git(output, "ls-files", "--others", "--exclude-standard").strip()
        ):
            raise ValueError("Source or patch selection changed; select a fresh output directory")
        return previous
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    reference = PROJECT / "extern/orphan/cccc"
    local_revision = (
        reference.is_dir()
        and subprocess.run(
            ["git", "-C", str(reference), "cat-file", "-e", revision + "^{commit}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )
    repository = str(reference) if local_revision else manifest["repository"]
    result = subprocess.run(
        ["git", "clone", "--no-checkout", repository, str(output)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("Cannot prepare the pinned CCCC source")
    _git(output, "checkout", "--detach", revision)
    for patch in patches:
        _git(output, "apply", "--check", "--index", str(patch))
        _git(output, "apply", "--index", str(patch))
    report = {
        "source": str(output),
        "revision": revision,
        "protocol_version": protocol_version,
        "selection": selection,
        "patches": manifest["patches"],
        "diff_sha256": hashlib.sha256(
            _git(output, "diff", "--binary", "HEAD").encode()
        ).hexdigest(),
    }
    receipt.write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    """Prepare the explicitly selected independent build source."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path.home() / ".local/share/houmao-cccc/source-receiver-v2"
    )
    arguments = parser.parse_args()
    try:
        print(json.dumps(prepare(arguments.output)))
    except (OSError, ValueError, KeyError, RuntimeError):
        parser.exit(1, "Receiver source setup failed; verify the pinned manifest and output tree\n")


if __name__ == "__main__":
    main()
