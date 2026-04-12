## 1. Skill Guidance Updates

- [x] 1.1 Update `houmao-agent-gateway/actions/lifecycle.md` so foreground same-session auxiliary-window attach is the first-choice command shape and `--background` is described as explicit user intent only.
- [x] 1.2 Update `houmao-specialist-mgr/actions/launch.md` so easy-instance launch guidance explains default foreground gateway auto-attach, separates `--headless` from gateway execution mode, and avoids `--gateway-background` unless explicitly requested.
- [x] 1.3 Update `houmao-agent-instance/actions/launch.md` so each launch lane preserves foreground-first gateway posture and routes later attach work to `houmao-agent-gateway`.
- [x] 1.4 Update `houmao-touring/branches/author-and-launch.md` and any necessary top-level touring guidance so first-run tours prefer visible foreground gateway posture and distinguish non-interactive tmux handoff from detached gateway execution.
- [x] 1.5 Update `houmao-adv-usage-pattern/patterns/self-wakeup-via-self-mail.md` so its gateway attach reference delegates posture selection to the foreground-first `houmao-agent-gateway` lifecycle guidance.

## 2. Audit And Consistency

- [x] 2.1 Run an `rg` audit across `src/houmao/agents/assets/system_skills` for gateway attach, gateway background, launch-time gateway, and foreground wording.
- [x] 2.2 Adjust any direct command-teaching skill text found by the audit so background gateway launch or attach is not implied as default.
- [x] 2.3 Leave route-only out-of-scope mentions concise unless they directly teach gateway launch or attach flag selection.

## 3. Tests

- [x] 3.1 Add or update system-skill content assertions in `tests/unit/agents/test_system_skills.py` for foreground-first gateway lifecycle guidance and explicit background intent.
- [x] 3.2 Add or update content assertions for specialist launch, instance launch, touring, and advanced-usage guidance where those pages teach or route gateway launch or attach posture.
- [x] 3.3 Run the targeted system-skill tests and document the exact command and result.
  - `pixi run pytest tests/unit/agents/test_system_skills.py -k cli_default_includes_agent_instance_messaging_and_gateway_skills` -> 2 passed, 15 deselected
  - `pixi run pytest tests/unit/agents/test_system_skills.py` -> 17 passed

## 4. Validation

- [x] 4.1 Run OpenSpec validation or status for `clarify-foreground-gateway-skill-guidance`.
  - `openspec validate clarify-foreground-gateway-skill-guidance --type change --strict` -> valid
- [x] 4.2 Run `pixi run lint` if the test or content changes touch linted Python or generated test expectations.
  - `pixi run lint` -> all checks passed
- [x] 4.3 Re-run the final gateway-guidance `rg` audit and confirm no direct skill guidance still teaches background gateway execution without explicit user intent.
  - `rg -n -S -- "--gateway-background|gateway-background|--background|background gateway|detached gateway|foreground gateway|same-session auxiliary|foreground-first" src/houmao/agents/assets/system_skills` -> only the intended foreground-first and explicit-background guidance remains
