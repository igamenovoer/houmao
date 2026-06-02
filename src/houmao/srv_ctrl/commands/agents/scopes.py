"""Click helpers for scoped managed-agent command surfaces."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import copy
from typing import Any

import click


CommandInjectionFactory = Callable[[], Mapping[str, Any]]


def clone_scoped_command_tree(
    command: click.Command,
    *,
    remove_params: frozenset[str],
    inject_params: CommandInjectionFactory,
) -> click.Command:
    """Clone one command tree with selected public parameters removed and injected."""

    if isinstance(command, click.Group):
        cloned_group = click.Group(
            name=command.name,
            context_settings=command.context_settings,
            callback=_clone_callback(
                command=command,
                removed_param_names=_removed_param_names(command.params, remove_params),
                inject_params=inject_params,
            )
            if command.callback is not None
            else None,
            params=_clone_params(command.params, remove_params),
            help=command.help,
            epilog=command.epilog,
            short_help=command.short_help,
            options_metavar=command.options_metavar,
            add_help_option=command.add_help_option,
            no_args_is_help=command.no_args_is_help,
            hidden=command.hidden,
            deprecated=command.deprecated,
            invoke_without_command=command.invoke_without_command,
            subcommand_metavar=command.subcommand_metavar,
            chain=command.chain,
        )
        for name, child in command.commands.items():
            cloned_group.add_command(
                clone_scoped_command_tree(
                    child,
                    remove_params=remove_params,
                    inject_params=inject_params,
                ),
                name=name,
            )
        return cloned_group

    removed_param_names = _removed_param_names(command.params, remove_params)
    return click.Command(
        name=command.name,
        context_settings=command.context_settings,
        callback=_clone_callback(
            command=command,
            removed_param_names=removed_param_names,
            inject_params=inject_params,
        ),
        params=_clone_params(command.params, remove_params),
        help=command.help,
        epilog=command.epilog,
        short_help=command.short_help,
        options_metavar=command.options_metavar,
        add_help_option=command.add_help_option,
        no_args_is_help=command.no_args_is_help,
        hidden=command.hidden,
        deprecated=command.deprecated,
    )


def _clone_params(
    params: list[click.Parameter],
    remove_params: frozenset[str],
) -> list[click.Parameter]:
    """Return copied Click parameters except those removed by scoped wrapping."""

    return [copy.copy(param) for param in params if param.name not in remove_params]


def _removed_param_names(
    params: list[click.Parameter],
    remove_params: frozenset[str],
) -> frozenset[str]:
    """Return callback parameter names removed from the cloned command."""

    return frozenset(param.name for param in params if param.name in remove_params)


def _clone_callback(
    *,
    command: click.Command,
    removed_param_names: frozenset[str],
    inject_params: CommandInjectionFactory,
) -> Callable[..., Any]:
    """Build one callback that restores removed parameters before delegation."""

    def _callback(**kwargs: Any) -> Any:
        merged_kwargs = dict(kwargs)
        for name, value in inject_params().items():
            if name in removed_param_names:
                merged_kwargs[name] = value
        if command.callback is None:
            return None
        return command.callback(**merged_kwargs)

    _callback.__name__ = f"scoped_{command.name or 'command'}"
    _callback.__doc__ = command.callback.__doc__ if command.callback is not None else command.help
    return _callback
