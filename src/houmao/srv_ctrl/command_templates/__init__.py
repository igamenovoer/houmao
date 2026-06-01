"""Code-first command-template registry and renderer."""

from .export import (
    export_command_template_yaml,
    export_command_templates_yaml,
    write_command_template_yaml,
    write_command_templates_yaml,
)
from .models import CommandTemplate, FieldAction, FieldConflict, TemplateField, ValueType
from .registry import (
    build_template_registry,
    get_command_template,
    list_command_templates,
    show_command_template,
)
from .rendering import load_render_intent, render_command_template

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
