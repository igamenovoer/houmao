## ADDED Requirements

### Requirement: Launch-profiles guide documents memo seeds
The launch-profiles guide SHALL document memo seeds as optional launch-profile-owned birth-time initialization for `houmao-memo.md` and `pages/`.

The guide SHALL use memo terminology for this feature, including `memo seed`, `--memo-seed-text`, `--memo-seed-file`, `--memo-seed-dir`, and `--memo-seed-policy`. It SHALL NOT call this feature a memory seed.

The guide SHALL explain:
- supported seed sources: inline text, Markdown file, and memo-shaped directory,
- accepted directory shape: `houmao-memo.md` and `pages/`,
- seed policies `initialize`, `replace`, and `fail-if-nonempty`,
- that the default `initialize` policy preserves non-empty existing memo/page state,
- that prompt overlays remain prompt shaping while memo seeds materialize durable memo/page content before launch.

#### Scenario: Reader finds memo seed terminology
- **WHEN** a reader opens the launch-profiles guide
- **THEN** the page describes the feature as memo seeds
- **AND THEN** the page does not introduce the term memory seed for this feature

#### Scenario: Reader understands memo seed versus prompt overlay
- **WHEN** a reader compares prompt overlays and memo seeds
- **THEN** the guide states that prompt overlays affect launch prompt composition
- **AND THEN** the guide states that memo seeds write `houmao-memo.md` and contained `pages/` before provider startup
