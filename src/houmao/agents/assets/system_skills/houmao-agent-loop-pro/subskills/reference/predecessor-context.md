# Predecessor Context

## Purpose

Use this page when generating or validating generic-loop communication.

## Core Rule

Generic loop routes must consider predecessor-context needs, but they do not always carry upstream context.

For each non-trivial route or message family, decide whether the receiver needs:
- only the current message;
- selected predecessor mail refs;
- selected ancestor refs;
- artifact, branch, commit, state, or evidence refs;
- compact summaries;
- current-hop delta;
- explicit context keys;
- no carried upstream context.

## Contract Shape

Record the selected posture in communication, process, topology, manifest, generated docs, or validation notes.

When context is selected, define:
- fields to carry or reference;
- renderer sections needed for human readability;
- harness validation or query surfaces when useful;
- state refs or lineage facts when durable bookkeeping needs them.

When context is intentionally omitted:
- make the omission explicit when the route is non-obvious;
- validation should not fail solely because no predecessor context is carried.

## Rules

- Do not require a fixed context bundle for every generic-loop mail family.
- Do not make downstream agents guess which distant upstream mail, artifact, or state entry matters when the execplan says they need that context.
- Store compact refs and lineage in state when needed; keep full prose, analysis, and rendered bodies in mail or artifacts.
