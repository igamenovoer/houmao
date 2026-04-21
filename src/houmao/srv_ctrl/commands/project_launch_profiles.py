"""Project-scoped explicit launch-profile commands."""

from __future__ import annotations

# ruff: noqa: F403,F405
from .project_common import *


@click.group(name="launch-profiles")
def project_launch_profiles_group() -> None:
    """Manage recipe-backed reusable launch profiles stored under `.houmao/agents/launch-profiles/`."""


@project_launch_profiles_group.command(name="list")
@click.option("--recipe", default=None, help="Optional source recipe filter.")
@click.option(
    "--tool",
    "tool_name",
    default=None,
    type=click.Choice(_SUPPORTED_PROJECT_TOOLS),
    help="Optional tool filter.",
)
def list_project_launch_profiles_command(recipe: str | None, tool_name: str | None) -> None:
    """List project-local named launch profiles."""

    overlay = _resolve_existing_project_overlay()
    launch_profiles = _list_launch_profile_payloads(
        overlay=overlay,
        source_recipe=_optional_non_empty_value(recipe),
        tool=tool_name,
    )
    payload: dict[str, object] = {
        "project_root": str(overlay.project_root),
        "launch_profiles": launch_profiles,
    }
    if not launch_profiles:
        easy_profile_count = sum(
            1
            for resolved in list_resolved_launch_profiles(overlay=overlay)
            if resolved.entry.profile_lane == "easy_profile"
            and (tool_name is None or resolved.tool == tool_name)
        )
        if easy_profile_count > 0:
            profile_label = "profile" if easy_profile_count == 1 else "profiles"
            payload["note"] = (
                "No explicit launch profiles found for this query. "
                f"Found {easy_profile_count} easy {profile_label} in this overlay; use "
                "`houmao-mgr project easy profile list`."
            )
    emit(payload)


@project_launch_profiles_group.command(name="get")
@click.option("--name", required=True, help="Launch profile name.")
def get_project_launch_profile_command(name: str) -> None:
    """Inspect one project-local named launch profile."""

    overlay = _resolve_existing_project_overlay()
    emit(
        _launch_profile_payload(
            overlay=overlay,
            profile_name=_require_non_empty_name(name, field_name="--name"),
            expected_lane="launch_profile",
            action="get",
        )
    )


