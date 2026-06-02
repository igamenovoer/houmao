"""Command-template declarations for this command family."""

from __future__ import annotations

from ..builders import (
    _choice,
    _clear,
    _conflict,
    _f,
    _flag,
    _int,
    _many,
    _path,
    _req,
    _template,
)
from ..models import (
    CommandTemplate,
    _PROMPT_MODE_CHOICES,
    _TOOL_CHOICES,
)


def templates() -> list[CommandTemplate]:
    """Return native-agent internals command templates."""

    native_root_field = _f(
        "native_agent_root",
        "--native-agent-root",
        "Native-agent root for direct internal material.",
    )
    prompt_mode = _choice(
        "prompt_mode",
        "--prompt-mode",
        "Persist an explicit prompt mode.",
        _PROMPT_MODE_CHOICES,
        default_action="omit-to-inherit",
    )
    recipe_fields = (
        native_root_field,
        _req("name", "--name", "Recipe name."),
        _f("role", "--role", "Role name."),
        _choice("tool", "--tool", "Tool lane.", _TOOL_CHOICES),
        _f("setup", "--setup", "Tool setup name."),
        _f("auth", "--auth", "Credential bundle name."),
        _many("skill", "--skill", "Registered skill."),
        prompt_mode,
        _f("model", "--model", "Launch-owned model."),
        _int("reasoning_level", "--reasoning-level", "Launch-owned reasoning preset index."),
    )
    launch_dossier_fields = (
        native_root_field,
        _req("name", "--name", "Launch dossier name."),
        _f("recipe", "--recipe", "Source recipe name."),
        _f("agent_name", "--agent-name", "Default managed-agent name."),
        _f("agent_id", "--agent-id", "Default managed-agent id."),
        _f("workdir", "--workdir", "Default runtime workdir."),
        _f("auth", "--auth", "Default auth override."),
        _f("model", "--model", "Launch-owned model."),
        _int("reasoning_level", "--reasoning-level", "Launch-owned reasoning preset index."),
        prompt_mode,
        _many("env_set", "--env-set", "Persistent launch env record."),
        _choice(
            "mail_transport",
            "--mail-transport",
            "Declarative mailbox transport.",
            ("filesystem", "stalwart"),
        ),
        _f("mail_principal_id", "--mail-principal-id", "Declarative mailbox principal id."),
        _f("mail_address", "--mail-address", "Declarative mailbox address."),
        _f("mail_root", "--mail-root", "Declarative filesystem mailbox root."),
        _f("mail_base_url", "--mail-base-url", "Declarative Stalwart base URL."),
        _f("mail_jmap_url", "--mail-jmap-url", "Declarative Stalwart JMAP URL."),
        _f("mail_management_url", "--mail-management-url", "Declarative Stalwart management URL."),
        _flag(
            "headless",
            "--headless",
            "Persist headless launch posture.",
            default_action="omit-to-inherit",
        ),
        _flag("no_gateway", "--no-gateway", "Disable gateway auto-attach."),
        _int("gateway_port", "--gateway-port", "Gateway port."),
        _flag(
            "managed_header",
            "--managed-header",
            "Persist managed-header posture.",
            negative_option="--no-managed-header",
            default_action="omit-to-inherit",
        ),
        _many(
            "managed_header_section", "--managed-header-section", "Managed-header section policy."
        ),
        _choice(
            "prompt_overlay_mode",
            "--prompt-overlay-mode",
            "Prompt overlay mode.",
            ("append", "replace"),
        ),
        _f("prompt_overlay_text", "--prompt-overlay-text", "Prompt overlay text."),
        _path("prompt_overlay_file", "--prompt-overlay-file", "Prompt overlay file."),
        _f(
            "gateway_mail_notifier_appendix_text",
            "--gateway-mail-notifier-appendix-text",
            "Mail-notifier appendix.",
        ),
        _f("memo_seed_text", "--memo-seed-text", "Inline memo seed."),
        _path("memo_seed_file", "--memo-seed-file", "Memo seed file."),
        _path("memo_seed_dir", "--memo-seed-dir", "Memo seed directory."),
        _flag("yes", "--yes", "Confirm replacement."),
    )
    launch_dossier_clear_fields = (
        _clear("clear_agent_name", "--clear-agent-name", "agent_name"),
        _clear("clear_agent_id", "--clear-agent-id", "agent_id"),
        _clear("clear_workdir", "--clear-workdir", "workdir"),
        _clear("clear_auth", "--clear-auth", "auth"),
        _clear("clear_model", "--clear-model", "model"),
        _clear("clear_reasoning_level", "--clear-reasoning-level", "reasoning_level"),
        _clear("clear_prompt_mode", "--clear-prompt-mode", "prompt_mode"),
        _clear("clear_env", "--clear-env", "env_set"),
        _clear("clear_mailbox", "--clear-mailbox", "mailbox"),
        _clear("clear_headless", "--clear-headless", "headless"),
        _clear("clear_managed_header", "--clear-managed-header", "managed_header"),
        _many(
            "clear_managed_header_section",
            "--clear-managed-header-section",
            "Clear one managed-header section.",
        ),
        _clear(
            "clear_managed_header_sections",
            "--clear-managed-header-sections",
            "managed_header_section",
        ),
        _clear("clear_prompt_overlay", "--clear-prompt-overlay", "prompt_overlay"),
        _clear("clear_memo_seed", "--clear-memo-seed", "memo_seed"),
    )
    return [
        _template(
            "internals.native-agent.roles.init",
            ("internals", "native-agent", "roles", "init"),
            "Create one native-agent role prompt root.",
            (
                native_root_field,
                _req("name", "--name", "Role name."),
                _f("system_prompt", "--system-prompt", "Inline system prompt."),
                _path("system_prompt_file", "--system-prompt-file", "System prompt file."),
            ),
            family="internals.native-agent.roles",
            conflicts=(
                _conflict(
                    "system_prompt",
                    "system_prompt_file",
                    message="System prompt text and file are mutually exclusive.",
                ),
            ),
        ),
        _template(
            "internals.native-agent.roles.set",
            ("internals", "native-agent", "roles", "set"),
            "Patch one native-agent role prompt.",
            (
                native_root_field,
                _req("name", "--name", "Role name."),
                _f("system_prompt", "--system-prompt", "Inline system prompt."),
                _path("system_prompt_file", "--system-prompt-file", "System prompt file."),
                _clear("clear_system_prompt", "--clear-system-prompt", "system_prompt"),
            ),
            family="internals.native-agent.roles",
            conflicts=(
                _conflict(
                    "system_prompt",
                    "system_prompt_file",
                    "clear_system_prompt",
                    message="System prompt set and clear fields are mutually exclusive.",
                ),
            ),
        ),
        _template(
            "internals.native-agent.recipes.add",
            ("internals", "native-agent", "recipes", "add"),
            "Create one native-agent recipe.",
            recipe_fields,
            family="internals.native-agent.recipes",
            required_one_of=(("role",), ("tool",)),
        ),
        _template(
            "internals.native-agent.recipes.set",
            ("internals", "native-agent", "recipes", "set"),
            "Patch one native-agent recipe.",
            (
                *recipe_fields,
                _clear("clear_auth", "--clear-auth", "auth"),
                _many("add_skill", "--add-skill", "Add registered skill."),
                _many("remove_skill", "--remove-skill", "Remove registered skill."),
                _clear("clear_skills", "--clear-skills", "skills"),
                _clear("clear_prompt_mode", "--clear-prompt-mode", "prompt_mode"),
                _clear("clear_model", "--clear-model", "model"),
                _clear("clear_reasoning_level", "--clear-reasoning-level", "reasoning_level"),
            ),
            family="internals.native-agent.recipes",
            conflicts=(
                _conflict("auth", "clear_auth", message="Auth cannot be set and cleared."),
                _conflict(
                    "skill", "clear_skills", message="Skills cannot be replaced and cleared."
                ),
                _conflict(
                    "prompt_mode",
                    "clear_prompt_mode",
                    message="Prompt mode cannot be set and cleared.",
                ),
                _conflict("model", "clear_model", message="Model cannot be set and cleared."),
                _conflict(
                    "reasoning_level",
                    "clear_reasoning_level",
                    message="Reasoning level cannot be set and cleared.",
                ),
            ),
        ),
        _template(
            "internals.native-agent.launch-dossiers.add",
            ("internals", "native-agent", "launch-dossiers", "add"),
            "Create one recipe-backed native launch dossier.",
            launch_dossier_fields,
            family="internals.native-agent.launch-dossiers",
            conflicts=(
                _conflict(
                    "prompt_overlay_text",
                    "prompt_overlay_file",
                    message="Prompt overlay sources conflict.",
                ),
                _conflict(
                    "memo_seed_text",
                    "memo_seed_file",
                    "memo_seed_dir",
                    message="Memo seed sources are mutually exclusive.",
                ),
            ),
        ),
        _template(
            "internals.native-agent.launch-dossiers.set",
            ("internals", "native-agent", "launch-dossiers", "set"),
            "Patch one recipe-backed native launch dossier.",
            (*launch_dossier_fields, *launch_dossier_clear_fields),
            family="internals.native-agent.launch-dossiers",
            conflicts=(
                _conflict(
                    "prompt_mode",
                    "clear_prompt_mode",
                    message="Prompt mode cannot be set and cleared.",
                ),
                _conflict(
                    "headless",
                    "clear_headless",
                    message="Launch posture cannot be set and cleared.",
                ),
                _conflict(
                    "managed_header",
                    "clear_managed_header",
                    message="Managed header cannot be set and cleared.",
                ),
                _conflict(
                    "prompt_overlay_text",
                    "prompt_overlay_file",
                    "clear_prompt_overlay",
                    message="Prompt overlay text, file, and clear are mutually exclusive.",
                ),
                _conflict(
                    "memo_seed_text",
                    "memo_seed_file",
                    "memo_seed_dir",
                    "clear_memo_seed",
                    message="Memo seed text, file, directory, and clear are mutually exclusive.",
                ),
            ),
        ),
    ]
