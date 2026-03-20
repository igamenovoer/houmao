## 1. Monitor Contract

- [x] 1.1 Update the server-backed shadow-watch monitor to present `houmao-server` state as a thin consumer surface rather than implying demo-owned tracking semantics
- [x] 1.2 Add or revise dashboard fields and labels so the header separates monitor-local poll cadence from server posture and per-agent visible stability is shown distinctly from completion debounce
- [x] 1.3 Sharpen inspect output and persisted-demo wording so timing/config values are described as server posture for the run; keep `samples.ndjson` and `transitions.ndjson` naming unchanged

## 2. Operator Workflow Copy

- [x] 2.1 Revise `scripts/demo/houmao-server-dual-shadow-watch/README.md` to describe the pack as “interactively prompt the tools and watch server-tracked state change”
- [x] 2.2 Update `case-interactive-shadow-validation.md` and related demo copy to teach the prompt-and-observe workflow while keeping the existing autotest case identifier stable
- [x] 2.3 Refresh the demo profile wording so it steers short observable turns without framing the pack as the owner of tracking semantics

## 3. Validation

- [x] 3.1 Update unit tests for the server-backed demo monitor to assert the revised server-consumer display contract
- [x] 3.2 Produce a grep-based inventory of active OpenSpec/demo references that still point to the older CAO-local shadow-watch ownership model, update the active files, and leave archived changes untouched
- [x] 3.3 Run the relevant demo/unit test subset and verify the updated docs and monitor behavior match the revised spec
