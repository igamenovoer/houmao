## 1. Retarget Maintained References

- [ ] 1.1 Update maintained live specs under `openspec/specs/` that still reference `tests/fixtures/agents/` so they point at `tests/fixtures/plain-agent-def/`, `tests/fixtures/auth-bundles/`, or owned generated trees as required by each workflow.
- [ ] 1.2 Update maintained docs, READMEs, helper constants, and runnable maintained surfaces that still mention the deprecated path, including the interactive Claude watch guidance and any maintained credential examples.
- [ ] 1.3 Update maintained credential-management guidance and examples so direct-dir examples use generic copied roots or `tests/fixtures/plain-agent-def/` instead of the removed path.

## 2. Guard Archived Entry Points

- [ ] 2.1 Audit archived demo scripts and legacy Python entrypoints that still default to `tests/fixtures/agents/` and classify which ones need explicit fail-fast guards once the path is removed.
- [ ] 2.2 Implement fail-fast checks and clear archived-demo messaging for legacy entrypoints that would otherwise crash late because the deprecated fixture root no longer exists.
- [ ] 2.3 Update any archived operator-facing guidance that is necessary to match the new fail-fast behavior without trying to modernize the archived workflows into maintained ones.

## 3. Remove The Deprecated Fixture Root

- [ ] 3.1 Remove the tracked `tests/fixtures/agents/` directory, including the redirect README and any remaining maintained scaffolding under that path.
- [ ] 3.2 Ensure no maintained repository surface recreates `tests/fixtures/agents/` as a stub, symlink, or compatibility alias during setup, tests, or docs generation.

## 4. Verify The Removal Contract

- [ ] 4.1 Run targeted checks for maintained path-resolution surfaces and updated examples so maintained workflows no longer depend on `tests/fixtures/agents/`.
- [ ] 4.2 Run targeted checks for the archived entrypoints covered by the new guards and confirm they fail early with clear archived-demo messaging instead of raw missing-path errors.
- [ ] 4.3 Run a repository-wide search for maintained references to `tests/fixtures/agents/` and confirm that only intentional archival or historical artifacts remain.
