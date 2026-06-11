## 1. Keyboard Shortcut Implementation

- [x] 1.1 Add a local `Shift+Enter` submit handler for normal agent pane prompt text areas that calls the existing Run submission path
- [x] 1.2 Add a local `Shift+Enter` submit handler for Debug Agent editor text areas that calls the existing Send submission path
- [x] 1.3 Preserve multiline editing by allowing plain `Enter` to keep normal textarea newline behavior
- [x] 1.4 Ignore repeated or empty `Shift+Enter` submissions without adding new visible errors
- [x] 1.5 Ensure read-only text areas, target configuration fields, search/filter fields, and tmux terminal input do not submit prompts through this shortcut

## 2. Browser Coverage

- [x] 2.1 Update workbench E2E coverage so an agent pane prompt submitted with `Shift+Enter` sends the same AG-UI run request as the Run button and clears the prompt
- [x] 2.2 Add or update workbench E2E coverage proving plain `Enter` in an agent prompt inserts a newline and does not submit
- [x] 2.3 Add or update Debug Agent E2E coverage so the debug editor sends with `Shift+Enter` and updates the debug display
- [x] 2.4 Add or update coverage proving whitespace-only `Shift+Enter` in send-capable editors is ignored

## 3. Validation

- [x] 3.1 Run `bun run typecheck` in `apps/ag-ui-workbench`
- [x] 3.2 Run the relevant Playwright workbench tests covering agent prompt and Debug Agent send behavior
- [x] 3.3 Run `openspec validate submit-prompts-with-shift-enter --strict --no-interactive`
