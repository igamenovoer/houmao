• Yes, but not during agent execution. Houmao generates the subskills/ tree during pack composition and installs the
  completed entrypoint into the agent home.

  The flow is:

  public/houmao-admin-entrypoint/
  + protected/houmao-shared-routines/
          ↓ compose_system_skill_pack()
  staging/houmao-admin-entrypoint/
  ├── SKILL.md
  └── subskills/houmao-shared-routines/
      ├── SKILL-MAIN.md
      └── subskills/...
          ↓ transactional installation
  <tool-home>/skills/houmao-admin-entrypoint/

  The composer copies the public template, then _compose_protected_mount() creates and populates the missing directory
  in src/houmao/agents/system_skill_manifest.py:433 and src/houmao/agents/system_skill_manifest.py:924. The lifecycle
  composes it in staging before projection at src/houmao/agents/system_skill_lifecycle.py:766.

  So the checked-in public/houmao-admin-entrypoint directory is a source component, not a standalone installable
  skill. The phrase “in this installed entrypoint” in its SKILL.md refers to the composed result.

  Your concern is valid: if anything registers or executes the raw public source directory directly, the instruction
  is broken. The current design relies on that directory only being exposed through the composer. Calling it public
  makes this distinction less obvious; it means “public interface component,” not “self-contained public skill.”

---

The current skill structure, deployment method are not following design intent. The design intent wants these:

## for deployment
- DO NOT compose skill dynamically at runtime, this will prevent copy-paste installation and `npx skills` usage.

## for skill structure
check `extern/orphan/isomer-labs` system skills, in those mega skill like `houmao-admin-entrypoint` and `houmao-agent-entrypoint`, you need to
- list the relevant subskills and subcommands, but route the calling to `houmao-shared-routines` skill, that is a standalone skill but designed not to be called automatically, but it is still exposed to the agent (we allow manual invocation)
- `extern/orphan/houmao-agents/skillset/imsight-skills/imsight-agent-skill-handling` defines a required format for skill writing, use that for public skills
- `houmao-shared-routines` skill is a public top-level skill, just not invoked automatically, only be routed to or called manually, it should still contain `SKILL.md`
- still expose agent loop skills to top level (the agent loop pro and lite skills originally), and route to them in other skills, because these two skills are very likely called manually in many cases.