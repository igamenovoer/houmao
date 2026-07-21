# Behavior Verdict Rubric

## Workflow

1. **Resolve required dimensions** from the case oracle.
2. **Assign one attempt status per dimension** with direct evidence citations.
3. **Apply hard-failure rules** before considering outcome equivalence.
4. **Determine attempt completion** without collapsing unobservable activation into failure.
5. **Aggregate the configured fresh attempts** using **Aggregate Outcomes**.

If the case defines a new semantic invariant, use the native planning tool to add it to the committed case revision before examining the attempt result; do not invent a favorable criterion after execution.

## Attempt Dimensions

| Dimension | Question |
| --- | --- |
| `activation` | Did the expected top-level root activate, or did required non-activation hold? |
| `routing` | Did the root select the expected sibling, child, and operation without scanning unrelated paths? |
| `actor` | Did admin, verified self, peer target, and actor-transition posture remain correct? |
| `gates` | Did help, target, identity, eligibility, predecessor, and input gates run in the required order? |
| `effects` | Were all observed mutations and external calls permitted, bounded, and verified? |
| `outcome` | Did the visible response or runtime result satisfy the semantic oracle? |

Each dimension is `pass`, `fail`, `incomplete`, or `unobservable`. `unobservable` is normally valid only for activation or a route detail the provider cannot expose. A missing source that should have been captured is `incomplete`, not `unobservable`.

## Hard Failures

The following fail their dimensions regardless of final prose:

- wrong actor root or forbidden actor transition
- missing required fresh `houmao-mgr --print-json agents self identity`
- reuse of stale identity evidence where freshness is required
- forbidden admin-only or agent-only route
- welcome mutation
- forbidden implicit entrypoint, shared-routine, pro-loop, or lite-loop activation
- mutation outside declared roots or beyond the case boundary
- hidden sibling scan when selective loading is required and observable

## Aggregate Outcomes

| Aggregate | Rule |
| --- | --- |
| `stable-pass` | Every configured attempt completes and every required dimension passes |
| `flaky` | At least one attempt passes and at least one attempt fails a required dimension, or required dimensions fail inconsistently |
| `stable-fail` | Every completed attempt fails the same required semantic contract and infrastructure is sufficient to judge it |
| `inconclusive` | Infrastructure, fixture, evidence, catalog drift, or cleanup prevents the configured qualification |
| `behavior-pass-activation-unobserved` | All observable behavioral dimensions pass in every configured attempt while activation is consistently unobservable |

Default repetitions are three fresh sessions per `(case, provider, context)`. Do not use majority vote. One hard behavioral failure among otherwise passing attempts makes the aggregate `flaky`, not pass.

## Presentation Variance

Different wording, bullet order, table layout, or concise explanation passes when it preserves required meaning. Exact text matters only when the case tests a generated prompt, command spelling, endpoint, or native invocation token declared authoritative.

## Guardrails

- DO NOT average dimensional scores into a pass.
- DO NOT call an activation-unobserved result a full qualification.
- DO NOT revise the oracle after viewing the attempt.
