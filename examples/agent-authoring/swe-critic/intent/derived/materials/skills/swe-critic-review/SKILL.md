---
name: swe-critic-review
description: Use when swe-critic performs its assigned codebase and design review and reports evidence-backed design-quality findings.
license: MIT
---

# swe-critic Review Method

## Workflow

1. **Frame the review.** Restate the objective from the role prompt. Identify the target project's stated maturity (demo or production) and the review scope. If the objective leaves maturity or scope ambiguous, state your assumption before proceeding.
2. **Survey before judging.** Map the project layout, entry points, dependency directions, documentation, and tests. Note what the project claims to be before assessing what it is.
3. **Assess each dimension.** Work through extensibility, ease of understanding, responsibility division, and coherence versus coupling. For every candidate finding, collect concrete file and line evidence first; drop impressions you cannot ground.
4. **Rank and separate.** Order findings by severity. Keep structural problems (layering violations, tangled responsibilities, brittle extension points) separate from stylistic preferences. Flag adjacent design-quality concerns, such as hidden dependencies or misleading naming, only when they are material.
5. **Report.** Use the reporting contract below.

## Reporting Contract

- Lead with a short overall assessment calibrated to project maturity.
- List findings in severity order. Each finding carries: title, severity, dimension, evidence (file and line references), why it matters, and a suggested direction rather than a full redesign.
- Close with strengths worth preserving, so later changes do not destroy what already works.
- Preserve uncertainty explicitly where evidence is incomplete; never present a guess as a finding.

## Boundaries

- Do not modify the reviewed project. Review is read-only unless the operator separately asks for implementation.
- Do not review generated code, vendored dependencies, or build output unless the objective names them.
