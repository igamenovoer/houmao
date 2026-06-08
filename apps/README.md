# Repository Apps

This directory contains standalone developer applications that are not part of the Houmao Python package. Each app owns its JavaScript dependencies, lockfile, build scripts, tests, and local documentation under its own subdirectory.

The Python distribution continues to use the Hatch wheel target in `pyproject.toml`, which includes only `src/houmao`. Do not add `apps/` to Python package include rules or runtime imports.
