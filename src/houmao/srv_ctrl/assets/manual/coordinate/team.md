# Coordinate a Builder and Reviewer

Use an operator-directed handoff when a user wants distinct workers to build and review a specific change. Establish who may edit, where each worker runs, what they will exchange, and what qualifies as a completed review.

1. Choose a workdir for each worker. Use separate Git worktrees for independent edits. Launch each worker with its selected workdir and record the returned agent ID.
2. Send the builder a scoped task and ask for an exact commit, patch, or other artifact with verification results. Check that the artifact exists and matches the request.
3. Make that exact revision or patch available to the reviewer, especially when the reviewer has a separate worktree. Send the review criteria after checking what the reviewer can access.
4. Verify that the findings refer to the intended artifact. Report the build result, review findings, and any outstanding follow-up with the relevant agent IDs.

See `houmao-mgr agents single --agent-id <id> prompt --help` for scoped prompting. Read `houmao-mgr manual coordinate loops` if the handoff needs recurring triggers and recovery. [Houmao quickstart](https://igamenovoer.github.io/houmao/getting-started/quickstart/)
