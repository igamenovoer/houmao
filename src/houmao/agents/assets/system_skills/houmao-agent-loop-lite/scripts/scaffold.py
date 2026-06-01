#!/usr/bin/env python3
"""Materialize lite loop scaffold profiles from packaged templates."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from string import Template


ASSET_ROOT = Path(__file__).resolve().parent.parent / "assets" / "scaffolds"


@dataclass(frozen=True)
class TemplateTarget:
    """Bind a template to an output path."""

    m_template_path: Path
    m_output_path: Path


@dataclass(frozen=True)
class ProfileDefinition:
    """Describe directories and templates for one profile."""

    m_directories: tuple[Path, ...]
    m_templates: tuple[TemplateTarget, ...]


INTENTION_TEMPLATES = (
    TemplateTarget(Path("intention/README.md.tmpl"), Path("intention/README.md")),
    TemplateTarget(Path("intention/loop-overview.md.tmpl"), Path("intention/loop-overview.md")),
)

EXECPLAN_DIRECTORIES = (
    Path("execplan"),
    Path("execplan/specs"),
    Path("execplan/specs/templates"),
    Path("execplan/specs/state"),
    Path("execplan/skills"),
    Path("execplan/agents"),
)

EXECPLAN_TEMPLATES = (
    TemplateTarget(Path("execplan/README.md.tmpl"), Path("execplan/README.md")),
    TemplateTarget(Path("execplan/manifest.md.tmpl"), Path("execplan/manifest.md")),
    TemplateTarget(Path("execplan/specs/README.md.tmpl"), Path("execplan/specs/README.md")),
    TemplateTarget(Path("execplan/specs/objective.md.tmpl"), Path("execplan/specs/objective.md")),
    TemplateTarget(
        Path("execplan/specs/organization.md.tmpl"),
        Path("execplan/specs/organization.md"),
    ),
    TemplateTarget(Path("execplan/specs/process.md.tmpl"), Path("execplan/specs/process.md")),
    TemplateTarget(
        Path("execplan/specs/communication.md.tmpl"),
        Path("execplan/specs/communication.md"),
    ),
    TemplateTarget(
        Path("execplan/specs/templates/task-request.md.tmpl"),
        Path("execplan/specs/templates/task-request.md"),
    ),
    TemplateTarget(
        Path("execplan/specs/state/README.md.tmpl"),
        Path("execplan/specs/state/README.md"),
    ),
    TemplateTarget(
        Path("execplan/specs/state/schema.sql.tmpl"),
        Path("execplan/specs/state/schema.sql"),
    ),
    TemplateTarget(Path("execplan/skills/README.md.tmpl"), Path("execplan/skills/README.md")),
    TemplateTarget(Path("execplan/agents/README.md.tmpl"), Path("execplan/agents/README.md")),
    TemplateTarget(Path("execplan/agents/bindings.md.tmpl"), Path("execplan/agents/bindings.md")),
)

PROFILES = {
    "intention-create": ProfileDefinition(
        m_directories=(Path("intention"),),
        m_templates=INTENTION_TEMPLATES,
    ),
    "intention-init": ProfileDefinition(
        m_directories=(Path("intention"),),
        m_templates=INTENTION_TEMPLATES
        + (TemplateTarget(Path("intention/project-context.md.tmpl"), Path("intention/project-context.md")),),
    ),
    "execplan-shell": ProfileDefinition(
        m_directories=EXECPLAN_DIRECTORIES,
        m_templates=EXECPLAN_TEMPLATES,
    ),
}


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, choices=sorted(PROFILES))
    parser.add_argument("--loop-dir", required=True)
    parser.add_argument("--plan-revision", default="0")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files.")
    return parser


def render_template(template_path: Path, values: dict[str, str]) -> str:
    """Render one scaffold template."""

    template = Template(template_path.read_text(encoding="utf-8"))
    return template.safe_substitute(values)


def materialize(profile: ProfileDefinition, loop_dir: Path, values: dict[str, str], force: bool) -> tuple[list[Path], list[Path]]:
    """Create directories and files for one scaffold profile."""

    created: list[Path] = []
    skipped: list[Path] = []
    for directory in profile.m_directories:
        path = loop_dir / directory
        path.mkdir(parents=True, exist_ok=True)
    for target in profile.m_templates:
        output_path = loop_dir / target.m_output_path
        if output_path.exists() and not force:
            skipped.append(output_path)
            continue
        output_path.parent.mkdir(parents=True, exist_ok=True)
        rendered = render_template(ASSET_ROOT / target.m_template_path, values)
        output_path.write_text(rendered, encoding="utf-8")
        created.append(output_path)
    return created, skipped


def main(argv: list[str] | None = None) -> int:
    """Run the scaffold command."""

    args = build_parser().parse_args(argv)
    loop_dir = Path(args.loop_dir).resolve()
    values = {
        "loop_dir_name": loop_dir.name,
        "plan_revision": args.plan_revision,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    created, skipped = materialize(PROFILES[args.profile], loop_dir, values, args.force)
    for path in created:
        print(f"created {path}")
    for path in skipped:
        print(f"skipped existing {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
