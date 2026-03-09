## 1. Wrapper Script Workflow

- [x] 1.1 Add a launch wrapper under `scripts/demo/cao-interactive-full-pipeline-demo/` that delegates through `run_demo.sh` or a shared helper backed by it and starts the session as `alice`.
- [x] 1.2 Add a prompt wrapper under `scripts/demo/cao-interactive-full-pipeline-demo/` that accepts `--prompt <text>` and forwards the prompt to the active interactive session through the same shared shell backend.
- [x] 1.3 Add a stop wrapper under `scripts/demo/cao-interactive-full-pipeline-demo/` that delegates through the shared shell backend to the existing interactive teardown flow.
- [x] 1.4 Ensure the wrapper scripts and lower-level `run_demo.sh` commands share one shell-level source of truth for workspace and environment defaults so the tutorial commands operate on one consistent session state.

## 2. Tutorial and Documentation Refresh

- [x] 2.1 Rewrite `scripts/demo/cao-interactive-full-pipeline-demo/README.md` into the repository's API usage tutorial format with explanatory prose and inline code blocks for launch, inspect, prompt, and stop.
- [x] 2.2 Update the README so the primary walkthrough is `launch alice -> interact manually -> stop`, with `verify` documented only as secondary maintainer tooling for the existing minimum two-turn regression check.
- [x] 2.3 Add an appendix covering key parameters, important input and output files, the underlying implementation files that support debugging or reruns, and the canonicalized persisted identity that corresponds to tutorial agent `alice`.

## 3. Manual Developer Validation

- [x] 3.1 Manually review the wrapper-script workflow, including the fixed `alice` launch path and prompt forwarding behavior, by walking through the tutorial commands as a developer would.
- [x] 3.2 Manually confirm that lower-level commands such as `run_demo.sh inspect` and `run_demo.sh verify` remain coherent as advanced or maintainer-oriented surfaces after the tutorial reshaping.
- [x] 3.3 Use lightweight shell syntax checks only as optional author sanity aids if helpful, and do not add new Pixi tasks or release-gating automation for this demo pack.
