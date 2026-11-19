# Stock Kimi Web Native Admission

This probe predates the revised readiness policy. Its queue behavior is preserved in the [current implementation](check-and-send.md).

## Installed Contract

An isolated loopback run of `kimi web --no-open` used installed Kimi Code `2.6.0`, a fresh private Kimi home and workspace, and the explicit `self-hosted` fixture for `Qwen/Qwen3.8-27B-FP8`. The installed OpenAPI document exposed ordinary prompt submission, queued prompt steering, and prompt abortion. Its ordinary submission schema offered no conditional readiness or conflict option. The server wrote its bearer file with mode `0600` and included the bearer in the captured private startup banner despite `--no-open`. The report contains no bearer values or access URLs.

## Busy Queue Reproduction

A private loopback relay held the first native Chat Completions request before forwarding it to Qwen. The authenticated Kimi API reported prompt `stock-houmao-07-first` active with an empty queue. A second native HTTP client submitted `stock-houmao-07-second` to the same session. Kimi responded with HTTP 200 and `status=queued`. A subsequent native read showed the first prompt still active and the second prompt alone in the queue. The second prompt had yet to reach the provider relay.

The relay released the first call and forwarded exactly two calls for the selected model to `/v1/chat/completions`, in prompt order. The private journal for session `session_3e21fbca-c8a1-49fd-a411-09c2f422627d` recorded both exact prompt IDs and completed native turns `0` and `1`. Each turn contained its distinct expected Qwen answer marker. The relay and exact native child stopped, and the temporary fixture and credentials were removed. The experiment established the stock queue behavior independently of Houmao admission.

## Native Dependency

The local source reference `67325c1b25e46b2fc66043bceab059221b719fa9` contains the browser assets for its own build. Its bundled composer sends ordinary prompts to `POST /sessions/{session_id}/prompts`. KAP resolves or resumes the session, prepares content, can apply model/profile changes, and calls `submit` regardless of the preceding idle snapshot. The generic scoped prompt service also queues when busy. The engine's quiescence guard pauses execution and permits queue insertion. These source observations and the installed native HTTP probe cover different builds. The installed-browser composer was outside this HTTP experiment.

The source checkout documents a native SEA build with pnpm `10.33.0` and Node `24.15.0` or newer. A separately maintained build could place a synchronous ready-only check and insertion at the common native loop boundary, qualify exact live-only scope lookup, and gate any asynchronous mutating preparation across submitters. The checkout version is `2.2.0`, and installing its stock executable would leave the same unconditional submission behavior. Positive Kimi Web qualification remains blocked on a qualifying native conditional operation or integration and the real browser versus gateway race.
