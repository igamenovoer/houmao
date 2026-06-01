"""Compatibility wrapper for command-template registry helpers."""

from __future__ import annotations

from houmao.srv_ctrl.command_templates import (
    CommandTemplate,
    FieldAction,
    FieldConflict,
    TemplateField,
    ValueType,
    build_template_registry,
    export_command_template_yaml,
    export_command_templates_yaml,
    get_command_template,
    list_command_templates,
    load_render_intent,
    render_command_template,
    show_command_template,
    write_command_template_yaml,
    write_command_templates_yaml,
)

__all__ = [
    "CommandTemplate",
    "FieldAction",
    "FieldConflict",
    "TemplateField",
    "ValueType",
    "build_template_registry",
    "export_command_template_yaml",
    "export_command_templates_yaml",
    "get_command_template",
    "list_command_templates",
    "load_render_intent",
    "render_command_template",
    "show_command_template",
    "write_command_template_yaml",
    "write_command_templates_yaml",
]
