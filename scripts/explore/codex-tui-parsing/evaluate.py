#!/usr/bin/env python3
"""Evaluate iteration-1 assertion contracts over frozen run artifacts.

Emulates promptfoo's Python assertion calling convention
(``get_assert(output, context)``) so the same scripts under ``asserts/`` can
later run unmodified under promptfoo itself. Gate results (``pass: false``)
fail the evaluation; measure results always pass and report scores.

Usage:
    pixi run python scripts/explore/kimi-code-tui-parsing/evaluate.py \
        --spec <session YAML> --run-root <run root> \
        --replay-tags baseline candidate-2.1.x
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from campaign_lib.spec import load_session_spec

ASSERTS_DIR = Path(__file__).resolve().parent / "asserts"
REPO_ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    """Evaluate all gate and measure assertions for one recorded run."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument(
        "--replay-tags", nargs="+", default=["baseline-fallback", "baseline-0.144.x"]
    )
    args = parser.parse_args()

    run_root = args.run_root.resolve()
    recording_root = run_root / "capture" / "recording"
    spec = load_session_spec(args.spec)

    replay: dict[str, dict[str, str]] = {}
    for tag in args.replay_tags:
        state_path = recording_root / f"state_observed_{tag}.ndjson"
        parser_path = recording_root / f"parser_observed_{tag}.ndjson"
        if state_path.is_file():
            replay[tag] = {
                "state_observed_path": str(state_path),
                "parser_observed_path": str(parser_path),
            }

    base_output = {
        "run_root": str(run_root),
        "recording_root": str(recording_root),
        "labels_path": str(run_root / "labels" / "labels.json"),
        "labels_manifest_path": str(run_root / "labels" / "labels-manifest.json"),
        "replay": replay,
    }

    evaluations: list[dict[str, Any]] = []
    for case in spec.cases:
        case_output = {**base_output, "case_id": case.case_id}
        assertions = list(spec.default_asserts) + list(case.asserts)
        for assertion in assertions:
            value = str(assertion.get("value") or "")
            if not value.startswith("file://"):
                continue
            script_name = Path(value).name
            configs: list[dict[str, Any]] = [dict(assertion.get("config") or {})]
            if script_name == "field_agreement.py":
                configs = [{**configs[0], "replay_tag": tag} for tag in replay]
            for config in configs:
                outcome = _run_assert(script_name, case_output, case, config)
                evaluations.append(
                    {
                        "case_id": case.case_id,
                        "assert": script_name,
                        "config": config,
                        "result": outcome,
                    }
                )

    out_dir = run_root / "comparison"
    out_dir.mkdir(parents=True, exist_ok=True)
    gates_failed = [
        item
        for item in evaluations
        if not item["result"].get("pass") and item["assert"] != "coverage_spans.py"
    ]
    coverage_failed = [
        item
        for item in evaluations
        if not item["result"].get("pass") and item["assert"] == "coverage_spans.py"
    ]
    payload = {
        "run_root": str(run_root),
        "spec": str(spec.path),
        "replay_tags": list(replay),
        "gates_failed": len(gates_failed),
        "coverage_failed": len(coverage_failed),
        "evaluations": evaluations,
    }
    (out_dir / "eval-results.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out_dir / "eval-results.md").write_text(_render_markdown(payload), encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items() if k != "evaluations"}, indent=2))
    return 1 if gates_failed else 0


def _run_assert(
    script_name: str, output: dict[str, Any], case, config: dict[str, Any]
) -> dict[str, Any]:
    """Load one assert script and invoke its promptfoo-contract entrypoint."""

    script_path = ASSERTS_DIR / script_name
    module_name = f"campaign_assert_{script_name.replace('.', '_')}"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        return {"pass": False, "reason": f"cannot load {script_name}"}
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
        context = SimpleNamespace(
            vars={"case_id": case.case_id, "ops": list(case.ops)}, assert_config=config
        )
        return module.get_assert(output, context)
    except Exception as exc:  # noqa: BLE001 - assertion crashes are gate failures
        return {"pass": False, "reason": f"{script_name} crashed: {exc!r}"}


def _render_markdown(payload: dict[str, Any]) -> str:
    """Render one human-readable evaluation summary."""

    lines = [
        f"# Evaluation: {payload['run_root']}",
        "",
        f"- spec: `{payload['spec']}`",
        f"- replay tags: {', '.join(payload['replay_tags']) or 'none'}",
        f"- gates failed: {payload['gates_failed']}",
        f"- coverage gates failed: {payload['coverage_failed']}",
        "",
        "| case | assert | pass | reason |",
        "| --- | --- | --- | --- |",
    ]
    for item in payload["evaluations"]:
        result = item["result"]
        lines.append(
            "| {case} | {name} | {ok} | {reason} |".format(
                case=item["case_id"],
                name=item["assert"],
                ok="yes" if result.get("pass") else "NO",
                reason=str(result.get("reason", ""))[:140].replace("|", "\\|"),
            )
        )
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
