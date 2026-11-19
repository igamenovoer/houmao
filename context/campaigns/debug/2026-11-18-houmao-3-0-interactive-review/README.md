# Houmao 3.0 Interactive Feature Review

Validate and review features introduced across the Houmao 3.0 release candidates through live, human-watched interactive execution so an operator can observe runtime behavior directly and decide what works as designed or needs revision. The current qualification target is `3.0.0rc3`; RC1 and RC2 records remain release-specific historical evidence rather than current coverage.

See [debug-intent.md](debug-intent.md) for the complete campaign description, and see [houmao-3-0-interactive-review harness](../../../../scripts/explore/houmao-3-0-interactive-review/README.md) for the temporary campaign helper scripts and isolation wrappers.

## Directory Structure

- **debug-intent.md**: Root campaign document with problem statement, scope, boundaries, and status updates
- **key-questions/**: Testable questions with propositions, answers, and scope declarations (`KQ-N-<slug>.md`)
- **iterations/**: Execution plans with frozen workload, predeclared arms, gates, and checklists (`YYYY-MM-DD-plan-N-<slug>.md`)
- **evidences/**: Raw observation logs from interactive sessions with exact commands, outputs, and environment identity (`YYYY-MM-DD-<observation>.md`)
- **logs/**: Diagnostic session and failure logs captured during interactive review runs (`YYYY-MM-DD-<topic>.md`)
- **discussions/**: Analysis and revision proposals distinguishing observed symptoms, root causes, and design options (`YYYY-MM-DD-<topic>.md`)
- **reports/**: Synthesis across multiple evidences summarizing verdicts and revision recommendations (`YYYY-MM-DD-<topic>.md`)
