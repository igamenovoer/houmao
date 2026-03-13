## 1. Canonicalize Active CAO References

- [ ] 1.1 Update active CAO docs and notes in `README.md`, `docs/reference/`, `context/issues/known/`, and `openspec/specs/` so they stop using orphan-path CAO source references
- [ ] 1.2 Replace active upstream CAO repository links and ambiguous package-name install guidance with the chosen fork-backed CAO source/install contract
- [ ] 1.3 Review provenance-facing files and keep only intentionally explicit upstream-origin wording where it is serving attribution or history

## 2. Align Launcher And Demo Guidance

- [ ] 2.1 Update CAO launcher docs and launcher error/help strings so missing-`cao-server` remediation points at the chosen fork-backed install guidance
- [ ] 2.2 Update CAO launcher demo README and runner prerequisite/troubleshooting guidance so it uses the same fork-backed install story
- [ ] 2.3 Verify CAO REST/client-contract references in active specs point at the fork-backed source-of-truth language

## 3. Verify Scope And Coverage

- [ ] 3.1 Run targeted sweeps for `extern/orphan/cli-agent-orchestrator`, `awslabs/cli-agent-orchestrator`, and `uv tool install cli-agent-orchestrator` across active `Houmao` guidance
- [ ] 3.2 Confirm any remaining upstream references are explicitly approved provenance/archive/governance exceptions
- [ ] 3.3 Re-read the final docs/specs/issue notes to confirm the active operator story consistently points at the CAO fork
