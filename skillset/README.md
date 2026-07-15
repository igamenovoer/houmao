# Houmao Skillsets

This directory provides convenient development-time access to the skillsets associated with Houmao.

- `dev/` contains project development skills for contributors working on the Houmao system itself. These skills are internal development tools and are not published as Houmao runtime skills.
- `runtime/` exposes the Houmao runtime skills that the system publishes for use by agents. It is a symlink to the canonical packaged assets in `src/houmao/agents/assets/system_skills/`; edit the files at that source location rather than replacing the link.
