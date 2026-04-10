## REMOVED Requirements

### Requirement: Houmao provides a packaged `houmao-loop-planner` system skill
**Reason**: Pairwise authoring and prestart now live directly in `houmao-agent-loop-pairwise`, and the repository no longer keeps a separate generic packaged planner skill.
**Migration**: Use `houmao-agent-loop-pairwise` for pairwise authoring, preparation, and run control. Use `houmao-agent-loop-relay` directly for relay authoring and run control.

### Requirement: The authoring lane writes one canonical Markdown-first loop bundle
**Reason**: The old planner-owned generic bundle contract is being removed together with the planner skill itself.
**Migration**: Use the authored forms defined by `houmao-agent-loop-pairwise` for pairwise runs, or use `houmao-agent-loop-relay` for relay-specific authored plans.

### Requirement: The authored bundle remains static and outside agent-local runtime directories
**Reason**: This requirement belonged to the removed generic planner capability and is no longer owned by a separate planner skill.
**Migration**: Follow the storage guidance documented by the loop-kind-specific skill that now owns the authored plan you are creating.

### Requirement: The bundle defines participant, execution, and distribution guidance in structured Markdown
**Reason**: The removed planner capability no longer owns pairwise participant and prestart authoring, and the old participant/distribution document model is being replaced rather than preserved.
**Migration**: For pairwise runs, use the standalone participant preparation and prestart artifacts defined by `houmao-agent-loop-pairwise`. For relay runs, use the relay skill's authored plan form directly.

### Requirement: The final bundle includes a Mermaid graph that distinguishes the operator from execution
**Reason**: Graph requirements now belong to the loop-kind-specific skills that author and operate the run directly.
**Migration**: Use the Mermaid graph requirements defined by `houmao-agent-loop-pairwise` or `houmao-agent-loop-relay`, depending on the loop kind.

### Requirement: The handoff lane prepares runtime activation templates and routes by loop kind
**Reason**: Runtime handoff is no longer owned by a separate generic planner capability.
**Migration**: Use `houmao-agent-loop-pairwise` directly for pairwise preparation and activation, or `houmao-agent-loop-relay` directly for relay preparation and activation.
