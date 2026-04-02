## 1. Projection Contract

- [x] 1.1 Update mailbox skill projection helpers to compute Claude-native top-level Houmao mailbox skill paths while preserving non-Claude projection behavior.
- [x] 1.2 Update runtime prompt/path helpers to derive visible mailbox skill documents from the centralized tool-aware projection contract instead of hard-coded `skills/mailbox/...` assumptions.

## 2. Claude Runtime Behavior

- [x] 2.1 Update Claude runtime/starter assets and mailbox skill installation flows so Claude homes project Houmao mailbox skills as native top-level skills.
- [x] 2.2 Add or adjust focused runtime and projection tests to verify Claude mailbox skills are discoverable through Claude-native skill lookup while non-Claude tools retain their intended layout.
- [x] 2.3 Add validation that Houmao keeps runtime-owned Claude state and mailbox skill projection out of the launched workdir's `.claude/` tree.

## 3. Docs And Validation

- [x] 3.1 Update mailbox reference and internal documentation to describe the tool-specific mailbox skill projection contract, including Claude-native top-level paths.
- [x] 3.2 Validate the Claude mailbox workflow surface in a focused live or fixture-backed flow, such as the single-agent mail wake-up demo or an equivalent Claude skill-discovery probe.
