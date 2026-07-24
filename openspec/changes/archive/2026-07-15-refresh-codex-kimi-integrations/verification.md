## Verification Evidence

Final installed versions at verification time: `codex-cli 0.144.1` and Kimi Code `0.23.5`. The initial Kimi smoke and canonical development capture used 0.23.4; subsequent tool, interruption, and corpus captures also exercised 0.23.5 within the maintained `<0.24.0` family.

### Kimi 0.23.4 Unattended Smoke

- Date: 2026-07-11
- Installed CLI: Kimi Code 0.23.4
- Source checkout: `extern/orphan/kimi-code` at `f17a6ecb52907ffabf67a26de65df89572ac515a`
- Credential handling: copied only `config.toml` and `credentials/kimi-code.json` from the local logged-in home into `/tmp/houmao-kimi-023-smoke/home`; no credential values were printed or retained in the repository
- Headless command shape: `kimi -p <redacted-prompt> --output-format stream-json`
- Headless result: two JSONL records (`assistant`, `session.resume_hint`), expected answer token observed, stderr empty
- TUI command shape: `kimi --auto`
- TUI process result: live `kimi-code` process, non-empty ready surface, no confirmation/login/session-picker anchors
- Intervention found during the first isolated TUI launch: legacy `kimi-cli` migration picker
- Supported suppression: current Kimi source checks `<KIMI_CODE_HOME>/.skip-migration-from-kimi-cli`; the maintained unattended TUI hook now creates this marker before launch
- Second TUI result after strategy-owned marker: prompt-free ready surface with no migration or confirmation anchor

No unavoidable Kimi intervention has been observed.

### Kimi 0.23.x Recorded TUI Validation

- Capture command posture: native `kimi --auto` through the maintained `kimi-tui-unattended-0.23.x` strategy, isolated home, `.skip-migration-from-kimi-cli`, empty intervention allowlist
- Corpus: five development and three held-out unattended sessions, each with multiple visible transitions and a managed explicit-input turn
- Requested source interval: `0.05s`; effective recorder throughput varied by host load while preserving high-frequency transition evidence
- Manual labels: startup unknown, empty/draft ready, live-edge moon or braille activity, response completion, ready return, and settled explicit-input success
- Strict replay: all labeled samples passed for all eight sessions; no approval, login, migration, session-picker, browser, or user-question surface appeared
- Sparse replay on the canonical development recording: regular 10 Hz, 5 Hz, and 2 Hz plus deterministic jittered and gapped 2 Hz preserved `unknown → ready → active → ready → success`
- Bursty 2 Hz replay: the brief initial ready span was omitted, but the remaining `unknown → active → ready → success` sequence was coherent and did not manufacture a failure or confirmation state
- Maintained detector behavior: activity is limited to the 0.23 live edge; historical moon rows and footer `thinking` capability text do not keep a completed turn active
- Additional current-surface captures: a native-auto `pwd` tool turn showed `Ran a command`, the live spinner, completion, and ready return without approval; an interruption capture showed `Interrupted by user` and immediate ready/interrupted state. Both passed every manual label.
- Todo/background source evidence: current Kimi renders todos in `TodoPanelComponent` while foreground activity remains owned by the shared moon/braille activity spinner; background task lifecycle is rendered as transcript/footer status and does not by itself imply a foreground turn.
- Retry source evidence: `session-event-handler.ts` deliberately handles `turn.step.retrying` with no TUI rendering (`case 'turn.step.retrying': break`). The retry event is therefore covered by headless canonical-event fixtures rather than a fabricated TUI label.

### Codex 0.144.1 Recorded TUI Validation

- Date: 2026-07-11
- Installed CLI: `codex-cli 0.144.1`
- Source checkout: `extern/orphan/codex` at `5c19155cbd93bfa099016e7487259f61669823ff`
- Source posture: GPT-5.6 catalog and current multi-agent collaboration cells inspected from the checkout
- Effective TUI posture: isolated `CODEX_HOME`, `approval_policy=never`, `sandbox_mode=danger-full-access`, YOLO-mode ready surface, Apps and plugins disabled for the controlled capture, empty intervention allowlist
- Initial timeout diagnosis: the outer test shell used `127.0.0.1:7990`, but the demo adapter did not project proxy variables into the controlled Codex process. A direct proxied API request succeeded, while process inspection confirmed that the launched Codex environment lacked those variables.
- Fix: the development demo adapter now allowlists uppercase and lowercase HTTP, HTTPS, ALL, and NO proxy variables. The rerun projected `127.0.0.1:7990` into the isolated Codex environment and completed normally.
- Requested source interval: `0.05s`; effective recorder throughput varied around 10 to 20 fps because tmux capture cost and host load are part of the measured path.
- High-rate corpus: explicit success (77 samples), Escape interruption with restored editable draft (52 samples), unattended `pwd` tool activity (137 samples), and GPT-5.6 delegated-agent activity (277 samples).
- Manual labeling order: each raw pane and managed-input timeline was labeled before tracker analysis. The labels cover empty startup, dim placeholder, literal draft, queued startup, `Working`, tool output, delegated-agent start/wait/finished-wait cells, silent interruption recovery, ready return, and settled success.
- Strict replay: all 543 labeled high-rate samples passed with the 0.144.x profile.
- Sparse replay: regular 10 Hz and 5 Hz streams passed strict sample-aligned validation. Regular, jittered, and gapped 2 Hz streams preserved meaningful semantic sequences. Success cases retained `unknown/ready → active → ready → success`; interruption retained `unknown/ready → active → ready/interrupted`, with the restored draft allowed to clear the terminal result on later samples.
- Maintained detector behavior: a later assistant response supersedes stale animated `Working` rows retained in tmux history; current queue, tool, and collaboration cells remain active; a bounded recent active-to-restored-draft transition represents Codex 0.144.1's banner-free Escape behavior.
- Registry result: Codex `>=0.144.0,<0.145.0` now selects the maintained `0.144.x` profile by default. Version gaps and `>=0.145.0` remain on the Codex fallback.
- No unavoidable operator intervention or confirmation surface was observed.

### Stale-Contract Audit

- Repository-wide searches covered implementation code, tests, docs, context, demo and starter assets, active OpenSpec artifacts, and packaged system skills.
- No user-facing document or packaged asset teaches obsolete Kimi thinking variables, the old resume conflict, a conversational `/auto on` bootstrap, a four-level GPT-5.6 ladder, or an experimental/unregistered Codex 0.144.x profile.
- Remaining `/auto on` references in current docs are explicit negative statements. The active change design and proposal retain old-version statements as problem history. Superseded requirements in the main OpenSpec tree remain pending the normal change sync/archive step and are replaced by this change's delta specs.

### Repository Validation

- `pixi run format`: passed
- `pixi run lint`: passed
- Targeted changed-area suites: 289 passed
- `pixi run test-runtime`: 843 passed
- `openspec validate refresh-codex-kimi-integrations --type change --strict --no-interactive`: passed
- `pixi run typecheck`: the changed shared-tracker error was fixed; the command still reports seven existing literal-narrowing errors in `managed_launch_force.py`, `managed_prompt_header.py`, and `launch_policy/engine.py`, none introduced by this change
- `pixi run test`: 2265 passed and 13 skipped; two unrelated existing failures remain because `extern/orphan/plotly.js/dist/plot-schema.json` is absent and one Click-version assertion expects the older `No such option '--endpoint'` punctuation
