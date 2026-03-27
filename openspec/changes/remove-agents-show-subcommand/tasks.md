## 1. CLI Surface Removal

- [ ] 1.1 Remove the `houmao-mgr agents show` command registration and any now-unused CLI helper wiring for that subcommand.
- [ ] 1.2 Verify the `houmao-mgr agents` help surface no longer advertises `show` and that supported inspection guidance still points to `state`, `agents gateway tui ...`, and related remaining commands.

## 2. Docs And Workflow Cleanup

- [ ] 2.1 Update reference docs that currently list or recommend `houmao-mgr agents show`, including native CLI and pair-workflow guidance.
- [ ] 2.2 Update workflow documents and examples that invoke `houmao-mgr agents show` so they use supported inspection commands instead.

## 3. Test And Fixture Updates

- [ ] 3.1 Update CLI shape and command-contract tests that currently expect the `show` subcommand to exist.
- [ ] 3.2 Update any workflow fixtures or demo-related assertions that reference `houmao-mgr agents show` so the test suite reflects the removed command.
