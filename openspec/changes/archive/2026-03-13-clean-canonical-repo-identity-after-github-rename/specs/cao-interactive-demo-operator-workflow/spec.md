## MODIFIED Requirements

### Requirement: README appendix SHALL make the tutorial easy to rerun and debug
The tutorial README SHALL include an appendix describing the key parameters,
tracked inputs, generated outputs, supported startup recipes, and supporting
source files used by the interactive demo pack, including the control-input
wrapper and the dedicated control artifact family.

When the appendix includes repo-owned module invocation examples, it SHALL use
the canonical `houmao...` package paths rather than superseded
`gig_agents...` module paths.

The README SHALL avoid presenting host-specific absolute checkout paths as the
default rerun contract. When filesystem locations are part of active operator
guidance, it SHALL use repo-relative paths or an explicit placeholder such as
`<repo-root>` unless the path is clearly labeled as observed diagnostic output
or historical context.

#### Scenario: Appendix enumerates important files, parameters, and recipe choices
- **WHEN** a developer wants to inspect or rerun the tutorial environment
- **THEN** the README lists the fixed CAO base URL, the tutorial agent identity, the default workspace location, and the main wrapper or CLI entrypoints including the control-input wrapper
- **AND** it identifies the default Claude launch as the tracked recipe `claude/gpu-kernel-coder-default`
- **AND** it identifies the supported explicit `--brain-recipe` examples without requiring the `brains/brain-recipes/` prefix
- **AND** it explains that direct `run_demo.sh start` uses the selected recipe's default agent name unless the operator supplies `--agent-name`
- **AND** it explains that subdirectory context may be required when recipe basenames collide, such as the shared `gpu-kernel-coder-default` basename for Claude and Codex
- **AND** it includes an explicit ambiguity-error example that tells the operator to retry with subdirectory context when basename-only lookup matches more than one recipe
- **AND** the README identifies the relevant input files, generated workspace files including control-input artifacts, and supporting implementation files for debugging
- **AND** it notes that `launch_alice.sh` is only a convenience wrapper that injects `--agent-name alice` rather than the source of the demo's default naming semantics
- **AND** it uses canonical `houmao...` module paths for repo-owned module invocation examples
- **AND** it uses repo-relative paths or explicit placeholders for rerunnable file locations and commands instead of presenting a host-specific absolute checkout path as the default operator contract
