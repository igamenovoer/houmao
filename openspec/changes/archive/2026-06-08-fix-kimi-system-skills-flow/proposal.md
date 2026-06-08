## Why

Kimi Code TUI can now run as a maintained local interactive provider, but the system-skill-driven user flow still partly treats Kimi as unavailable or headless-only. Users who rely on Houmao skills to create credentials, create a specialist, install system skills, or launch a managed Kimi agent need those paths to agree with the new Kimi TUI runtime contract.

## What Changes

- Allow project-backed Kimi specialists to launch through the maintained TUI/local-interactive path when headless posture is not requested, while Gemini remains headless-only on the project easy launch surface.
- Resolve the Kimi system-skill projection contract so Houmao-owned skills are actually reachable by Kimi Code when installed or auto-projected for managed launches.
- Update `houmao-credential-mgr` guidance to include Kimi credential add/set/list/get/rename/remove surfaces and Kimi-specific credential inputs, while keeping login-helper guidance scoped to providers that have a maintained login helper.
- Update `houmao-agent-definition` guidance so specialists, profiles, create-agent-fast-forward, and launch-agent paths describe Kimi as a supported tool and avoid stale headless-only language.
- Add or repair credential reference material used by installed system skills, including Kimi references and existing broken `houmao-agent-definition` credential-reference links.
- Update system-skills and run/project documentation so Kimi skill projection, `KIMI_CODE_HOME`, `.kimi-code/skills`, headless-only `--skills-dir`, and TUI launch posture are described consistently.
- Add tests proving the packaged system skills and project launch flows expose the Kimi path correctly.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-project-easy-cli`: Kimi project specialists can use TUI/local-interactive launch when headless posture is omitted, and only Gemini remains headless-only.
- `houmao-mgr-system-skills-cli`: Kimi system-skill installation/status semantics are aligned with Kimi Code's real skill discovery and managed-launch projection contract.
- `component-agent-construction`: Managed Kimi brain homes make projected skills discoverable through Kimi-supported additive configuration rather than assuming `KIMI_CODE_HOME/skills` is auto-discovered.
- `houmao-manage-credentials-skill`: The packaged credential-management skill supports Kimi credential CRUD guidance and Kimi credential input references.
- `houmao-manage-agent-definition-skill`: The packaged agent-definition skill supports Kimi specialist/profile/launch guidance without stale Claude/Codex/Gemini-only examples.
- `docs-cli-reference`: CLI reference material documents the corrected Kimi system-skill and launch posture behavior.
- `docs-system-skills-overview-guide`: Getting-started system-skill guidance includes Kimi home resolution and Kimi skill reachability constraints.

## Impact

- Affected runtime/control code includes project-backed managed-agent launch posture checks, Kimi tool-home or skill-projection handling, and possibly brain construction or launch-plan metadata if Kimi managed skills require an explicit provider skill path.
- Affected packaged assets include `houmao-credential-mgr`, `houmao-agent-definition`, `houmao-agent-instance`, `houmao-touring`, credential reference files, and any docs that list supported tool lanes.
- Affected tests include project easy launch tests, system-skill projection/status tests, packaged skill content tests, and docs tests.
- External dependency behavior is grounded in the local Kimi Code source reference under `extern/orphan/kimi-code`, especially its documented skill search paths and `--skills-dir` semantics.
