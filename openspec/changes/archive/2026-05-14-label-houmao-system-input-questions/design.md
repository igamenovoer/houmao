## Context

Houmao has many packaged system skills that ask the user for missing platform inputs: project overlays, credential targets, tool lanes, agent definitions, mailbox roots, gateway targets, launch selectors, workspace paths, loop directories, and lifecycle actions. Some pages already mention required inputs, but the question format is inconsistent and often does not separate blocking information from optional modifiers.

This change is documentation and skill-contract work. It does not change CLI behavior. The implementation should scan all packaged Houmao system skills, then edit only Houmao-system question paths.

## Goals / Non-Goals

**Goals:**

- Make every Houmao system-operation question identify required inputs separately from optional inputs.
- Preserve defaults and skip behavior by naming them in the optional section.
- Keep direct-operation skills concise and operator-oriented.
- Keep `houmao-touring` explanatory, but still explicit about required versus optional system values.
- Preserve task/domain clarification style for user objectives, acceptance criteria, algorithm choices, content preferences, and loop business semantics.

**Non-Goals:**

- Do not force required/optional labels onto user-task or domain-intent questions.
- Do not change `houmao-mgr` command behavior or output formats.
- Do not rename system skills or add new runtime dependencies.
- Do not rewrite unrelated utility-task guidance just because it lives under `system_skills/`.

## Decisions

1. Use a system-input boundary rather than a global question rule.

   A question is in scope when it asks for a Houmao platform/setup/control value needed to run a Houmao operation. Examples include project overlay location, agent-definition target, tool lane, credential name, specialist/profile/raw-profile name, managed-agent selector, mailbox root, gateway URL, workspace path, loop directory, execplan location, launch mode, lifecycle action, and validation target.

   A question is out of scope when it asks about the user's task semantics. Examples include objective wording, acceptance criteria, domain constraints, design preferences, content scope, algorithm choices, and loop business semantics. Loop clarification pages can still ask those questions without required/optional labels unless the specific question is about Houmao runtime mechanics.

2. Standardize the question shape, not the exact prose.

   Direct-operation skills should use compact Markdown:

   ```markdown
   Required:
   - `<field>`: why it is needed.

   Optional:
   - `<field>`: default, skip behavior, or supported modifier.
   ```

   A compact table is also acceptable when it is clearer, as long as required and optional inputs are visibly separated. If there are no optional inputs for that step, say `Optional: none for this step.`

3. Route repeated guidance through shared pages where possible.

   Skills with shared missing-input references should add the rule once there and keep action pages concise. Skills without shared references should update their top-level `Missing Input Questions` section or the specific action page that asks for system input.

4. Keep touring first-time friendly.

   `houmao-touring` should keep explanations, examples, recommended defaults, and skip paths. Its system-input questions should still mark required values and optional values, but the tone can remain tutorial rather than terse.

5. Test representative contract points.

   Add focused assertions for shared guidance and representative skill pages rather than brittle checks over every Markdown line. Tests should catch missing required/optional guidance on the common pages and loop/touring boundaries that are most likely to regress.

## Risks / Trade-offs

- Over-formatting intent clarification -> Mitigation: explicitly exclude user-task/domain questions and call out loop intent/execplan clarification boundaries.
- Missing a direct action page during the scan -> Mitigation: use `rg` for `ask the user`, `missing input`, and `Missing Input Questions`, then cover shared guidance and representative pages with tests.
- Touring text becoming too terse -> Mitigation: allow explanations and examples around the required/optional labels.
- Repetition across many skill files -> Mitigation: prefer shared missing-input references and short routing notes over duplicating long policy text.
