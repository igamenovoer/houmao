#!/usr/bin/env python3
"""Materialize shared loop scaffolds from packaged assets.

Usage examples:

    pixi run python scripts/scaffold.py --profile intention-create --loop-dir /path/to/loop
    pixi run python scripts/scaffold.py --profile intention-init --loop-dir /path/to/loop
    pixi run python scripts/scaffold.py --profile execplan-shell --loop-dir /path/to/loop
    pixi run python scripts/scaffold.py --profile execplan-stepwise-shell --loop-dir /path/to/loop
    pixi run python scripts/scaffold.py --profile execplan-finalize-docs --loop-dir /path/to/loop
    pixi run python scripts/scaffold.py \
        --profile execplan-adr \
        --loop-dir /path/to/loop \
        --adr-index 3 \
        --adr-slug worker-result-evidence-link \
        --adr-title "Worker Result Evidence Link" \
        --stage execplan-specs-contract
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from string import Template


ASSET_ROOT = Path(__file__).resolve().parent.parent / "assets" / "scaffolds"


@dataclass(frozen=True)
class TemplateTarget:
    """Bind one template asset to one output path."""

    m_template_path: Path
    m_output_path: Path


@dataclass(frozen=True)
class ProfileDefinition:
    """Describe directories and template files owned by one scaffold profile."""

    m_directories: tuple[Path, ...]
    m_templates: tuple[TemplateTarget, ...]


COMMON_EXECPLAN_DIRECTORIES = (
    Path("execplan"),
    Path("execplan/specs"),
    Path("execplan/specs/objective"),
    Path("execplan/specs/collab"),
    Path("execplan/specs/comms"),
    Path("execplan/specs/comms/schemas"),
    Path("execplan/specs/comms/renderers"),
    Path("execplan/specs/state"),
    Path("execplan/specs/workspace"),
    Path("execplan/specs/run"),
    Path("execplan/specs/participants"),
    Path("execplan/skills"),
    Path("execplan/agents"),
    Path("execplan/agents/profiles"),
    Path("execplan/agents/notifier-prompts"),
    Path("execplan/harness"),
    Path("execplan/harness/bin"),
    Path("execplan/harness/src"),
    Path("execplan/harness/refs"),
    Path("execplan/harness/schemas"),
    Path("execplan/docs"),
)


COMMON_EXECPLAN_READMES = (
    TemplateTarget(Path("execplan/README.md.tmpl"), Path("execplan/README.md")),
    TemplateTarget(Path("execplan/specs/README.md.tmpl"), Path("execplan/specs/README.md")),
    TemplateTarget(
        Path("execplan/specs/objective/README.md.tmpl"),
        Path("execplan/specs/objective/README.md"),
    ),
    TemplateTarget(
        Path("execplan/specs/collab/README.md.tmpl"),
        Path("execplan/specs/collab/README.md"),
    ),
    TemplateTarget(
        Path("execplan/specs/comms/README.md.tmpl"),
        Path("execplan/specs/comms/README.md"),
    ),
    TemplateTarget(
        Path("execplan/specs/comms/schemas/README.md.tmpl"),
        Path("execplan/specs/comms/schemas/README.md"),
    ),
    TemplateTarget(
        Path("execplan/specs/comms/renderers/README.md.tmpl"),
        Path("execplan/specs/comms/renderers/README.md"),
    ),
    TemplateTarget(
        Path("execplan/specs/state/README.md.tmpl"),
        Path("execplan/specs/state/README.md"),
    ),
    TemplateTarget(
        Path("execplan/specs/workspace/README.md.tmpl"),
        Path("execplan/specs/workspace/README.md"),
    ),
    TemplateTarget(
        Path("execplan/specs/run/README.md.tmpl"),
        Path("execplan/specs/run/README.md"),
    ),
    TemplateTarget(
        Path("execplan/specs/participants/README.md.tmpl"),
        Path("execplan/specs/participants/README.md"),
    ),
    TemplateTarget(Path("execplan/skills/README.md.tmpl"), Path("execplan/skills/README.md")),
    TemplateTarget(Path("execplan/agents/README.md.tmpl"), Path("execplan/agents/README.md")),
    TemplateTarget(
        Path("execplan/agents/profiles/README.md.tmpl"),
        Path("execplan/agents/profiles/README.md"),
    ),
    TemplateTarget(
        Path("execplan/agents/notifier-prompts/README.md.tmpl"),
        Path("execplan/agents/notifier-prompts/README.md"),
    ),
    TemplateTarget(Path("execplan/harness/README.md.tmpl"), Path("execplan/harness/README.md")),
    TemplateTarget(
        Path("execplan/harness/bin/README.md.tmpl"),
        Path("execplan/harness/bin/README.md"),
    ),
    TemplateTarget(
        Path("execplan/harness/src/README.md.tmpl"),
        Path("execplan/harness/src/README.md"),
    ),
    TemplateTarget(
        Path("execplan/harness/refs/README.md.tmpl"),
        Path("execplan/harness/refs/README.md"),
    ),
    TemplateTarget(
        Path("execplan/harness/schemas/README.md.tmpl"),
        Path("execplan/harness/schemas/README.md"),
    ),
    TemplateTarget(Path("execplan/docs/README.md.tmpl"), Path("execplan/docs/README.md")),
)

EXECPLAN_ADRS_README = TemplateTarget(
    Path("execplan/adrs/README.md.tmpl"),
    Path("execplan/adrs/README.md"),
)


PROFILES = {
    "intention-create": ProfileDefinition(
        m_directories=(Path("intention"),),
        m_templates=(
            TemplateTarget(
                m_template_path=Path("intention/README.md.tmpl"),
                m_output_path=Path("intention/README.md"),
            ),
            TemplateTarget(
                m_template_path=Path("intention/loop-overview.md.tmpl"),
                m_output_path=Path("intention/loop-overview.md"),
            ),
        ),
    ),
    "intention-init": ProfileDefinition(
        m_directories=(Path("intention"),),
        m_templates=(
            TemplateTarget(
                m_template_path=Path("intention/README.md.tmpl"),
                m_output_path=Path("intention/README.md"),
            ),
            TemplateTarget(
                m_template_path=Path("intention/loop-overview.md.tmpl"),
                m_output_path=Path("intention/loop-overview.md"),
            ),
            TemplateTarget(
                m_template_path=Path("intention/project-context.md.tmpl"),
                m_output_path=Path("intention/project-context.md"),
            ),
        ),
    ),
    "execplan-shell": ProfileDefinition(
        m_directories=COMMON_EXECPLAN_DIRECTORIES,
        m_templates=(
            TemplateTarget(
                m_template_path=Path("execplan/manifest.toml.tmpl"),
                m_output_path=Path("execplan/manifest.toml"),
            ),
        )
        + COMMON_EXECPLAN_READMES,
    ),
    "execplan-stepwise-shell": ProfileDefinition(
        m_directories=COMMON_EXECPLAN_DIRECTORIES + (Path("execplan/adrs"),),
        m_templates=(
            TemplateTarget(
                m_template_path=Path("execplan/manifest.toml.tmpl"),
                m_output_path=Path("execplan/manifest.toml"),
            ),
        )
        + COMMON_EXECPLAN_READMES
        + (EXECPLAN_ADRS_README,),
    ),
    "execplan-finalize-docs": ProfileDefinition(
        m_directories=(Path("execplan"), Path("execplan/docs")),
        m_templates=(
            TemplateTarget(
                m_template_path=Path("execplan/README.md.tmpl"),
                m_output_path=Path("execplan/README.md"),
            ),
            TemplateTarget(
                m_template_path=Path("execplan/docs/README.md.tmpl"),
                m_output_path=Path("execplan/docs/README.md"),
            ),
            TemplateTarget(
                m_template_path=Path("execplan/docs/artifact-index.md.tmpl"),
                m_output_path=Path("execplan/docs/artifact-index.md"),
            ),
            TemplateTarget(
                m_template_path=Path("execplan/docs/operator-guide.md.tmpl"),
                m_output_path=Path("execplan/docs/operator-guide.md"),
            ),
            TemplateTarget(
                m_template_path=Path("execplan/docs/runtime-model.md.tmpl"),
                m_output_path=Path("execplan/docs/runtime-model.md"),
            ),
            TemplateTarget(
                m_template_path=Path("execplan/docs/validation.md.tmpl"),
                m_output_path=Path("execplan/docs/validation.md"),
            ),
        ),
    ),
    "execplan-adr": ProfileDefinition(
        m_directories=(Path("execplan/adrs"),),
        m_templates=(
            TemplateTarget(
                m_template_path=Path("execplan/adrs/execplan-adr.md.tmpl"),
                m_output_path=Path("__DYNAMIC_EXECPLAN_ADR__"),
            ),
        ),
    ),
}


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        required=True,
        choices=sorted(PROFILES),
        help="Scaffold profile to materialize.",
    )
    parser.add_argument(
        "--loop-dir",
        required=True,
        help="Root loop directory that owns intention/ and execplan/.",
    )
    parser.add_argument(
        "--plan-revision",
        default="0",
        help="Plan revision to record in scaffold-owned starter files.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Rewrite scaffold-owned files instead of preserving existing content.",
    )
    parser.add_argument(
        "--adr-index",
        type=int,
        help="Sequential numeric ADR index for the execplan-adr profile.",
    )
    parser.add_argument(
        "--adr-slug",
        help="Kebab-case ADR slug for the execplan-adr profile.",
    )
    parser.add_argument(
        "--adr-title",
        help="Human-readable ADR title for the execplan-adr profile.",
    )
    parser.add_argument(
        "--stage",
        help="Owning stage name for the execplan-adr profile.",
    )
    return parser


def slugify(value: str) -> str:
    """Normalize freeform text to kebab-case."""

    collapsed = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return collapsed.strip("-") or "loop"


def render_context(args: argparse.Namespace) -> dict[str, str]:
    """Build template-substitution values for the requested profile."""

    loop_dir = Path(args.loop_dir).expanduser()
    loop_dir_name = loop_dir.name or "loop"
    include_execplan_adrs = args.profile == "execplan-stepwise-shell"
    purpose_directories = [
        "specs",
        "skills",
        "agents",
        "harness",
        "docs",
    ]
    if include_execplan_adrs:
        purpose_directories.append("adrs")

    adrs_artifact_block = ""
    if include_execplan_adrs:
        adrs_artifact_block = """
