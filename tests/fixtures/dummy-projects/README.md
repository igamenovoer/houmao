# Dummy Project Fixtures

`tests/fixtures/dummy-projects/` stores small tracked source trees that are copied into demo- or test-owned workdirs before live runtime sessions start.

Use a dummy project fixture when the goal is narrow runtime coverage rather than repository-scale engineering behavior.

## Selection Rubric

Choose `dummy-projects/` plus a lightweight role when:

- the test/demo only needs one mailbox turn or a small prompt turn
- the launched workdir should stay tiny and predictable
- deterministic setup matters more than repo-scale discovery behavior

Choose a repo worktree plus a heavyweight role when:

- the workflow is intentionally about large-repo navigation
- the agent should inspect broad project context before acting
- the scenario needs the real repository layout rather than a tutorial-sized sandbox

Quick decision tree:

1. Does the agent need the real repository checkout as its workdir?
   If `yes`, use a repo worktree.
   If `no`, use a copied dummy project.
2. Is the prompt about a narrow mailbox/runtime-contract action?
   If `yes`, pair the dummy project with `mailbox-demo`.
   If `no`, choose the role family that matches the broader engineering workflow.

## Source-Of-Truth Rules

- Keep fixtures source-only in git.
- Do not track `.git/` metadata inside fixture trees.
- Tests and demos must copy the fixture into a run-local path and initialize any needed git metadata after the copy.
