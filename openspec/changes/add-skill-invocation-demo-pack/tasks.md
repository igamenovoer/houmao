## 1. Probe skill fixtures

- [x] 1.1 Create a tracked reusable probe skill under `tests/fixtures/agents/brains/skills/` with a stable trigger contract and helper assets for writing a deterministic marker file in the launched dummy-project workdir
- [x] 1.2 Add lightweight skill-invocation demo role assets under `tests/fixtures/agents/roles/` that bias the agent toward the narrow probe action instead of repo-scale exploration
- [x] 1.3 Add `claude/skill-invocation-demo-default.yaml`, `codex/skill-invocation-demo-default.yaml`, `skill-invocation-demo-claude.yaml`, and `skill-invocation-demo-codex.yaml` so recipes own the probe skill/config/credential inputs and blueprints bind those recipes to the lightweight demo role
- [x] 1.4 Update fixture documentation so maintainers know when to use the probe-skill fixture family instead of mailbox-demo or heavyweight repo-scale fixtures

## 2. Demo pack runner

- [x] 2.1 Scaffold `scripts/demo/skill-invocation-demo-pack/` with the standard demo-pack structure (`README.md`, `run_demo.sh`, `inputs/`, `scripts/`, `expected_report/`)
- [x] 2.2 Implement a shared command surface in `run_demo.sh` that supports `auto|start|inspect|prompt|verify|stop` for `--tool claude|codex`
- [x] 2.3 Implement demo-owned output-root setup that provisions a copied dummy project plus persisted control/runtime state so stepwise commands reuse one selected demo root
- [x] 2.4 Start the selected live session from the tracked skill-invocation demo definition on `shadow_only` and persist the metadata needed for later inspect, verify, and stop commands
- [x] 2.5 Implement CAO preflight, loopback-ownership handling, and `SKIP:` behavior for missing prerequisites or unsupported external CAO ownership
- [x] 2.6 Implement the trigger-prompt step so the operator-facing prompt uses trigger wording only and does not mention the skill name or install path
- [x] 2.7 Implement an inspect step that reports the persisted session/watch coordinates needed to attach or debug a slow live run

## 3. Probe verification and reports

- [x] 3.1 Implement pack helpers that locate the expected probe marker file and validate its marker schema/content for the selected run
- [x] 3.2 Implement `scripts/verify_report.py` and any sanitize/report helpers needed to build a structured, sanitized verification report
- [x] 3.3 Add `expected_report/report.json` based on sanitized content for the tracked demo contract
- [x] 3.4 Add automated coverage for the probe marker/report verification path so the pack's core success boundary is testable without requiring a live credentialed run

## 4. Operator documentation

- [x] 4.1 Write `scripts/demo/skill-invocation-demo-pack/README.md` covering prerequisites, selected tool lane, `auto` plus stepwise workflow, loopback-CAO ownership expectations, inspect guidance, verification, and snapshot refresh
- [x] 4.2 Document the reusable probe-skill contract and how future demos/tests can reuse it instead of inventing one-off dummy skills