# Generated execplan decision records directory.
[[artifacts]]
id = "adrs"
description = "Generated decision records for accepted execplan-generation choices."
path = "adrs/"
artifact_kind = "dir"
purpose = "accepted execplan-generation decisions"
""".strip()

    adr_index = f"{args.adr_index:04d}" if args.adr_index is not None else "0001"
    adr_slug = slugify(args.adr_slug or "short-decision-slug")
    adr_title = args.adr_title or "Short Decision Title"
    stage = args.stage or "execplan-specs-contract"

    return {
        "adr_file_name": f"{adr_index}-{adr_slug}.md",
        "adr_index": adr_index,
        "adr_slug": adr_slug,
        "adr_title": adr_title,
        "execplan_adrs_artifact_block": adrs_artifact_block,
        "generated_date": datetime.now(timezone.utc).date().isoformat(),
        "include_execplan_adrs": str(include_execplan_adrs).lower(),
        "loop_dir_name": loop_dir_name,
        "loop_slug": slugify(loop_dir_name),
        "plan_revision": str(args.plan_revision),
        "purpose_directories_toml": "["
        + ", ".join(f'"{item}"' for item in purpose_directories)
        + "]",
        "scaffold_profile": args.profile,
        "stage": stage,
    }


def resolve_profile(profile_name: str, context: dict[str, str]) -> ProfileDefinition:
    """Resolve any dynamic paths for a profile before materialization."""

    profile = PROFILES[profile_name]
    if profile_name != "execplan-adr":
        return profile

    targets = []
    for target in profile.m_templates:
        if target.m_output_path == Path("__DYNAMIC_EXECPLAN_ADR__"):
            output_path = Path("execplan/adrs") / context["adr_file_name"]
        else:
            output_path = target.m_output_path
        targets.append(
            TemplateTarget(
                m_template_path=target.m_template_path,
                m_output_path=output_path,
            )
        )

    return ProfileDefinition(
        m_directories=profile.m_directories,
        m_templates=tuple(targets),
    )


def ensure_directories(root: Path, directories: tuple[Path, ...]) -> list[str]:
    """Create directories owned by the selected profile."""

    created = []
    for relative_path in directories:
        absolute_path = root / relative_path
        absolute_path.mkdir(parents=True, exist_ok=True)
        created.append(str(relative_path))
    return created


def render_template(template_path: Path, context: dict[str, str]) -> str:
    """Render one scaffold template."""

    template_text = template_path.read_text(encoding="utf-8")
    return Template(template_text).substitute(context)


def write_template_outputs(
    root: Path,
    definition: ProfileDefinition,
    context: dict[str, str],
    overwrite: bool,
) -> tuple[list[str], list[str]]:
    """Write scaffold-owned files for the selected profile."""

    written = []
    preserved = []
    for template_target in definition.m_templates:
        template_path = ASSET_ROOT / template_target.m_template_path
        output_path = root / template_target.m_output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists() and not overwrite:
            preserved.append(str(template_target.m_output_path))
            continue
        output_path.write_text(render_template(template_path, context), encoding="utf-8")
        written.append(str(template_target.m_output_path))
    return written, preserved


def validate_args(args: argparse.Namespace) -> None:
    """Validate profile-specific CLI requirements."""

    if args.profile != "execplan-adr":
        return
    missing = []
    if args.adr_index is None:
        missing.append("--adr-index")
    if not args.adr_slug:
        missing.append("--adr-slug")
    if not args.adr_title:
        missing.append("--adr-title")
    if not args.stage:
        missing.append("--stage")
    if missing:
        raise ValueError(f"execplan-adr requires: {', '.join(missing)}")


def main() -> int:
    """Run the scaffold generator."""

    parser = build_parser()
    args = parser.parse_args()

    try:
        validate_args(args)
    except ValueError as exc:
        parser.error(str(exc))

    loop_dir = Path(args.loop_dir).expanduser()
    context = render_context(args)
    profile = resolve_profile(args.profile, context)

    created_directories = ensure_directories(loop_dir, profile.m_directories)
    written_files, preserved_files = write_template_outputs(
        root=loop_dir,
        definition=profile,
        context=context,
        overwrite=args.overwrite,
    )

    print(f"profile: {args.profile}")
    print(f"loop_dir: {loop_dir}")
    for relative_path in created_directories:
        print(f"dir: {relative_path}")
    for relative_path in written_files:
        print(f"wrote: {relative_path}")
    for relative_path in preserved_files:
        print(f"preserved: {relative_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
