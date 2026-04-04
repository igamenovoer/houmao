## ADDED Requirements

### Requirement: `houmao-mgr server start` resolves the runtime root project-aware by default
When `houmao-mgr server start` runs in project context without an explicit `--runtime-root`, the effective runtime root SHALL default to `<active-overlay>/runtime`.

When no active project overlay exists and no stronger override is supplied, the command SHALL ensure `<cwd>/.houmao` exists and use `<cwd>/.houmao/runtime` as the resulting default runtime root.

Explicit `--runtime-root` input SHALL continue to win over project-aware defaults.

#### Scenario: Server start uses overlay-local runtime by default in project context
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** an operator runs `houmao-mgr server start` without `--runtime-root`
- **THEN** the command starts or reuses `houmao-server` using `/repo/.houmao/runtime` as the effective runtime root
- **AND THEN** owned server artifacts for that start path are written under the overlay-local runtime root

#### Scenario: Explicit runtime-root override still wins for server start
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** an operator runs `houmao-mgr server start --runtime-root /tmp/houmao-server-runtime`
- **THEN** the command uses `/tmp/houmao-server-runtime` as the effective runtime root
- **AND THEN** it does not replace that explicit override with `/repo/.houmao/runtime`
