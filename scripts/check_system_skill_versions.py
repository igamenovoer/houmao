#!/usr/bin/env python3
"""Check public system-skill source versions against the project release."""

from __future__ import annotations

import argparse
from pathlib import Path

from houmao.agents.system_skill_version import check_system_skill_source_versions


def main() -> int:
    """Run the read-only source synchronization check."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root containing pyproject.toml (default: current checkout).",
    )
    args = parser.parse_args()
    try:
        result = check_system_skill_source_versions(project_root=args.project_root)
    except RuntimeError as exc:
        print(f"system-skill version check failed: {exc}")
        return 1
    if result.healthy:
        print(
            f"system-skill versions match Houmao {result.project_version}: "
            f"{', '.join(result.checked_skill_names)}"
        )
        return 0
    print(f"system-skill version check expected Houmao {result.project_version}:")
    for issue in result.issues:
        observed = issue.observed_version if issue.observed_version is not None else "unavailable"
        print(
            f"  - {issue.skill_name}: observed={observed}; expected={issue.expected_version}; "
            f"{issue.problem} ({issue.path})"
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
