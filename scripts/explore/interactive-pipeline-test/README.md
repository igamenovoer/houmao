# Interactive Pipeline Exploration

Prepare a selected Claude case with the shared helper, then pass its returned external run directory:

```bash
pixi run python scripts/agents/test-fixtures/fixture.py prepare --client claude --case cloud-api --model MODEL --env-file .env --mode tui --surface manager --role gpu-kernel-coder
scripts/explore/interactive-pipeline-test/interactive_pipeline_cao_claude.sh --run-dir /external/run
scripts/explore/interactive-pipeline-test/send_prompt.sh --run-dir /external/run --prompt 'Reply exactly OK'
pixi run python scripts/agents/test-fixtures/fixture.py stop --run-dir /external/run
```

The retained launcher filename now delegates to the maintained project manager. Select `self-hosted` for another declared compatible endpoint, or explicitly imported `native-login` state for a vendor smoke. No model/account or CAO server is selected implicitly. Keys, generated homes, and runtime evidence remain in the private external run. See [the helper](../../agents/test-fixtures/README.md).
