#!/usr/bin/env python3
"""Validate pack-local preflight requirements for the unattended autotest case."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from houmao.agents.brain_builder import load_brain_recipe
from houmao.demo.mail_ping_pong_gateway_demo_pack.models import (
    load_demo_parameters,
    resolve_repo_relative_path,
)


def _existing_dir(path: Path, *, description: str) -> None:
    if not path.is_dir():
        raise SystemExit(f"missing {description}: {path}")


def _existing_file(path: Path, *, description: str) -> None:
    if not path.is_file():
        raise SystemExit(f"missing {description}: {path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--parameters", required=True)
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    parameters_path = Path(args.parameters).resolve()
    _existing_file(parameters_path, description="demo parameters file")

    parameters = load_demo_parameters(parameters_path)
    agent_def_root = os.environ.get("AGENT_DEF_DIR")
    if agent_def_root and agent_def_root.strip():
        agent_def_dir = resolve_repo_relative_path(agent_def_root, repo_root=repo_root)
    else:
        agent_def_dir = resolve_repo_relative_path(parameters.agent_def_dir, repo_root=repo_root)
    _existing_dir(agent_def_dir, description="agent definition root")

    project_fixture = resolve_repo_relative_path(parameters.project_fixture, repo_root=repo_root)
    _existing_dir(project_fixture, description="dummy project fixture")

    participants = {
        "initiator": parameters.initiator,
        "responder": parameters.responder,
    }
    for role, participant in participants.items():
        recipe_path = resolve_repo_relative_path(participant.brain_recipe_path, repo_root=repo_root)
        _existing_file(recipe_path, description=f"{role} recipe")
        recipe = load_brain_recipe(recipe_path)
        config_dir = agent_def_dir / "brains" / "cli-configs" / recipe.tool / recipe.config_profile
        creds_dir = agent_def_dir / "brains" / "api-creds" / recipe.tool / recipe.credential_profile
        _existing_dir(config_dir, description=f"{role} config profile")
        _existing_dir(creds_dir, description=f"{role} credential profile")

    print("preflight ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
