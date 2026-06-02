## 1. Narrow Draft Registry

- [x] 1.1 Update `project.easy.specialist` draft fields to accept only required `name`, `tool`, and `credential`.
- [x] 1.2 Update `project.easy.profile` draft fields to accept only required `name`, `specialist`, and `credential`.
- [x] 1.3 Update `project.agents.launch-profile` draft fields to accept only required `name`, `recipe`, and `credential`.
- [x] 1.4 Remove now-unused draft field helpers, choice constants, and conflict definitions that only supported hidden optional override fields.

## 2. Render Minimal Opinionated YAML

- [x] 2.1 Update the specialist renderer to emit fixed specialist draft values plus caller-supplied name, tool, and credential reference only.
- [x] 2.2 Update easy-profile rendering so credential is required and rendered as the profile auth/credential reference.
- [x] 2.3 Update raw launch-profile rendering so credential is required and rendered as the profile auth/credential reference.
- [x] 2.4 Ensure generated YAML does not include hidden optional sections for model, reasoning, env, mailbox, skills, system skills, posture, gateway, managed header, prompt overlay, memo seed, relaunch, or credential material.

## 3. CLI and Skill Guidance

- [x] 3.1 Update `config-drafts list` expectations so required intent keys reflect the narrowed field sets.
- [x] 3.2 Update packaged `houmao-agent-definition` skill guidance to describe config drafts as minimal opinionated drafts and route full customization to maintained project subcommands.
- [x] 3.3 Update related profile/raw-profile/memory guidance so generated draft examples include credential and do not advertise hidden optional override inputs.

## 4. Tests and Verification

- [x] 4.1 Update unit tests for each initial draft's minimal YAML shape and required credential behavior.
- [x] 4.2 Add or update blocker tests showing hidden full-model fields such as `model`, `api_key`, `profile_lane`, env, memo seed, and mailbox fields are rejected.
- [x] 4.3 Update CLI tests for `internals config-drafts list` and `generate` to include credential in successful intents.
- [x] 4.4 Update system-skill text regression tests for the narrowed guidance.
- [x] 4.5 Run focused config-draft and system-skill tests.
- [x] 4.6 Run `pixi run test`, `pixi run lint`, and `pixi run typecheck`.
