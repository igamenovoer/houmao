# Extension Guide

This guide is for developers revising `houmao-agent-loop-pairwise-v5`. It is not part of the skill execution path.

## Preserve The Split

Keep these responsibilities separate:

- `SKILL.md`: activation, routing, global boundaries, and the required root vocabulary.
- `subskills/reference/`: shared runtime guidance read by routed operation pages through `Read First` sections.
- `subskills/authoring/`: source creation, source refinement, execplan generation, validation, and execplan updates.
- `subskills/execution/`: operating a validated execplan through generated contracts and maintained Houmao surfaces.
- `scripts/scaffold.py` plus `assets/scaffolds/`: shared ownership for scaffold-owned starter files and directory shells.
- `dev/design/`: rationale for maintainers only.

Do not put long design rationale into execution-facing pages. Those pages should stay concise and actionable for the active agent.

Do not put runtime guidance that agents must follow only in `dev/design/`. Move shared execution guidance to `subskills/reference/`, then let operation pages name the needed references in `Read First`.

Keep `SKILL.md` as a router. If it starts accumulating scaffold profiles, generated-contract details, bookkeeping rules, mail-runtime details, or platform-boundary details, move that material to a reference page and leave a concise pointer.

Do not duplicate scaffold-owned starter file bodies across routed pages. If the initial README, manifest seed, named docs starter, or execplan ADR shape changes, update the packaged scaffold assets first and then keep the routed pages aligned to the profile names that own them.

Generated artifact directory README files are scaffold and generation support material. Keep them concise and limited to `Purpose` and `Contents`; do not move contract authority into README prose.

## Adding Source Inputs

The first workflow intentionally uses `intention/README.md` and `intention/loop-overview.md` as the minimum source set. If a later change adds ADRs, templates, imported source directories, or reference-plan harvesting, keep that as an explicit authoring capability and preserve the rule that `intention/` remains the normal source authority for execplan updates.

If importing from an existing source-design directory, define a clear adapter step instead of silently treating arbitrary Markdown as a valid root.

## Tightening Generation

When tightening execplan generation, update the contract in small layers:

1. add the generated artifact requirement to the authoring subskill;
2. add matching validation checks;
3. update execution subskills only when the new artifact affects runtime behavior;
4. update these design notes with the rationale.

Prefer explicit unresolved entries over inferred behavior. A generated execplan that says what it cannot decide is easier to repair than one that hides assumptions.

## Clarification Commands

Preserve the source-authority split:

- `clarify-intent` works on what the loop means. It reads `intention/`, project context, and intent ADRs, then writes intent ADRs plus intention Markdown.
- `clarify-execplan` works on how the generated loop is implemented. It reads `execplan/`, prior execplan ADRs, and runtime references, then writes execplan ADRs plus affected generated artifacts or stale-artifact notes.

Both commands should scan coverage before asking, ask at most five accepted questions, ask exactly one question at a time, recommend answers when context supports it, and update artifacts immediately after accepted answers.

If `clarify-execplan` exposes missing or contradictory user intent, do not patch around it in generated artifacts. Report the gap and send the operator back to `clarify-intent` or direct intention edits.

## Harness Dependencies

Generated harnesses may use `click`, `jinja2`, and `jsonschema` when their generated features need modular commands, Markdown template rendering, or schema validation. Preserve this dependency order:

- treat these libraries as normal Houmao runtime dependencies provided by the Houmao-installed environment;
- use packages already importable by the intended harness interpreter when possible;
- when imports fail, generated entrypoints should name the missing dependency and tell the caller to install it into the active harness Python environment or use the Python environment associated with the installed Houmao uv tool;
- when generated harness tests fail because dependencies are missing or the wrong interpreter appears active, tell the authoring agent to retry the same test through the Houmao uv-installed environment before changing harness logic;
- generate `execplan/harness/requirements.txt`, `execplan/harness/vendor/`, and `python -m pip install --target` guidance only for intentional standalone/custom execution;
- add a local `sys.path` bootstrap before generated entrypoints import locally installed packages only when optional `vendor/` support exists;
- record dependency posture, interpreter evidence, import-failure guidance, install commands for standalone support, and diagnostics in generated harness metadata.

Do not reintroduce source-bundled wheel files for these harness libraries. Do not add dependency guidance that requires global Python, user site-packages, or project-environment mutation.

## Generated State And TOML

When improving generated state guidance, preserve the control-plane split:

- state stores compact facts, refs, ownership, decisions, transitions, evidence links, and completion posture;
- mail, docs, and artifacts store rich prose, rationale, pseudocode, rendered Markdown, and detailed analysis;
- sqlite is the default when the generated loop has stable entities and transitions with a clear SQL schema;
- JSONL plus explicit schemas is the alternate for append-only or schema-light state;
- unstructured ad hoc state files are not acceptable when either structured option is feasible.

Generated TOML files should stay readable and explainable:

- put plain human-readable comments above generated section headers;
- use TOML `description` fields for records or sections exposed through harness commands;
- use `description` fields, not parsed comments, as the source for harness `--explain`.

## Execution Boundaries

Execution should compose existing Houmao operation surfaces. Keep managed-agent launch, mailbox, gateway, memory, lifecycle, inspection, and platform setup routed to their owning skills or supported `houmao-mgr` surfaces.

Keep execution preparation and readiness validation as separate ordered stages:

- `prepare-agents` prepares profiles, concrete agent/profile facts, generated skill bindings, maintained support skills, mailbox/gateway posture, memory posture, notifier prompt posture, and launch facts;
- `prepare-workspace` adapts generated workspace contracts, generated agent bindings, and prepared agent/profile facts to `houmao-utils-workspace-mgr` plan or execute inputs, then reports readiness facts; explicit manual evidence may replace this command only when it satisfies the generated workspace contract;
- `validate-loop` checks concrete pre-launch readiness before `launch-agents`;
- `launch-agents` launches prepared participants through maintained Houmao launch surfaces and does not send loop-start work;
- `start` sends the first loop trigger after agents are live and does not launch agents;
- `prepare-agents` and `prepare-workspace` do not call each other;
- missing live readiness is reported by `validate-loop` or `launch-agents`, not by authoring-time `validate-execplan`.

Loop-local behavior belongs in generated material:

- role instructions and event handlers under `execplan/skills/`;
- participant and concrete-agent mapping under `execplan/agents/`;
- deterministic loop state helpers under `execplan/harness/`;
- machine contracts under `execplan/specs/`.

Do not duplicate maintained Houmao platform contracts inside generated loop skills unless a later change explicitly moves ownership.

## Domain Neutrality

The packaged skill must remain domain-neutral. Domain-specific material may appear in examples, fixtures, or generated artifacts for a specific loop, but never as required global behavior.

When a domain-specific reference reveals a general need, promote the general contract rather than the domain fact. For example, promote "evidence gates belong in `specs/` and participant skills must consult them" instead of promoting one loop's exact gate values.
