# GEMINI.md - Project Context for Houmao (猴毛)

Houmao is a framework and CLI toolkit designed to orchestrate teams of loosely-coupled, CLI-based AI agents. It treats each agent as a dedicated, real CLI process (such as `codex`, `claude`, or `gemini`) operating with its own isolated disk state, memory, and native user experience (typically backed by `tmux`).

## 1. Project Overview

- **Name:** Houmao (猴毛, "monkey hair") — inspired by Sun Wukong's ability to create independent clones.
- **Core Goal:** Orchestrate agents as first-class CLI citizens while keeping coordination flexible and context-driven.
- **Key Concepts:**
    - **Agent Definition Directory:** A folder containing `brains/`, `roles/`, and `blueprints/`.
    - **Brain Recipe:** A declarative preset selecting tool + skill subset + config profile + credential profile.
    - **Role:** A package defining the system prompt and behavior policy for an agent session.
    - **Blueprint:** A binding of a brain recipe to a role.
- **Main Technologies:**
    - **Language:** Python (3.11+)
    - **Environment Management:** [Pixi](https://pixi.sh/)
    - **Agent Runtime:** [CAO (CLI Agent Orchestrator)](https://github.com/imsight-forks/cli-agent-orchestrator)
    - **Orchestration Backend:** `tmux` (local), `cao_rest` (external/server-backed).
    - **Data/Validation:** Pydantic v2, OmegaConf/Hydra.

## 2. Architecture & Lifecycle

### Two-Phase Lifecycle
1.  **Build Phase (`build-brain`):**
    - Input: `BrainRecipe` or `Blueprint`.
    - Process: `BrainBuilder` resolves tool adapters, projects configs, skills, and credentials.
    - Output: A **Runtime Home** (disk folder) and a `BrainManifest` (JSON).
2.  **Run Phase (`start-session`):**
    - Input: `BrainManifest` + `Role` (or `Blueprint`).
    - Process: `RuntimeSessionController` creates a `LaunchPlan` and dispatches it to a backend (`tmux` or `cao_rest`).
    - Interaction: Use `send-prompt` and `stop-session` to manage the lifecycle.

### Key Source Components
- `src/houmao/agents/brain_builder.py`: Build phase logic.
- `src/houmao/agents/realm_controller/`: Run phase logic (session management, backends).
- `src/houmao/cao/`: Integration with CAO server and client.

## 3. Development Workflow

### Key Commands (via Pixi)
Always prefer `pixi run ...` over direct command execution.

- **Setup:** `pixi install` (optional: `pixi install -e pg-hosting` for database features).
- **Format:** `pixi run format` (Ruff format).
- **Lint:** `pixi run lint` (Ruff check).
- **Typecheck:** `pixi run typecheck` (Strict `mypy` checks).
- **Test (Unit):** `pixi run test` (under `tests/unit`).
- **Test (Runtime):** `pixi run test-runtime` (under `tests/unit/agents` and `tests/unit/cao`).
- **Build Package:** `pixi run build-dist`.

### Python Entry Points
- `houmao-cli`: Main lifecycle management (build/start/prompt/stop).
- `houmao-cao-server`: Local CAO server launcher.
- `houmao-server`: Custom Houmao-owned CAO-compatible server.
- `houmao-mgr`: Pair-management CLI for `houmao-server`.

## 4. Development Conventions

- **Typing:** Strict type hints everywhere (`mypy --strict`).
- **Linting:** Ruff (100 char line length).
- **Docstrings:** NumPy-style for all public APIs. Private helpers require brief descriptions.
- **Naming:**
    - `snake_case` for modules/functions/variables.
    - `PascalCase` for classes.
    - **Instance Members:** Prefix with `m_` in stateful service/helper/controller classes (e.g., `self.m_storage`).
    - **Exception:** Do *not* use `m_` prefix for `pydantic` or `attrs` model fields.
- **Imports:** Absolute imports preferred. Group: Standard lib -> Third-party -> Local.
- **Credentials:** **NEVER** commit `api-creds/`, `*.env`, `auth.json`, or `credentials.json`.
- **Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`).

## 5. Directory Structure Overview

- `src/houmao/`: Core implementation.
- `tests/`: Split into `unit/`, `integration/`, and `manual/`.
- `docs/`: Reference (`agents_brains.md`, `cli.md`) and migration guides.
- `context/`: Shared context packages (roles, skills, instructions).
- `openspec/`: Spec-driven change tracking.
- `scripts/`: Automation and demo scripts.
- `config/`: Project-level configuration assets.
- `tmp/`: Runtime homes and build artifacts (safe to delete, gitignored).
- `extern/`: Tracked (`tracked/`) and reference (`orphan/`) external dependencies.

## 6. Project Status

Active and unstable development. Breaking changes are common. Prioritize design clarity and forward progress over backward compatibility.