@project_launch_profiles_group.command(name="add")
@click.option("--name", required=True, help="Launch profile name.")
@click.option("--recipe", required=True, help="Source recipe name.")
@click.option("--agent-name", default=None, help="Optional default managed-agent name.")
@click.option("--agent-id", default=None, help="Optional default managed-agent id.")
@click.option("--workdir", default=None, help="Optional default working directory.")
@click.option("--auth", default=None, help="Optional default auth bundle override.")
@click.option("--model", default=None, help="Optional launch-owned model override.")
@click.option(
    "--reasoning-level",
    type=click.IntRange(min=0),
    default=None,
    help="Optional launch-owned tool/model-specific reasoning preset index override (>=0).",
)
@click.option(
    "--prompt-mode",
    type=click.Choice(("unattended", "as_is")),
    default=None,
    help="Optional default operator prompt mode.",
)
@click.option(
    "--env-set",
    "env_set",
    multiple=True,
    help="Repeatable persistent launch env record (`NAME=value`).",
)
@click.option(
    "--mail-transport",
    type=click.Choice(("filesystem", "stalwart")),
    default=None,
    help="Optional declarative mailbox transport.",
)
@click.option(
    "--mail-principal-id", default=None, help="Optional declarative mailbox principal id."
)
@click.option("--mail-address", default=None, help="Optional declarative mailbox address.")
@click.option("--mail-root", default=None, help="Optional declarative filesystem mailbox root.")
@click.option("--mail-base-url", default=None, help="Optional declarative Stalwart base URL.")
@click.option("--mail-jmap-url", default=None, help="Optional declarative Stalwart JMAP URL.")
@click.option(
    "--mail-management-url",
    default=None,
    help="Optional declarative Stalwart management URL.",
)
@click.option("--headless", is_flag=True, help="Persist headless launch as the default posture.")
@click.option("--no-gateway", is_flag=True, help="Persist gateway auto-attach disabled.")
@click.option(
    "--managed-header/--no-managed-header",
    "managed_header",
    default=None,
    help="Persist managed prompt header policy for launches from this profile.",
)
@click.option(
    "--managed-header-section",
    "managed_header_section",
    multiple=True,
    metavar="SECTION=STATE",
    help="Persist one managed-header section policy (`enabled` or `disabled`).",
)
@click.option(
    "--gateway-port",
    type=click.IntRange(1, 65535),
    default=None,
    help="Persist one fixed loopback gateway port for launches from this profile.",
)
@click.option(
    "--relaunch-chat-session-mode",
    type=click.Choice(_RELAUNCH_CHAT_SESSION_MODES),
    default=None,
    help="Persist relaunch chat-session policy: new, tool_last_or_new, or exact.",
)
@click.option(
    "--relaunch-chat-session-id",
    default=None,
    help="Persist provider chat-session id for relaunch when mode is exact.",
)
@click.option(
    "--prompt-overlay-mode",
    type=click.Choice(("append", "replace")),
    default=None,
    help="Optional prompt-overlay mode.",
)
@click.option("--prompt-overlay-text", default=None, help="Inline prompt-overlay text.")
@click.option(
    "--prompt-overlay-file",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default=None,
    help="Path to a prompt-overlay text file.",
)
@click.option(
    "--gateway-mail-notifier-appendix-text",
    default=None,
    help="Default runtime guidance appended to mail-notifier prompts for launches from this profile.",
)
@click.option("--memo-seed-text", default=None, help="Inline launch-profile memo seed text.")
@click.option(
    "--memo-seed-file",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default=None,
    help="Path to a Markdown memo-seed file.",
)
@click.option(
    "--memo-seed-dir",
    type=click.Path(path_type=Path, exists=True, file_okay=False, dir_okay=True),
    default=None,
    help="Path to a memo-shaped seed directory containing `houmao-memo.md` and/or `pages/`.",
)
@overwrite_confirm_option
def add_project_launch_profile_command(
    name: str,
    recipe: str,
    agent_name: str | None,
    agent_id: str | None,
    workdir: str | None,
    auth: str | None,
    model: str | None,
    reasoning_level: int | None,
    prompt_mode: str | None,
    env_set: tuple[str, ...],
    mail_transport: str | None,
    mail_principal_id: str | None,
    mail_address: str | None,
    mail_root: str | None,
    mail_base_url: str | None,
    mail_jmap_url: str | None,
    mail_management_url: str | None,
    headless: bool,
    no_gateway: bool,
    managed_header: bool | None,
    managed_header_section: tuple[str, ...],
    gateway_port: int | None,
    relaunch_chat_session_mode: str | None,
    relaunch_chat_session_id: str | None,
    prompt_overlay_mode: str | None,
    prompt_overlay_text: str | None,
    prompt_overlay_file: Path | None,
    gateway_mail_notifier_appendix_text: str | None,
    memo_seed_text: str | None,
    memo_seed_file: Path | None,
    memo_seed_dir: Path | None,
    yes: bool,
) -> None:
    """Create one recipe-backed explicit launch profile."""

    overlay = _ensure_project_overlay()
    profile_name = _require_non_empty_name(name, field_name="--name")
    payload = _store_launch_profile_from_cli(
        overlay=overlay,
        profile_name=profile_name,
        profile_lane="launch_profile",
        source_kind="recipe",
        source_name=_require_non_empty_name(recipe, field_name="--recipe"),
        operation=_resolve_launch_profile_create_operation_or_click(
            overlay=overlay,
            profile_name=profile_name,
            profile_lane="launch_profile",
            yes=yes,
        ),
        agent_name=agent_name,
        agent_id=agent_id,
        workdir=workdir,
        auth=auth,
        model=model,
        reasoning_level=reasoning_level,
        prompt_mode=prompt_mode,
        env_set=env_set,
        mail_transport=mail_transport,
        mail_principal_id=mail_principal_id,
        mail_address=mail_address,
        mail_root=mail_root,
        mail_base_url=mail_base_url,
        mail_jmap_url=mail_jmap_url,
        mail_management_url=mail_management_url,
        headless=headless,
        clear_headless=False,
        no_gateway=no_gateway,
        managed_header=managed_header,
        clear_managed_header=False,
        managed_header_section=managed_header_section,
        clear_managed_header_section=(),
        clear_managed_header_sections=False,
        gateway_port=gateway_port,
        relaunch_chat_session_mode=relaunch_chat_session_mode,
        relaunch_chat_session_id=relaunch_chat_session_id,
        clear_relaunch_chat_session=False,
        prompt_overlay_mode=prompt_overlay_mode,
        prompt_overlay_text=prompt_overlay_text,
        prompt_overlay_file=prompt_overlay_file,
        clear_prompt_overlay=False,
        memo_seed_text=memo_seed_text,
        memo_seed_file=memo_seed_file,
        memo_seed_dir=memo_seed_dir,
        clear_memo_seed=False,
        gateway_mail_notifier_appendix_text=gateway_mail_notifier_appendix_text,
        clear_gateway_mail_notifier_appendix=False,
        clear_mailbox=False,
        clear_env=False,
        clear_agent_name=False,
        clear_agent_id=False,
        clear_workdir=False,
        clear_auth=False,
        clear_model=False,
        clear_reasoning_level=False,
        clear_prompt_mode=False,
    )
    emit(payload)


