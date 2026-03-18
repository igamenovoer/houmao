## 1. Probe skill fixtures

- [ ] 1.1 Create a tracked reusable probe skill under `tests/fixtures/agents/brains/skills/` with a stable trigger contract and helper assets for writing a deterministic marker file in the launched dummy-project workdir
- [ ] 1.2 Add lightweight skill-invocation demo role assets under `tests/fixtures/agents/roles/` that bias the agent toward the narrow probe action instead of repo-scale exploration
- [ ] 1.3 Add Claude and Codex brain recipes/blueprints that include the probe skill and lightweight demo role
- [ ] 1.4 Update fixture documentation so maintainers know when to use the probe-skill fixture family instead of mailbox-demo or heavyweight repo-scale fixtures

## 2. Demo pack runner

- [ ] 2.1 Scaffold `scripts/demo/skill-invocation-demo-pack/` with the standard demo-pack structure (`README.md`, `run_demo.sh`, `inputs/`, `scripts/`, `expected_report/`)
- [ ] 2.2 Implement a shared command surface in `run_demo.sh` that supports stepwise interactive flow for `--tool claude|codex` including start, inspect, prompt, verify, and stop
- [ ] 2.3 Implement demo-owned output-root setup that copies the tracked dummy project into the run-local workdir and initializes it as a fresh git-backed workspace
- [ ] 2.4 Start the selected live session from the tracked skill-invocation demo definition and persist the metadata needed for later inspect, verify, and stop commands
- [ ] 2.5 Implement the trigger-prompt step so the operator-facing prompt uses trigger wording only and does not mention the skill name or install path

## 3. Probe verification and reports

- [ ] 3.1 Implement pack helpers that locate the expected probe marker file and validate its marker schema/content for the selected run
- [ ] 3.2 Implement `scripts/verify_report.py` and any sanitize/report helpers needed to build a structured, sanitized verification report
- [ ] 3.3 Add `expected_report/report.json` based on sanitized content for the tracked demo contract
- [ ] 3.4 Add automated coverage for the probe marker/report verification path so the pack's core success boundary is testable without requiring a live credentialed run

## 4. Operator documentation

- [ ] 4.1 Write `scripts/demo/skill-invocation-demo-pack/README.md` covering prerequisites, selected tool lane, stepwise workflow, inspect guidance, verification, and snapshot refresh
- [ ] 4.2 Document the reusable probe-skill contract and how future demos/tests can reuse it instead of inventing one-off dummy skills
