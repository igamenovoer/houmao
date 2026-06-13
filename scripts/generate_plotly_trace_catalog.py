#!/usr/bin/env python3
"""Generate the Houmao Plotly 2D trace catalog artifacts."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from pathlib import Path
from pprint import pformat
import json
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "extern/orphan/plotly.js/dist/plot-schema.json"
PYTHON_OUTPUT = REPO_ROOT / "src/houmao/ag_ui/plotly_trace_catalog.py"
TYPESCRIPT_OUTPUT = REPO_ROOT / "apps/ag-ui-workbench/src/ag-ui/plotlyTraceCatalog.ts"

EXCLUDED_CATEGORY = "gl3d"
GLOBAL_REJECTED_FIELDS = (
    "*src",
    "stream",
    "transform",
    "transforms",
    "frame",
    "frames",
    "template",
    "templates",
    "html",
    "iframe",
    "javascript",
    "script",
    "svg",
    "accesstoken",
)

DATA_ROOTS = frozenset(
    {
        "a",
        "b",
        "cells",
        "close",
        "dimensions",
        "header",
        "high",
        "ids",
        "lat",
        "labels",
        "link",
        "locations",
        "lon",
        "low",
        "node",
        "open",
        "parents",
        "r",
        "source",
        "target",
        "theta",
        "text",
        "value",
        "values",
        "x",
        "y",
        "z",
    }
)

STYLE_ROOTS = frozenset(
    {
        "alignmentgroup",
        "arrangement",
        "autocolorscale",
        "box",
        "boxmean",
        "boxpoints",
        "coloraxis",
        "colorbar",
        "colorscale",
        "connectgaps",
        "contours",
        "domain",
        "fill",
        "fillcolor",
        "hoverinfo",
        "hoverlabel",
        "hovermode",
        "hoveron",
        "hovertemplate",
        "insidetextfont",
        "line",
        "marker",
        "meanline",
        "mode",
        "opacity",
        "orientation",
        "outsidetextfont",
        "selected",
        "selectedpoints",
        "showlegend",
        "showscale",
        "textfont",
        "textinfo",
        "textposition",
        "texttemplate",
        "type",
        "visible",
        "zauto",
        "zmax",
        "zmid",
        "zmin",
        "zsmooth",
    }
)

SCHEMA_METADATA_KEYS = frozenset(
    {
        "_deprecated",
        "arrayOk",
        "description",
        "dflt",
        "editType",
        "flags",
        "impliedEdits",
        "items",
        "max",
        "min",
        "role",
        "values",
        "valType",
    }
)

SPECIAL_DATA_PATHS: dict[str, tuple[str, ...]] = {
    "barpolar": ("r", "theta"),
    "candlestick": ("x", "open", "high", "low", "close"),
    "carpet": ("a", "b", "y"),
    "choropleth": ("locations", "z"),
    "choroplethmap": ("locations", "z"),
    "choroplethmapbox": ("locations", "z"),
    "densitymap": ("lat", "lon", "z"),
    "densitymapbox": ("lat", "lon", "z"),
    "funnelarea": ("labels", "values"),
    "heatmap": ("z", "x", "y"),
    "histogram": ("x", "y"),
    "histogram2d": ("x", "y", "z"),
    "histogram2dcontour": ("x", "y", "z"),
    "icicle": ("labels", "parents", "values"),
    "indicator": ("value",),
    "ohlc": ("x", "open", "high", "low", "close"),
    "parcats": ("dimensions",),
    "parcoords": ("dimensions",),
    "pie": ("labels", "values"),
    "sankey": ("node.label", "link.source", "link.target", "link.value"),
    "scattercarpet": ("a", "b"),
    "scattergeo": ("lat", "lon"),
    "scattermap": ("lat", "lon"),
    "scattermapbox": ("lat", "lon"),
    "scatterpolar": ("r", "theta"),
    "scatterpolargl": ("r", "theta"),
    "scattersmith": ("real", "imag"),
    "scatterternary": ("a", "b", "c"),
    "splom": ("dimensions",),
    "sunburst": ("labels", "parents", "values"),
    "table": ("header.values", "cells.values"),
    "treemap": ("labels", "parents", "values"),
}

EXAMPLE_BY_TRACE: dict[str, dict[str, Any]] = {
    "bar": {"data": {"x": ["passed", "failed"], "y": [42, 2]}},
    "barpolar": {"data": {"r": [1, 2, 3], "theta": [0, 60, 120]}},
    "box": {"data": {"y": [1, 2, 2, 3, 5]}},
    "candlestick": {
        "data": {
            "x": ["2026-01-01", "2026-01-02"],
            "open": [10, 12],
            "high": [13, 14],
            "low": [9, 11],
            "close": [12, 13],
        }
    },
    "carpet": {"data": {"a": [1, 2, 3], "b": [1, 2, 3], "y": [1, 2, 3]}},
    "choropleth": {"data": {"locations": ["USA", "CAN"], "z": [1, 2]}},
    "choroplethmap": {"data": {"locations": ["USA", "CAN"], "z": [1, 2]}},
    "choroplethmapbox": {"data": {"locations": ["USA", "CAN"], "z": [1, 2]}},
    "contour": {"data": {"z": [[1, 2], [3, 4]]}},
    "contourcarpet": {"data": {"a": [1, 2], "b": [1, 2], "z": [1, 2]}},
    "densitymap": {"data": {"lat": [37.78, 37.79], "lon": [-122.42, -122.41], "z": [1, 2]}},
    "densitymapbox": {"data": {"lat": [37.78, 37.79], "lon": [-122.42, -122.41], "z": [1, 2]}},
    "funnel": {"data": {"y": ["lead", "trial", "paid"], "x": [100, 60, 25]}},
    "funnelarea": {"data": {"labels": ["lead", "trial", "paid"], "values": [100, 60, 25]}},
    "heatmap": {"data": {"z": [[1, 2], [3, 4]]}},
    "histogram": {"data": {"x": [1, 1, 2, 3, 3, 3]}},
    "histogram2d": {"data": {"x": [1, 2, 3], "y": [3, 2, 1]}},
    "histogram2dcontour": {"data": {"x": [1, 2, 3], "y": [3, 2, 1]}},
    "icicle": {"data": {"labels": ["all", "api"], "parents": ["", "all"], "values": [2, 1]}},
    "image": {"data": {"z": [[[255, 0, 0], [0, 255, 0]], [[0, 0, 255], [255, 255, 0]]]}},
    "indicator": {"data": {"value": 42}},
    "ohlc": {
        "data": {
            "x": ["2026-01-01", "2026-01-02"],
            "open": [10, 12],
            "high": [13, 14],
            "low": [9, 11],
            "close": [12, 13],
        }
    },
    "parcats": {
        "data": {"dimensions": [{"label": "status", "values": ["queued", "done"]}]}
    },
    "parcoords": {"data": {"dimensions": [{"label": "latency", "values": [91, 107]}]}},
    "pie": {"data": {"labels": ["A", "B"], "values": [60, 40]}},
    "sankey": {
        "data": {
            "node": {"label": ["start", "end"]},
            "link": {"source": [0], "target": [1], "value": [3]},
        }
    },
    "scatter": {"data": {"x": [1, 2, 3], "y": [3, 2, 4]}, "style": {"mode": "markers"}},
    "scattercarpet": {"data": {"a": [1, 2, 3], "b": [1, 2, 3]}},
    "scattergeo": {"data": {"lat": [37.78, 40.71], "lon": [-122.42, -74.0]}},
    "scattergl": {"data": {"x": [1, 2, 3], "y": [3, 2, 4]}, "style": {"mode": "markers"}},
    "scattermap": {"data": {"lat": [37.78, 40.71], "lon": [-122.42, -74.0]}},
    "scattermapbox": {"data": {"lat": [37.78, 40.71], "lon": [-122.42, -74.0]}},
    "scatterpolar": {"data": {"r": [1, 2, 3], "theta": [0, 60, 120]}},
    "scatterpolargl": {"data": {"r": [1, 2, 3], "theta": [0, 60, 120]}},
    "scattersmith": {"data": {"real": [0.1, 0.2], "imag": [0.3, 0.4]}},
    "scatterternary": {"data": {"a": [0.2, 0.3], "b": [0.3, 0.3], "c": [0.5, 0.4]}},
    "splom": {"data": {"dimensions": [{"label": "x", "values": [1, 2, 3]}]}},
    "sunburst": {"data": {"labels": ["all", "api"], "parents": ["", "all"], "values": [2, 1]}},
    "table": {"data": {"header": {"values": [["Status"]]}, "cells": {"values": [["ready"]]}}},
    "treemap": {"data": {"labels": ["all", "api"], "parents": ["", "all"], "values": [2, 1]}},
    "violin": {"data": {"y": [1, 2, 2, 3, 5]}},
    "waterfall": {"data": {"x": ["start", "delta", "end"], "y": [10, 3, 13]}},
}


def main() -> int:
    """Generate or verify Plotly trace catalog artifacts."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if generated outputs differ")
    args = parser.parse_args()

    catalog = build_catalog(load_schema(SCHEMA_PATH))
    outputs = {
        PYTHON_OUTPUT: render_python(catalog),
        TYPESCRIPT_OUTPUT: render_typescript(catalog),
    }
    if args.check:
        mismatches = [path for path, content in outputs.items() if read_text(path) != content]
        if mismatches:
            for path in mismatches:
                print(f"stale generated catalog: {path.relative_to(REPO_ROOT)}", file=sys.stderr)
            return 1
        return 0
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return 0


