# Houmao Docs

This repository is the canonical documentation home for the extracted runtime subsystem.

## Developer

For the maintained CAO `shadow_only` parser/runtime contract and lifecycle semantics, start here.

- [TUI Parsing Developer Guide](developer/tui-parsing/index.md)
- [Terminal Recorder Developer Guide](developer/terminal-record/index.md)
- [Houmao Server Developer Guide](developer/houmao-server/index.md)

## Reference

- [Houmao server pair and managed-agent workflows](reference/houmao_server_pair.md)
- [Runtime CLI and session workflows](reference/realm_controller.md)
- [Runtime-managed agents reference](reference/agents/index.md)
- [Terminal recorder](reference/terminal_record.md)
- [Mailbox reference](reference/mailbox/index.md)
- [Mailbox roundtrip tutorial pack](../scripts/demo/mailbox-roundtrip-tutorial-pack/README.md)
- [Houmao-server interactive full-pipeline demo pack](../scripts/demo/houmao-server-interactive-full-pipeline-demo/README.md)
- [Interactive CAO demo retirement note](reference/cao_interactive_demo.md)
- [Brain builder and component library layout](reference/agents_brains.md)
- [CAO server launcher](reference/cao_server_launcher.md)
- [CAO shadow parsing](reference/cao_claude_shadow_parsing.md)
- [CAO shadow troubleshooting](reference/cao_shadow_parser_troubleshooting.md)
- [CLI reference](reference/cli.md)

If you already have a Claude Code, Codex, or Gemini tmux session running and want Houmao to manage it without relaunching it, start with `houmao-mgr agents join` in [Houmao Server Pair](reference/houmao_server_pair.md).

## Migration

- [Runtime migration parity checklist](migration/runtime_migration_parity_checklist.md)
- [Runtime migration report](migration/runtime_migration_report.md)
