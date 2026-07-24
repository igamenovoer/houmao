---
name: review-checklist
description: Use when the reference reviewer must perform its repository review and report evidence-backed findings.
license: MIT
---

# Review Checklist

Before substantive review work, run:

```bash
houmao-mgr agents self instance-state variables get review_depth
houmao-mgr agents self instance-state mindsets snapshot --skill review-checklist
```

Use the returned live `review_depth` and the single atomic mindset snapshot for this review. If identity verification, variable lookup, or mindset snapshot fails, stop and report the blocker.

Inspect the requested scope, reproduce relevant failures, and report findings in severity order with concrete file and line evidence. Do not change the project unless the user separately asks for implementation.
