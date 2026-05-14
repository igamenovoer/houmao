## 1. Agent Definition Skill

- [x] 1.1 Update `houmao-agent-definition` easy profile guidance to state that unspecified launch posture is TUI/local-interactive preferred when supported.
- [x] 1.2 Update raw-profile guidance to omit stored `--headless` unless explicitly requested or required by the selected tool/lane.
- [x] 1.3 Update `create-agent-fast-forward` guidance to separate unattended prompt mode from TUI/headless launch posture and to report TUI-preferred posture when supported.
- [x] 1.4 Update specialist-scoped easy launch guidance to omit `--headless` by default, while preserving Gemini or other required-headless exceptions.

## 2. Agent Instance Skill

- [x] 2.1 Update `houmao-agent-instance` launch action guidance so direct role/preset launch omits `--headless` when launch posture is unspecified and TUI is supported.
- [x] 2.2 Update raw-profile-backed launch guidance so agents do not add one-shot `--headless` unless explicitly requested, while preserving stored profile posture.
- [x] 2.3 Update specialist-backed launch guidance so agents omit `--headless` by default for TUI-capable tools and describe required-headless exceptions explicitly.

## 3. Verification

- [x] 3.1 Search packaged system skills for launch/profile guidance that could still imply headless by default and revise any conflicting wording.
- [x] 3.2 Run a focused verification command for the changed OpenSpec artifacts and Markdown asset consistency.
- [x] 3.3 Record the verification evidence in the implementation summary.