@project_launch_profiles_group.command(name="set")
@click.option("--name", required=True, help="Launch profile name.")
@click.option("--agent-name", default=None, help="Optional default managed-agent name override.")
@click.option(
    "--clear-agent-name", is_flag=True, help="Clear the stored default managed-agent name."
)
@click.option("--agent-id", default=None, help="Optional default managed-agent id override.")
@click.option("--clear-agent-id", is_flag=True, help="Clear the stored default managed-agent id.")
@click.option("--workdir", default=None, help="Optional default working directory override.")
@click.option("--clear-workdir", is_flag=True, help="Clear the stored default working directory.")
@click.option("--auth", default=None, help="Optional default auth bundle override.")
@click.option("--clear-auth", is_flag=True, help="Clear the stored auth override.")
@click.option("--model", default=None, help="Optional launch-owned model override.")
@click.option("--clear-model", is_flag=True, help="Clear the stored launch-owned model.")
@click.option(
    "--reasoning-level",
    type=click.IntRange(min=0),
    default=None,
    help="Optional launch-owned tool/model-specific reasoning preset index override (>=0).",
)
@click.option(
    "--clear-reasoning-level",
    is_flag=True,
    help="Clear the stored launch-owned reasoning level.",
)
@click.option(
    "--prompt-mode",
    type=click.Choice(("unattended", "as_is")),
    default=None,
    help="Optional default operator prompt mode override.",
)
@click.option("--clear-prompt-mode", is_flag=True, help="Clear the stored operator prompt mode.")
@click.option(
    "--env-set",
    "env_set",
    multiple=True,
    help="Repeatable persistent launch env record replacement (`NAME=value`).",
)
@click.option("--clear-env", is_flag=True, help="Clear stored persistent launch env records.")
@click.option(
    "--mail-transport",
    type=click.Choice(("filesystem", "stalwart")),
    default=None,
    help="Optional declarative mailbox transport override.",
)
@click.option(
    "--mail-principal-id", default=None, help="Optional declarative mailbox principal id."
)
@click.option("--mail-address", default=None, help="Optional declarative mailbox address.")
@click.option("--mail-root", default=None, help="Optional declarative filesystem mailbox root.")
@click.option("--mail-base-url", default=None, help="Optional declarative Stalwart base URL.")
@click.option("--mail-jmap-url", default=None, help="Optional declarative Stalwart JMAP URL.")
@click.option(
    "--mail-management-url",
    default=None,
    help="Optional declarative Stalwart management URL.",
)
@click.option(
    "--clear-mailbox", is_flag=True, help="Clear the stored declarative mailbox defaults."
)
@click.option("--headless", is_flag=True, help="Persist headless launch as the default posture.")
@click.option("--clear-headless", is_flag=True, help="Clear the stored headless launch posture.")
@click.option("--no-gateway", is_flag=True, help="Persist gateway auto-attach disabled.")
@click.option(
    "--managed-header/--no-managed-header",
    "managed_header",
    default=None,
    help="Persist managed prompt header policy for launches from this profile.",
)
@click.option(
    "--clear-managed-header",
    is_flag=True,
    help="Clear the stored managed prompt header policy back to inherit.",
)
@click.option(
    "--managed-header-section",
    "managed_header_section",
    multiple=True,
    metavar="SECTION=STATE",
    help="Persist or replace one managed-header section policy (`enabled` or `disabled`).",
)
@click.option(
    "--clear-managed-header-section",
    "clear_managed_header_section",
    multiple=True,
    metavar="SECTION",
    help="Clear one stored managed-header section policy entry.",
)
@click.option(
    "--clear-managed-header-sections",
    is_flag=True,
    help="Clear all stored managed-header section policy entries.",
)
@click.option(
    "--gateway-port",
    type=click.IntRange(1, 65535),
    default=None,
    help="Persist one fixed loopback gateway port for launches from this profile.",
)
@click.option(
    "--relaunch-chat-session-mode",
    type=click.Choice(_RELAUNCH_CHAT_SESSION_MODES),
    default=None,
    help="Persist relaunch chat-session policy override: new, tool_last_or_new, or exact.",
)
@click.option(
    "--relaunch-chat-session-id",
    default=None,
    help="Persist provider chat-session id for relaunch when mode is exact.",
)
@click.option(
    "--clear-relaunch-chat-session",
    is_flag=True,
    help="Clear the stored relaunch chat-session policy.",
)
@click.option(
    "--prompt-overlay-mode",
    type=click.Choice(("append", "replace")),
    default=None,
    help="Optional prompt-overlay mode override.",
)
@click.option("--prompt-overlay-text", default=None, help="Inline prompt-overlay text override.")
@click.option(
    "--prompt-overlay-file",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default=None,
    help="Path to a prompt-overlay text file.",
)
@click.option("--clear-prompt-overlay", is_flag=True, help="Clear the stored prompt overlay.")
@click.option(
    "--gateway-mail-notifier-appendix-text",
    default=None,
    help="Default runtime guidance appended to mail-notifier prompts for launches from this profile.",
)
@click.option(
    "--clear-gateway-mail-notifier-appendix",
    is_flag=True,
    help="Clear the stored mail-notifier appendix default.",
)
@click.option("--memo-seed-text", default=None, help="Inline launch-profile memo seed text.")
@click.option(
    "--memo-seed-file",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default=None,
    help="Path to a Markdown memo-seed file.",
)
@click.option(
    "--memo-seed-dir",
    type=click.Path(path_type=Path, exists=True, file_okay=False, dir_okay=True),
    default=None,
    help="Path to a memo-shaped seed directory containing `houmao-memo.md` and/or `pages/`.",
)
@click.option("--clear-memo-seed", is_flag=True, help="Clear the stored memo seed.")
def set_project_launch_profile_command(
    name: str,
    agent_name: str | None,
    clear_agent_name: bool,
    agent_id: str | None,
    clear_agent_id: bool,
    workdir: str | None,
    clear_workdir: bool,
    auth: str | None,
    clear_auth: bool,
    model: str | None,
    clear_model: bool,
    reasoning_level: int | None,
    clear_reasoning_level: bool,
    prompt_mode: str | None,
    clear_prompt_mode: bool,
    env_set: tuple[str, ...],
    clear_env: bool,
    mail_transport: str | None,
    mail_principal_id: str | None,
    mail_address: str | None,
    mail_root: str | None,
    mail_base_url: str | None,
    mail_jmap_url: str | None,
    mail_management_url: str | None,
    clear_mailbox: bool,
    headless: bool,
    clear_headless: bool,
    no_gateway: bool,
    managed_header: bool | None,
    clear_managed_header: bool,
    managed_header_section: tuple[str, ...],
    clear_managed_header_section: tuple[str, ...],
    clear_managed_header_sections: bool,
    gateway_port: int | None,
    relaunch_chat_session_mode: str | None,
    relaunch_chat_session_id: str | None,
    clear_relaunch_chat_session: bool,
    prompt_overlay_mode: str | None,
    prompt_overlay_text: str | None,
    prompt_overlay_file: Path | None,
    clear_prompt_overlay: bool,
    gateway_mail_notifier_appendix_text: str | None,
    clear_gateway_mail_notifier_appendix: bool,
    memo_seed_text: str | None,
    memo_seed_file: Path | None,
    memo_seed_dir: Path | None,
    clear_memo_seed: bool,
) -> None:
    """Update one recipe-backed explicit launch profile."""

    overlay = _ensure_project_overlay()
    profile_name = _require_non_empty_name(name, field_name="--name")
    payload = _store_launch_profile_from_cli(
        overlay=overlay,
        profile_name=profile_name,
        profile_lane="launch_profile",
        source_kind="recipe",
        source_name=_load_launch_profile_or_click(
            overlay=overlay,
            name=profile_name,
            expected_lane="launch_profile",
            action="set",
        ).entry.source_name,
        operation="patch",
        agent_name=agent_name,
        agent_id=agent_id,
        workdir=workdir,
        auth=auth,
        model=model,
        reasoning_level=reasoning_level,
        prompt_mode=prompt_mode,
        env_set=env_set,
        mail_transport=mail_transport,
        mail_principal_id=mail_principal_id,
        mail_address=mail_address,
        mail_root=mail_root,
        mail_base_url=mail_base_url,
        mail_jmap_url=mail_jmap_url,
        mail_management_url=mail_management_url,
        headless=headless,
        clear_headless=clear_headless,
        no_gateway=no_gateway,
        managed_header=managed_header,
        clear_managed_header=clear_managed_header,
        managed_header_section=managed_header_section,
        clear_managed_header_section=clear_managed_header_section,
        clear_managed_header_sections=clear_managed_header_sections,
        gateway_port=gateway_port,
        relaunch_chat_session_mode=relaunch_chat_session_mode,
        relaunch_chat_session_id=relaunch_chat_session_id,
        clear_relaunch_chat_session=clear_relaunch_chat_session,
        prompt_overlay_mode=prompt_overlay_mode,
        prompt_overlay_text=prompt_overlay_text,
        prompt_overlay_file=prompt_overlay_file,
        clear_prompt_overlay=clear_prompt_overlay,
        memo_seed_text=memo_seed_text,
        memo_seed_file=memo_seed_file,
        memo_seed_dir=memo_seed_dir,
        clear_memo_seed=clear_memo_seed,
        gateway_mail_notifier_appendix_text=gateway_mail_notifier_appendix_text,
        clear_gateway_mail_notifier_appendix=clear_gateway_mail_notifier_appendix,
        clear_mailbox=clear_mailbox,
        clear_env=clear_env,
        clear_agent_name=clear_agent_name,
        clear_agent_id=clear_agent_id,
        clear_workdir=clear_workdir,
        clear_auth=clear_auth,
        clear_model=clear_model,
        clear_reasoning_level=clear_reasoning_level,
        clear_prompt_mode=clear_prompt_mode,
    )
    emit(payload)


@project_launch_profiles_group.command(name="remove")
@click.option("--name", required=True, help="Launch profile name.")
def remove_project_launch_profile_command(name: str) -> None:
    """Remove one project-local named launch profile."""

    overlay = _resolve_existing_project_overlay()
    profile_name = _require_non_empty_name(name, field_name="--name")
    _load_launch_profile_or_click(
        overlay=overlay,
        name=profile_name,
        expected_lane="launch_profile",
        action="remove",
    )
    try:
        metadata_path = ProjectCatalog.from_overlay(overlay).remove_launch_profile(profile_name)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    emit(
        {
            "project_root": str(overlay.project_root),
            "name": profile_name,
            "removed": True,
            "metadata_path": str(metadata_path),
            "path": str(
                (overlay.agents_root / "launch-profiles" / f"{profile_name}.yaml").resolve()
            ),
        }
    )