def load_schema(path: Path) -> Mapping[str, Any]:
    """Return the Plotly schema object."""

    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, Mapping):
        raise TypeError("Plotly schema must be a JSON object")
    return value


def build_catalog(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Build the generated catalog data from the Plotly schema."""

    raw_traces = schema.get("traces")
    if not isinstance(raw_traces, Mapping):
        raise TypeError("Plotly schema is missing traces")

    allowed: dict[str, dict[str, Any]] = {}
    excluded: dict[str, str] = {}
    for trace_type in sorted(str(key) for key in raw_traces):
        trace_schema = raw_traces[trace_type]
        if not isinstance(trace_schema, Mapping):
            continue
        categories = tuple(str(item) for item in trace_schema.get("categories", ()) or ())
        if EXCLUDED_CATEGORY in categories:
            excluded[trace_type] = "true_3d_scene_trace"
            continue
        attributes = trace_schema.get("attributes")
        if not isinstance(attributes, Mapping):
            attributes = {}
        paths = collect_attribute_paths(attributes)
        data_paths = sorted(data_paths_for(trace_type, paths))
        style_paths = sorted(style_paths_for(paths, data_paths))
        binding_paths = data_paths
        allowed[trace_type] = {
            "categories": list(categories),
            "dataPaths": data_paths,
            "stylePaths": style_paths,
            "bindingPaths": binding_paths,
            "example": EXAMPLE_BY_TRACE.get(
                trace_type,
                {"data": {"x": [1, 2, 3], "y": [3, 2, 4]}},
            ),
        }

    return {
        "version": 1,
        "plotlySchemaPath": str(SCHEMA_PATH.relative_to(REPO_ROOT)),
        "source": "plotly.js/dist/plot-schema.json",
        "policy": {
            "excludedCategory": EXCLUDED_CATEGORY,
            "globalRejectedFields": list(GLOBAL_REJECTED_FIELDS),
            "mapPolicy": "offline_only_no_remote_tiles_styles_or_tokens",
        },
        "allowedTraces": allowed,
        "excludedTraces": excluded,
    }


def collect_attribute_paths(attributes: Mapping[str, Any], prefix: str = "") -> set[str]:
    """Return safe Plotly attribute paths under one trace attributes object."""

    paths: set[str] = set()
    for key, value in attributes.items():
        key_text = str(key)
        if key_text in SCHEMA_METADATA_KEYS or is_rejected_key(key_text):
            continue
        next_path = f"{prefix}.{key_text}" if prefix else key_text
        if isinstance(value, Mapping) and "valType" not in value and nested_attribute_keys(value):
            paths.update(collect_attribute_paths(value, prefix=next_path))
        else:
            paths.add(next_path)
    return paths


def nested_attribute_keys(value: Mapping[str, Any]) -> bool:
    """Return whether a schema node looks like nested attributes."""

    return any(str(key) not in SCHEMA_METADATA_KEYS for key in value)


def data_paths_for(trace_type: str, paths: set[str]) -> set[str]:
    """Return allowed data field paths for one trace."""

    data_paths = {path for path in paths if path.split(".", 1)[0] in DATA_ROOTS}
    data_paths.update(SPECIAL_DATA_PATHS.get(trace_type, ()))
    return {path for path in data_paths if not is_rejected_path(path)}


def style_paths_for(paths: set[str], data_paths: Sequence[str]) -> set[str]:
    """Return allowed style field paths for one trace."""

    data_set = set(data_paths)
    return {
        path
        for path in paths
        if path not in data_set
        and (path.split(".", 1)[0] in STYLE_ROOTS or path.split(".", 1)[0] not in DATA_ROOTS)
        and not is_rejected_path(path)
    }


def is_rejected_path(path: str) -> bool:
    """Return whether a path contains a globally rejected field segment."""

    return any(is_rejected_key(segment) for segment in path.split("."))


def is_rejected_key(key: str) -> bool:
    """Return whether a key is globally rejected."""

    lowered = key.lower()
    if lowered.endswith("src"):
        return True
    return lowered in set(GLOBAL_REJECTED_FIELDS)


def render_python(catalog: Mapping[str, Any]) -> str:
    """Render the generated Python module."""

    allowed = catalog["allowedTraces"]
    excluded = catalog["excludedTraces"]
    return (
        '"""Generated Plotly 2D trace catalog for Houmao AG-UI."""\n'
        "\n"
        "# ruff: noqa: E501\n"
        "\n"
        "from __future__ import annotations\n"
        "\n"
        "from typing import Any, Final, TypedDict\n"
        "\n"
        "\n"
        "class PlotlyTraceCatalogEntry(TypedDict):\n"
        '    """One generated Plotly trace catalog entry."""\n'
        "\n"
        "    categories: tuple[str, ...]\n"
        "    data_paths: tuple[str, ...]\n"
        "    style_paths: tuple[str, ...]\n"
        "    binding_paths: tuple[str, ...]\n"
        "    example: dict[str, Any]\n"
        "\n"
        "\n"
        "PLOTLY_TRACE_CATALOG_VERSION: Final[int] = "
        f"{catalog['version']!r}\n"
        "PLOTLY_TRACE_CATALOG_SOURCE: Final[str] = "
        f"{catalog['source']!r}\n"
        "PLOTLY_TRACE_CATALOG_POLICY: Final[dict[str, Any]] = "
        f"{python_repr(catalog['policy'])}\n"
        "PLOTLY_2D_TRACE_TYPES: Final[tuple[str, ...]] = "
        f"{tuple(sorted(allowed))!r}\n"
        "PLOTLY_EXCLUDED_TRACE_TYPES: Final[dict[str, str]] = "
        f"{python_repr(excluded)}\n"
        "PLOTLY_2D_TRACE_CATALOG: Final[dict[str, PlotlyTraceCatalogEntry]] = "
        f"{python_catalog_repr(allowed)}\n"
    )


def python_catalog_repr(value: Mapping[str, Any]) -> str:
    """Render catalog entries as valid typed Python syntax."""

    normalized: dict[str, Any] = {}
    for trace_type, entry in value.items():
        assert isinstance(entry, Mapping)
        normalized[str(trace_type)] = {
            "categories": tuple(entry["categories"]),
            "data_paths": tuple(entry["dataPaths"]),
            "style_paths": tuple(entry["stylePaths"]),
            "binding_paths": tuple(entry["bindingPaths"]),
            "example": entry["example"],
        }
    return python_repr(normalized)


def python_repr(value: Any) -> str:
    """Return deterministic Python literal text."""

    return pformat(value, width=100, sort_dicts=True)


def render_typescript(catalog: Mapping[str, Any]) -> str:
    """Render the generated TypeScript module."""

    allowed = catalog["allowedTraces"]
    normalized_allowed: dict[str, Any] = {}
    for trace_type, entry in allowed.items():
        assert isinstance(entry, Mapping)
        normalized_allowed[str(trace_type)] = {
            "categories": entry["categories"],
            "dataPaths": entry["dataPaths"],
            "stylePaths": entry["stylePaths"],
            "bindingPaths": entry["bindingPaths"],
            "example": entry["example"],
        }
    return (
        "export interface PlotlyTraceCatalogEntry {\n"
        "  categories: readonly string[];\n"
        "  dataPaths: readonly string[];\n"
        "  stylePaths: readonly string[];\n"
        "  bindingPaths: readonly string[];\n"
        "  example: Record<string, unknown>;\n"
        "}\n"
        "\n"
        f"export const PLOTLY_TRACE_CATALOG_VERSION = {catalog['version']} as const;\n"
        "export const PLOTLY_TRACE_CATALOG_POLICY = "
        f"{json.dumps(catalog['policy'], indent=2, sort_keys=True)} as const;\n"
        "export const PLOTLY_2D_TRACE_TYPES = "
        f"{json.dumps(sorted(allowed), indent=2)} as const;\n"
        "export const PLOTLY_EXCLUDED_TRACE_TYPES = "
        f"{json.dumps(catalog['excludedTraces'], indent=2, sort_keys=True)} as const;\n"
        "export const PLOTLY_2D_TRACE_CATALOG: Record<string, PlotlyTraceCatalogEntry> = "
        f"{json.dumps(normalized_allowed, indent=2, sort_keys=True)} as const;\n"
    )


def read_text(path: Path) -> str:
    """Return path text or an empty string when the file is absent."""

    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
