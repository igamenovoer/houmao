# Vault-Root Wikilink Resolver

Canonical wikilink targets are paths relative to the vault root, without a
`.md` suffix for Markdown files:

```md
[[wiki/concepts/grouped-gemm|Grouped GEMM]]
[[wiki/entities/sm100|SM100]]
[[wiki/summaries/deepgemm-source-code|DeepGEMM Source Code]]
[[raw/refs/model-weights|model weights]]
[[log/20260415#0012-migrate|migration log]]
[[outputs/queries/2026-04-15-kernel-summary|query output]]
```

The alias is the short display text. The target remains explicit so tools,
Obsidian, and generated content share one coordinate system.

## Target Classes

| Prefix | Kind | Existence check | Graph/index/orphan checks |
| --- | --- | --- | --- |
| `wiki/` | article | yes | yes |
| `raw/` | source | yes | no |
| `log/` | log | yes | no |
| `audit/` | audit | yes | no |
| `outputs/` | output | yes | no |
| other | unknown | reported missing unless compatibility resolves it | no |

## Compatibility

During migration, tools still resolve legacy article links such as
`[[concepts/foo|Foo]]`, `[[entities/bar|Bar]]`, and
`[[summaries/source|Source]]` to their `wiki/...` article targets. Lint reports
these links as non-canonical; new/generated content should not emit them.

Title-only or stem-only article links may resolve as compatibility links when a
unique article exists, but they are not canonical for generated KBs.

## Resolver Cases

| Input target | Existing file | Canonical target | Kind | Notes |
| --- | --- | --- | --- | --- |
| `wiki/concepts/foo` | `wiki/concepts/foo.md` | `wiki/concepts/foo` | article | canonical |
| `wiki/concepts/foo.md` | `wiki/concepts/foo.md` | `wiki/concepts/foo` | article | suffix accepted |
| `concepts/foo` | `wiki/concepts/foo.md` | `wiki/concepts/foo` | article | legacy, non-canonical |
| `foo` | `wiki/concepts/foo.md` | `wiki/concepts/foo` | article | stem fallback, non-canonical |
| `raw/refs/model` | `raw/refs/model.md` | `raw/refs/model` | source | checked, not graphed |
| `log/20260415#0012` | `log/20260415.md` | `log/20260415` | log | anchor preserved by renderer |
| `audit/20260415-note` | `audit/20260415-note.md` | `audit/20260415-note` | audit | checked, not graphed |
| `outputs/queries/q1` | `outputs/queries/q1.md` | `outputs/queries/q1` | output | checked, not graphed |
| `missing/foo` | none | `missing/foo` | unknown | reported missing |
