# Chat Qualification, 2026-11-15

Change `cccc-01-add-owner-bound-chat-plugin` passed its provider, installed-distribution, failure-recovery, and two-real-agent acceptance gates. Deferred Mail remains a separate change. The complete [75-scenario map](../../docs/reference/gateway/cccc-acceptance.md) distinguishes the evidence layers.

| Input | Qualified Identity |
| --- | --- |
| CCCC upstream | `d12732ebd6dfdbc260a59a286bd5e510d04d4832` |
| Tracked receiver patch SHA256 | `477a22149476740b4364d1be57130c009cbf8abc742dfb03c3789f0535dfd169` |
| Receiver protocol | `1` |
| Houmao wheel | `houmao-2.4.0-py3-none-any.whl` |
| Houmao wheel SHA256 | `d29208a619e828e984c38b39bee96d0b82236f5a0afed4bf9ad6940c6e6bd347` |
| Optional wheel | `houmao_cccc-0.1.0-py3-none-any.whl` |
| Optional wheel SHA256 | `c316472e5fff6d168c7957a7cbeff33d0fc4f4930308507115e8542675405bbe` |

The clean pinned source and patch build passed, with 13 native Rust tests. Actual HTTP integration passed four Actor/lease/retry/history tests and six transport/coexistence tests, including a lost response after provider storage. Six isolated native-process recovery tests passed, including real 45-second expiry, daemon SIGKILL/restart, grant revocation, Actor recreation, partial recipients, repeated settlement, and Group stop without external body control. A separately prepared clean-source binary also passed actual daemon restart recovery.

Independent wheels installed offline in a fresh external environment. Both detached-process and tmux auxiliary-window gateways passed owner isolation, ordinary handoff, reply ancestry, bounded history/reference continuity, preserved body PID/conversation, broad-listener refusal, busy refusal, explicit retry, gateway absence, body replacement/death fencing, and verified cleanup. The final report is `/tmp/houmao-cccc-installed-final-2/qualification.json` in this development workspace.

The final-wheel real-agent smoke used two distinct managed UUID owners and CCCC Actors, Claude Code 2.1.323, and the explicit headless `cloud-api`/`deepseek-flash` fixture profile. One agent sent chat through its local plugin. Its peer received ordinary content and authored a reply whose native `reply_to` equals the original event ID. The provider confirmed ordinary handoff. Both agents and their owned CCCC Group were cleaned up. The private local report is `~/.local/state/houmao/cccc-real-chat-04/qualification.json`.

Final repository checks passed: format, lint, strict mypy, 3,717 unit tests (14 existing skips), distribution build/Twine validation, strict documentation build, and strict OpenSpec change validation. Core wheel/sdist inventories exclude the optional package and operational tooling. Credential exports and native/model output remain private and untracked. No external remote CCCC deployment or live online-email delivery was exercised by this chat qualification; deferred Mail qualification covers its separate Stalwart coexistence requirement.
