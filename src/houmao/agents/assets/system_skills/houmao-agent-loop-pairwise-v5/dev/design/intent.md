# Design Intent

This note explains why `houmao-agent-loop-pairwise-v5` is shaped the way it is. It is not part of skill execution.

## Purpose

This skill is a general manual workflow for building and operating agent collaboration loops. It separates editable loop intention from generated execution material so operators can refine goals and policy without hand-editing runtime contracts.

The intended model is:

```text
<loop-dir>/
  intention/   # editable source material
  execplan/    # generated operational material
```

## Core Commitments

- Manual invocation only: the workflow should run only when the operator explicitly selects this skill or a named operation.
- User-selected root: the workflow must not invent `<loop-dir>`.
- Editable source: `intention/` is the human-maintained source area.
- Generated execution package: `execplan/` is generated from intention and should be safe to replace during `update-execplan`.
- Domain neutrality: packaged behavior must not encode domain-specific goals, toolchains, topology, scheduling policy, or evidence gates.
- Composed execution: platform operations should route through maintained Houmao skills and CLI surfaces instead of being duplicated here.
- Progressive disclosure: top-level routing should remain short; shared runtime detail belongs in `subskills/reference/`, and operation-specific detail belongs in routed subskills.

## Why Not Use Execplan As Source

Generated execplans contain machine contracts, generated skills, concrete agent bindings, docs, and sometimes harness code. Those artifacts need stable generated names and explicit revision metadata, but they are not the ergonomic place for source thinking.

Keeping `intention/` as the source avoids two failure modes:

- user edits to generated files silently drifting from the next generation pass;
- runtime agents reading exploratory Markdown as if it were an operational contract.

## Why The Contract Is General

A mature domain-specific loop plan can demonstrate the kind of package this skill should be able to generate for one concrete loop. It should inform the general concepts: manifest, specs, skills, agents, harness, docs, generated metadata, and validation posture.

It should not become global behavior. Domain-specific policy belongs in that loop's intention and generated execplan, not in the packaged skill.

## Known Gap

The current packaged skill defines the broad workflow and directory vocabulary. It does not yet provide a deterministic generator or a complete artifact-level schema for reproducing a mature reference package. Future work should close that gap by tightening the execplan contract, adding validation depth, and optionally adding adapters for existing source-design directories.
