#!/usr/bin/env python3
"""
Deploy the bundled LLM Wiki web viewer to a user-selected directory.

The helper copies source from this skill's viewer/ directory, installs and
builds dependencies with npm or bun, writes local Git exclusions, and can
launch the viewer against an existing LLM Wiki root.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


DEFAULT_PORT = 8080
DEFAULT_HOST = "127.0.0.1"
METADATA_FILE = ".llm-wiki-viewer.json"
LOG_FILE = ".llm-wiki-viewer.log"
MANAGED_DIRS = ("audit-shared", "web")
PACKAGE_EXCLUDES = (
    "node_modules",
    "dist",
    "*.tsbuildinfo",
    "package-lock.json",
    "bun.lock",
    "bun.lockb",
)
INSTALL_GITIGNORE_LINES = (
    "node_modules/",
    "dist/",
    "*.tsbuildinfo",
    "package-lock.json",
    "bun.lock",
    "bun.lockb",
    LOG_FILE,
)


class DeployError(RuntimeError):
    """Raised for expected deployment failures with actionable messages."""


@dataclass(frozen=True)
class Toolchain:
    manager: str
    node: str | None
    npm: str | None
    bun: str | None


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        skill_root = Path(__file__).resolve().parents[1]
        source_root = skill_root / "viewer"
        install_dir = Path(args.install_dir).expanduser().resolve()
        wiki_root = resolve_wiki_root(args.wiki, args.no_input)

        validate_source_tree(source_root)
        validate_wiki_root(wiki_root)
        if args.launch_mode != "no-launch":
            ensure_port_available(args.host, args.port)

        toolchain = select_toolchain(args.package_manager)
        if not args.skip_install or args.launch_mode != "no-launch":
            require_toolchain(toolchain)

        print(f"Installing viewer into: {install_dir}")
        copy_viewer_source(source_root, install_dir, force=args.force)
        write_install_gitignore(install_dir)
        write_git_info_exclude(install_dir)

        launch_command = build_launch_command(
            toolchain.manager,
            wiki_root,
            args.port,
            args.host,
            args.author,
        )
        write_metadata(
            install_dir,
            wiki_root=wiki_root,
            port=args.port,
            host=args.host,
            author=args.author,
            package_manager=toolchain.manager,
            launch_mode=args.launch_mode,
            launch_command=launch_command,
            skill_root=skill_root,
        )

        if args.skip_install:
            print("Skipping dependency installation and build (--skip-install).")
        else:
            install_and_build(install_dir, toolchain.manager)

        if args.launch_mode == "no-launch":
            print("Viewer prepared but not launched (--launch-mode no-launch).")
            print_summary(install_dir, wiki_root, args.host, args.port, launch_command)
            return 0

        if args.launch_mode == "foreground":
            print_summary(install_dir, wiki_root, args.host, args.port, launch_command)
            print("Starting viewer in the foreground. Stop it with Ctrl-C.")
            run_foreground(install_dir / "web", launch_command)
            return 0

        pid, log_path = run_background(install_dir / "web", launch_command)
        update_background_metadata(install_dir, pid, log_path)
        wait_for_server(args.host, args.port, pid, log_path)
        print_summary(install_dir, wiki_root, args.host, args.port, launch_command)
        print(f"Background PID: {pid}")
        print(f"Stop command: kill -TERM -{pid}")
        print(f"Log file: {log_path}")
        return 0
    except DeployError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--install-dir", required=True, help="Directory to install the viewer into."
    )
    parser.add_argument("--wiki", help="Existing LLM Wiki root. Prompted or inferred when omitted.")
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help=f"Viewer port. Default: {DEFAULT_PORT}."
    )
    parser.add_argument(
        "--host", default=DEFAULT_HOST, help=f"Host to bind. Default: {DEFAULT_HOST}."
    )
    parser.add_argument(
        "--author", help="Author name passed to the viewer for audit feedback files."
    )
    parser.add_argument(
        "--package-manager",
        choices=("auto", "npm", "bun"),
        default="auto",
        help="Package manager to use. Default: auto.",
    )
    parser.add_argument(
        "--launch-mode",
        choices=("background", "foreground", "no-launch"),
        default="background",
        help="How to start the viewer after build. Default: background.",
    )
    parser.add_argument(
        "--skip-install", action="store_true", help="Copy source but skip install/build commands."
    )
    parser.add_argument(
        "--force", action="store_true", help="Overwrite existing unmanaged viewer subdirectories."
    )
    parser.add_argument("--no-input", action="store_true", help="Do not prompt for missing values.")
    args = parser.parse_args(argv)
    if args.port < 1 or args.port > 65535:
        raise DeployError("--port must be between 1 and 65535")
    return args


def resolve_wiki_root(value: str | None, no_input: bool) -> Path:
    if value:
        return Path(value).expanduser().resolve()

    candidates = infer_wiki_roots(Path.cwd())
    if len(candidates) == 1:
        print(f"Inferred wiki root: {candidates[0]}")
        return candidates[0]

    if no_input or not sys.stdin.isatty():
        if candidates:
            joined = "\n  ".join(str(p) for p in candidates)
            raise DeployError(f"--wiki is required; multiple candidates found:\n  {joined}")
        raise DeployError("--wiki is required; no LLM Wiki root could be inferred")

    prompt = "Wiki root path (directory containing wiki/index.md and audit/): "
    entered = input(prompt).strip()
    if not entered:
        raise DeployError("wiki root is required")
    return Path(entered).expanduser().resolve()


def infer_wiki_roots(start: Path) -> list[Path]:
    skip = {".git", ".codex", ".claude", ".gemini", "node_modules", "extern"}
    found: list[Path] = []
    for root, dirs, files in os.walk(start):
        rel_depth = len(Path(root).relative_to(start).parts)
        if rel_depth > 4:
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if d not in skip]
        current = Path(root)
        if current.name == "wiki" and "index.md" in files:
            candidate = current.parent.resolve()
            if (candidate / "audit").is_dir():
                found.append(candidate)
    return sorted(set(found))


def validate_source_tree(source_root: Path) -> None:
    required = [
        source_root / "audit-shared" / "package.json",
        source_root / "audit-shared" / "tsconfig.json",
        source_root / "audit-shared" / "src",
        source_root / "web" / "package.json",
        source_root / "web" / "tsconfig.json",
        source_root / "web" / "build-client.mjs",
        source_root / "web" / "client",
        source_root / "web" / "server",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise DeployError("packaged viewer source is incomplete:\n  " + "\n  ".join(missing))


def validate_wiki_root(wiki_root: Path) -> None:
    if not wiki_root.is_dir():
        raise DeployError(f"wiki root is not a directory: {wiki_root}")
    required = [wiki_root / "wiki" / "index.md", wiki_root / "audit"]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise DeployError(
            "wiki root is missing required LLM Wiki paths:\n  " + "\n  ".join(missing)
        )


def ensure_port_available(host: str, port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError as exc:
            raise DeployError(f"port {host}:{port} is not available: {exc}") from exc


def select_toolchain(preference: str) -> Toolchain:
    node = shutil.which("node")
    npm = shutil.which("npm")
    bun = shutil.which("bun")

    if preference == "npm":
        manager = "npm"
    elif preference == "bun":
        manager = "bun"
    elif node and npm:
        manager = "npm"
    elif bun:
        manager = "bun"
    else:
        manager = "npm"

    return Toolchain(manager=manager, node=node, npm=npm, bun=bun)


def require_toolchain(toolchain: Toolchain) -> None:
    if toolchain.manager == "npm":
        missing = []
        if not toolchain.node:
            missing.append("node")
        if not toolchain.npm:
            missing.append("npm")
        if missing:
            raise DeployError(
                "npm deployment requires missing tools: "
                + ", ".join(missing)
                + ". Install Node.js with npm, or rerun with --package-manager bun if bun is available."
            )
    elif toolchain.manager == "bun":
        if not toolchain.bun:
            raise DeployError("bun deployment requires missing tool: bun")
    else:
        raise DeployError(f"unsupported package manager: {toolchain.manager}")


def copy_viewer_source(source_root: Path, install_dir: Path, force: bool) -> None:
    install_dir.mkdir(parents=True, exist_ok=True)
    metadata_exists = (install_dir / METADATA_FILE).exists()
    unmanaged = [
        install_dir / name
        for name in MANAGED_DIRS
        if (install_dir / name).exists() and not metadata_exists and not force
    ]
    if unmanaged:
        raise DeployError(
            "installation directory contains existing unmanaged viewer paths:\n  "
            + "\n  ".join(str(p) for p in unmanaged)
            + "\nRerun with --force only if these paths can be overwritten."
        )

    ignore = shutil.ignore_patterns(*PACKAGE_EXCLUDES)
    for name in MANAGED_DIRS:
        src = source_root / name
        dst = install_dir / name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, ignore=ignore)


def write_install_gitignore(install_dir: Path) -> None:
    repo = git_repo_for(install_dir)
    gitignore = install_dir / ".gitignore"
    if repo and gitignore.exists() and is_tracked(repo, gitignore):
        print(f"Skipping tracked .gitignore: {gitignore}")
        return

    block = [
        "# llm-wiki viewer generated files",
        *INSTALL_GITIGNORE_LINES,
    ]
    append_unique_lines(gitignore, block)


def write_git_info_exclude(install_dir: Path) -> None:
    repo = git_repo_for(install_dir)
    if not repo:
        return
    git_path = run_git(repo, "rev-parse", "--git-path", "info/exclude")
    if not git_path:
        return
    exclude_path = (
        (repo / git_path).resolve() if not Path(git_path).is_absolute() else Path(git_path)
    )
    rel = install_dir.relative_to(repo).as_posix()
    if rel == ".":
        lines = [
            "# llm-wiki viewer deployed at repository root",
            "audit-shared/",
            "web/",
            METADATA_FILE,
            LOG_FILE,
        ]
    else:
        lines = [
            "# llm-wiki viewer install directory",
            rel.rstrip("/") + "/",
        ]
    append_unique_lines(exclude_path, lines)


def git_repo_for(path: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()).resolve()


def run_git(repo: Path, *args: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def is_tracked(repo: Path, path: Path) -> bool:
    rel = path.resolve().relative_to(repo).as_posix()
    result = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "--error-unmatch", rel],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def append_unique_lines(path: Path, lines: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    updated = existing[:]
    changed = False
    for line in lines:
        if line not in updated:
            updated.append(line)
            changed = True
    if changed:
        path.write_text("\n".join(updated).rstrip() + "\n", encoding="utf-8")


def build_launch_command(
    manager: str,
    wiki_root: Path,
    port: int,
    host: str,
    author: str | None,
) -> list[str]:
    if manager == "npm":
        command = ["npm", "start", "--"]
    else:
        command = ["bun", "run", "start", "--"]
    command.extend(["--wiki", str(wiki_root), "--port", str(port), "--host", host])
    if author:
        command.extend(["--author", author])
    return command


def write_metadata(
    install_dir: Path,
    *,
    wiki_root: Path,
    port: int,
    host: str,
    author: str | None,
    package_manager: str,
    launch_mode: str,
    launch_command: list[str],
    skill_root: Path,
) -> None:
    metadata = {
        "managed_by": "houmao-utils-llm-wiki",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "skill_root": str(skill_root),
        "wiki_root": str(wiki_root),
        "port": port,
        "host": host,
        "author": author,
        "package_manager": package_manager,
        "launch_mode": launch_mode,
        "launch_command": launch_command,
    }
    (install_dir / METADATA_FILE).write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )


def update_background_metadata(install_dir: Path, pid: int, log_path: Path) -> None:
    metadata_path = install_dir / METADATA_FILE
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["background_pid"] = pid
    metadata["background_pgid"] = pid
    metadata["log_path"] = str(log_path)
    metadata["stop_command"] = f"kill -TERM -{pid}"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def install_and_build(install_dir: Path, manager: str) -> None:
    audit_shared = install_dir / "audit-shared"
    web = install_dir / "web"
    if manager == "npm":
        commands = [
            (audit_shared, ["npm", "install", "--no-package-lock"]),
            (audit_shared, ["npm", "run", "build"]),
            (web, ["npm", "install", "--no-package-lock"]),
            (web, ["npm", "run", "build"]),
        ]
    else:
        commands = [
            (audit_shared, ["bun", "install"]),
            (audit_shared, ["bun", "run", "build"]),
            (web, ["bun", "install"]),
            (web, ["bun", "run", "build"]),
        ]

    for cwd, command in commands:
        run_checked(command, cwd)


def run_checked(command: list[str], cwd: Path) -> None:
    print(f"$ {format_command(command)}  # cwd={cwd}")
    result = subprocess.run(command, cwd=str(cwd), check=False)
    if result.returncode != 0:
        raise DeployError(
            f"command failed with exit code {result.returncode}: {format_command(command)}"
        )


def run_foreground(cwd: Path, command: list[str]) -> None:
    result = subprocess.run(command, cwd=str(cwd), check=False)
    if result.returncode != 0:
        raise DeployError(f"viewer exited with code {result.returncode}: {format_command(command)}")


def run_background(cwd: Path, command: list[str]) -> tuple[int, Path]:
    log_path = cwd.parent / LOG_FILE
    log_file = log_path.open("ab")
    try:
        proc = subprocess.Popen(
            command,
            cwd=str(cwd),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    finally:
        log_file.close()
    return proc.pid, log_path


def wait_for_server(host: str, port: int, pid: int, log_path: Path) -> None:
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        if process_exited(pid):
            raise DeployError(f"viewer process exited early. Last log lines:\n{tail(log_path)}")
        if can_connect(host, port):
            return
        time.sleep(0.5)
    raise DeployError(
        f"viewer did not start on http://{host}:{port}. Last log lines:\n{tail(log_path)}"
    )


def process_exited(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


def can_connect(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((host, port)) == 0


def tail(path: Path, max_lines: int = 20) -> str:
    if not path.exists():
        return "(log file does not exist)"
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-max_lines:]) or "(log file is empty)"


def print_summary(
    install_dir: Path,
    wiki_root: Path,
    host: str,
    port: int,
    launch_command: list[str],
) -> None:
    print("")
    print("LLM Wiki viewer deployment")
    print(f"  URL:          http://{host}:{port}")
    print(f"  install dir:  {install_dir}")
    print(f"  wiki root:    {wiki_root}")
    print(f"  launch cmd:   cd {install_dir / 'web'} && {format_command(launch_command)}")


def format_command(command: list[str]) -> str:
    return " ".join(shell_quote(part) for part in command)


def shell_quote(value: str) -> str:
    if not value:
        return "''"
    safe = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@%_+=:,./-")
    if all(ch in safe for ch in value):
        return value
    return "'" + value.replace("'", "'\"'\"'") + "'"


if __name__ == "__main__":
    raise SystemExit(main())
