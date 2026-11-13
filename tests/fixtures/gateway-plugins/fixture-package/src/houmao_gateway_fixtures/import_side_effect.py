"""Mark an unwanted import so selected-only discovery is observable."""

import os
from pathlib import Path

marker = os.environ.get("HOUMAO_PLUGIN_UNSELECTED_IMPORT_MARKER")
if marker:
    Path(marker).write_text("imported\n", encoding="utf-8")
raise RuntimeError("Unselected fixture module was imported")
