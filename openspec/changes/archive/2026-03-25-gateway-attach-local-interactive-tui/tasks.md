## 1. Runtime attach eligibility

- [x] 1.1 Update the runtime gateway attach admission path so runtime-owned `local_interactive` sessions are treated as supported tmux-backed backends when a gateway execution adapter exists, and keep unsupported-backend failure text truthful for the backends that remain unsupported.
- [x] 1.2 Replace or clarify the local gateway adapter contract so it explicitly covers both runtime-owned native headless sessions and runtime-owned `local_interactive` sessions without requiring a rename, and make local runtime type assumptions plus tmux-unavailable wording explicit and backend-neutral.

## 2. Local gateway execution behavior

- [x] 2.1 Ensure gateway status for an attached runtime-owned `local_interactive` session reports a live attached gateway instead of an unsupported-backend or permanently unavailable posture.
- [x] 2.2 Ensure gateway-managed `submit_prompt` and `interrupt` requests are dispatched through resumed `local_interactive` runtime authority rather than bypassing the gateway path.

## 3. Validation and documentation

- [x] 3.1 Add regression coverage for gateway attach, status, prompt, and interrupt on runtime-owned `local_interactive` sessions in the relevant unit and integration suites, reusing existing gateway test infrastructure where practical and introducing a dedicated local-interactive seed helper when persisted local-interactive resume state must be exercised.
- [x] 3.2 Update operator-facing docs or help text to describe gateway control support for serverless local interactive agents and to keep unsupported-backend failures explicit for backends that still lack adapters.
