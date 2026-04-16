## MODIFIED Requirements

### Requirement: Launch-profiles guide documents memo seeds
The launch-profiles guide SHALL document memo seeds as optional launch-profile-owned birth-time initialization for `houmao-memo.md` and `pages/`.

The guide SHALL use memo terminology for this feature, including `memo seed`, `--memo-seed-text`, `--memo-seed-file`, and `--memo-seed-dir`. It SHALL NOT call this feature a memory seed.

The guide SHALL explain:
- supported seed sources: inline text, Markdown file, and memo-shaped directory,
- accepted directory shape: `houmao-memo.md` and `pages/`,
- that memo seeds do not expose an apply policy,
- that memo seeds replace only managed-memory components represented by the seed source,
- that memo-only seeds update `houmao-memo.md` without clearing pages,
- that a directory seed containing `pages/` replaces the contained pages tree,
- that an empty `pages/` directory in a seed clears pages while leaving memo unchanged when `houmao-memo.md` is omitted,
- that `--clear-memo-seed` removes stored profile seed configuration rather than seeding an empty memo,
- that prompt overlays remain prompt shaping while memo seeds materialize durable memo/page content before launch.

#### Scenario: Reader finds memo seed terminology
- **WHEN** a reader opens the launch-profiles guide
- **THEN** the page describes the feature as memo seeds
- **AND THEN** the page does not introduce the term memory seed for this feature
- **AND THEN** the page does not document `--memo-seed-policy`

#### Scenario: Reader understands memo seed versus prompt overlay
- **WHEN** a reader compares prompt overlays and memo seeds
- **THEN** the guide states that prompt overlays affect launch prompt composition
- **AND THEN** the guide states that memo seeds write represented `houmao-memo.md` and contained `pages/` content before provider startup

#### Scenario: Reader understands memo-only seeds
- **WHEN** a reader checks memo seed behavior for `--memo-seed-text "note"`
- **THEN** the guide states that the launch replaces `houmao-memo.md`
- **AND THEN** the guide states that the launch does not clear existing pages
