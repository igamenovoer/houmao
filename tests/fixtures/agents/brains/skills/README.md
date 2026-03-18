# Skills Repository

Skills follow Agent Skills format (`<skill-name>/SKILL.md`).

Initial seed skills were copied from existing OpenSpec automation skills.

To add a skill:

1. Create `agents/brains/skills/<skill-name>/SKILL.md`.
2. Keep skill instructions self-contained (link only required references).
3. Use the skill name in brain recipes or direct builder inputs.

Use the tracked `skill-invocation-probe` fixture when the question under test is whether an installed skill triggers cleanly from narrow prompt wording.

Its stable trigger phrase is `workspace probe handshake`, and its stable side effect is writing `.houmao-skill-invocation-demo/markers/workspace-probe.json` in the launched workdir.
