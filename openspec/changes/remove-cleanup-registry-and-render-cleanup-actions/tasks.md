## 1. Retire the native cleanup alias

- [ ] 1.1 Remove `houmao-mgr admin cleanup-registry` from the native admin command tree and update help-surface behavior to keep `admin cleanup registry` as the only supported shared-registry cleanup path.
- [ ] 1.2 Update cleanup CLI tests to cover the grouped path, assert that `admin --help` no longer lists `cleanup-registry`, and verify that the retired alias now fails with a corrective error.

## 2. Add shared cleanup rendering

- [ ] 2.1 Implement shared plain/fancy cleanup renderers for the normalized cleanup payload shape without changing the JSON cleanup payload contract.
- [ ] 2.2 Route all cleanup emit sites through the shared cleanup renderer, including `admin cleanup`, `agents cleanup`, `mailbox cleanup`, and `project mailbox cleanup`.
- [ ] 2.3 Add or update output-focused tests to verify that human-oriented cleanup output prints populated planned/applied/blocked/preserved actions line by line instead of only summary placeholders.

## 3. Update docs and verify the change

- [ ] 3.1 Update CLI and registry cleanup reference docs to remove the retired alias and describe the per-action cleanup output under the grouped `houmao-mgr admin cleanup registry` path.
- [ ] 3.2 Run the targeted cleanup and output test suites and confirm the changed help surface and cleanup rendering behavior.
