## Context

The packaged `houmao-agent-definition` authoring route drives a staged workspace:

```text
intent/src -> intent/derived -> approval -> agent-definition
```

The CLI intentionally creates and validates contract artifacts only. It does not maintain human-facing directory documentation. The workspace root is therefore the right place for an agent-generated orientation document: it can describe every stage without becoming source intent, derived machine authority, or immutable revision content.

Current digest boundaries already support this separation. Source freshness covers the overview and its referenced files under `intent/src`; derived freshness covers the interpretation, materialization authority, and copied materials under `intent/derived`; revision identity covers the materialized revision root. A root README is outside all three sets.

## Goals / Non-Goals

**Goals:**

- Make every skill-authored or skill-resumed Agent Definition workspace understandable without prior Houmao knowledge.
- Keep the README accurate at every user-facing authoring boundary, including partial work that stops before approval.
- Describe the actual directory structure and every regular file using relative paths.
- Explain which files are authoritative, generated, immutable, or safe to regenerate.
- Preserve portability and existing digest, approval, preview, and materialization behavior.

**Non-Goals:**

- Add README generation to `houmao-mgr` or guarantee it for direct CLI-only callers.
- Add a README inside the immutable Agent Definition Revision.
- Change the source, derived, revision, deployment, or instance-contract schemas.
- Make README text an input to derivation, approval, validation, or deployment.
- Introduce a reusable renderer, template engine, or new runtime dependency.

## Decisions

### Use standard root-level `README.md`

The authoring route will create `<authoring-dir>/README.md`, not `READMD.md`. Git hosting tools and users recognize the standard name automatically. The file is a generated orientation sidecar owned by the skill workflow.

Alternatives considered:

- A custom filename would be less discoverable.
- `intent/src/README.md` would risk accidental inclusion as user source and blur authority.
- `agent-definition/README.md` would change immutable revision contents and would not explain the authoring layers.

### Refresh at user-facing boundaries

The route will refresh the README after initialization or workspace resumption and immediately before each return, review stop, or handoff following derivation, approval, preview, materialization, or validation. This captures partial states such as “derived, not approved” instead of documenting only completed revisions.

The README will describe files that currently exist. Expected future outputs may appear in a separate continuation section, but not in the current file inventory.

### Define content, not exact prose

The skill will require these semantic sections:

1. agent name and purpose;
2. current lifecycle state;
3. actual relative directory tree;
4. exhaustive regular-file inventory with relative links and concise explanations;
5. ownership and authority of source, derived, revision, and README content;
6. revision identity and digests when available;
7. relative continuation, validation, and deployment guidance;
8. distribution guidance for the full authoring workspace versus `agent-definition/`.

The skill may adapt headings and prose to the definition. This avoids brittle generated text while retaining testable content requirements.

### Keep the README non-authoritative and portable

The README will state that it is generated orientation and can be refreshed. Contract changes belong in `intent/src`, not in the README. It will not contain credentials, secrets, absolute machine paths, temporary operator paths, or claims about files outside the workspace.

When materialization uses an external output path, the README may record definition identity, revision id, and digest, but it will not serialize the absolute output path or claim that the revision travels with the workspace.

### Prefer workspace-local materialization

When the user does not specify an output, the skill will use the CLI default `<authoring-dir>/agent-definition`. An explicit external output remains supported. Keeping the ordinary revision inside the workspace makes the directory self-contained for handoff and allows the README to inventory it.

### Update qualification without adding cases

Behavior catalog version 5 will advance `ADF-001` and `ADF-002` to revision 2. Their routes and profile tiers stay unchanged, but required observables will include a current root README. Existing semantic-digest fixtures will preserve every unaffected case.

The maintained `swe-critic` example will gain a representative final-state README and deterministic tests will check the skill contract and example coverage.

## Risks / Trade-offs

- **README accuracy depends on agent compliance** → Require refresh immediately before every return boundary and cover manual and automatic routes with behavior cases.
- **Exhaustive inventories can become long** → Keep explanations concise and group directory purpose separately while still listing every regular file.
- **Users may edit generated prose as if it were source intent** → State the authority boundary prominently and route requirement changes to `intent/src/agent-def-overview.md`.
- **External materialization cannot travel with the workspace** → Prefer the workspace-local default and describe external revisions only by portable identity facts.
- **Direct CLI callers still receive no README** → Document this as a skill-owned behavior; a future CLI feature can be proposed independently if universal generation becomes necessary.

## Migration Plan

1. Update the packaged authoring page and entrypoint help.
2. Add the final-state README to the existing `swe-critic` example.
3. Update user documentation and deterministic system-skill tests.
4. Advance the behavior catalog and the two authoring cases.
5. Validate system-skill versions, documentation, behavior fixtures, and the example revision.

Rollback removes the skill instructions and example README. No stored schema or runtime migration is required.

## Open Questions

None for this scope. Revision-local README generation remains explicitly separate.
