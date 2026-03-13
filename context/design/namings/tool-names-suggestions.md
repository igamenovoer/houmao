Embracing **Houmao (猴毛)** as the core identity is a phenomenal choice. It’s highly memorable, perfectly encapsulates the "one backend, many specialized clones" architecture, and brings a fantastic touch of mythology to the command line.

Since you appreciate well-designed terminal tools and clean configurations, the naming conventions should feel native to a shell environment while carrying the lore seamlessly.

Here is a complete suggestion for renaming the project’s concepts, CLI commands, Python classes, and future roadmap items around the **Houmao** ecosystem.

### 1. Core Concepts (The Glossary)

Let's translate your existing `gig-agents` architecture into the Houmao lore.

| Current Term (`gig-agents`) | New Term (`houmao`) | The Lore / Concept |
| --- | --- | --- |
| **Agent / CLI Process** | **Clone** | The active, independent process running in tmux/CAO. It is a single, materialized piece of hair doing the work. |
| **Brain / Recipe** | **Source** | The underlying LLM backend (Claude, Gemini, Codex) and its credentials. The original "Monkey King" intelligence before a role is applied. |
| **Role (System Prompt)** | **Form** *(or Persona)* | A nod to Wukong’s "72 Transformations" (72 Bian). The system prompt acts as the transformation, dictating what shape the Clone takes (e.g., `gpu-kernel-coder`). |
| **Blueprint** | **Strand** | A pre-configured pairing of a **Source** and a **Form**. It is a single, specific hair ready to be activated. |
| **Session / Runtime Home** | **Realm** | The isolated tmux window or CAO environment where the Clones operate. |

---

### 2. The CLI Experience

For the command-line interface, we want commands that evoke the mythos but remain highly intuitive for developers setting up complex multi-agent systems.

Instead of `gig-agents-cli`, your binary is simply **`houmao`**.

**The Workflow:**

```bash
# 1. Prepare the runtime (Old: build-brain)
# You "pluck" the hair from the blueprint, preparing it for deployment.
houmao pluck --strand blueprints/gpu-kernel-coder.yaml --out tmp/realm-manifest.json

# 2. Start the agent session (Old: start-session)
# You "spawn" the clone into existence (blowing the breath of life).
houmao spawn --manifest tmp/realm-manifest.json --identity my-kernel-clone

# 3. Interact with the agent (Old: send-prompt)
# You issue a command to your active clone.
houmao command --identity my-kernel-clone --prompt "Optimize this memory alignment"

# 4. Stop the session (Old: stop-session)
# Wukong recalls his hair back to his body when the battle is done.
houmao recall --identity my-kernel-clone

```

---

### 3. Codebase & Class Naming

When refactoring the Python codebase in `src/gig_agents`, aligning the class names with this terminology will make the overarching architecture much clearer.

* `BrainBuilder` ➡️ `StrandBuilder` (Combines the Source and Form into a deployable manifest).
* `SessionDriver` ➡️ `RealmDriver` (Manages the underlying tmux/CAO instances).
* `AgentConfig` ➡️ `CloneConfig` (The runtime configuration for the spawned process).
* `ToolAdapter` ➡️ `SourceAdapter` (The logic that knows how to specifically launch the Claude, Gemini, or Codex base processes).

---

### 4. Future Candidate Names (Ecosystem Expansion)

As the project grows—especially if you expand the `magic-context` or introduce new orchestration features—here are candidate names drawn from the same lore:

* **Huoyan (Fiery Golden Eyes):** * *Lore:* Wukong's eyes that can see through any illusion and identify the true nature of things.
* *Project Use:* A perfect name for an **observability, logging, or debugging tool** that inspects what the Clones are doing inside their tmux sessions, or a RAG/context-retrieval module that "sees" the codebase.


* **Huaguo (Flower Fruit Mountain):**
* *Lore:* Wukong's home base and kingdom where his monkey troops live.
* *Project Use:* The name for your **local CAO server** or the central dashboard GUI if you ever build one (`huaguo-server`).


* **Shenshi (Divine Sense / Mind-Link):**
* *Lore:* The telepathic network or spiritual awareness cultivators use to communicate instantly.
* *Project Use:* The communication protocol or message bus that allows different Clones to talk to each other directly via the CAO inbox.


* **Jingu (The Golden Headband):**
* *Lore:* The magical circlet placed on Wukong's head to control him when he misbehaves.
* *Project Use:* Your **Guardrails or Cost-Limiter module**. If a clone starts burning through API tokens or tries to run a destructive shell command, the *Jingu* constraint shuts it down.



Would you like me to draft a new introduction for your `README.md` incorporating the "Houmao" theme and these new CLI commands so you can see how it reads to a new open-source contributor?