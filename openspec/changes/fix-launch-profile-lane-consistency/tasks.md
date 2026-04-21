## 1. Lane Ownership Enforcement

- [x] 1.1 Extend the shared launch-profile command helpers to detect wrong-lane targets and emit verb-specific redirect guidance for `get`, `set`, and `remove`.
- [x] 1.2 Tighten explicit launch-profile `get` and `remove`, plus easy-profile `remove` and any easy lane helper wrappers, so they validate the expected `profile_lane` before returning or deleting a stored profile.

## 2. Lane-Aware Discovery And Docs

- [x] 2.1 Update explicit and easy profile list commands to keep their existing lane-filtered arrays while adding an optional note when only the other lane has matching stored profiles.
- [x] 2.2 Refresh the launch-profiles guide and nearby getting-started wording so shared projection paths are explained as lane-bounded management surfaces rather than interchangeable command families.

## 3. Regression Coverage

- [x] 3.1 Add CLI tests covering wrong-lane `get`, `set`, and `remove` flows in both directions, including redirect guidance to the correct command family.
- [x] 3.2 Add CLI tests covering empty explicit-list and empty easy-list results when profiles exist only in the opposite lane, ensuring the output keeps the current array keys and includes the new guidance note.
