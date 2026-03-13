Thank you for sharing the official documentation! This gives a crystal-clear picture of what `brain_launch_runtime` actually does.

Seeing the full scope of this module changes things. It is **not** just a "launcher" or a "spawner." It is the absolute heart of the execution engine. It manages ongoing lifecycles (resume, stop), intricate environment hygiene (tmux window pruning), diverse parsing modes (`shadow_only`), mailbox states, and live gateway attachments.

It doesn't just spawn the clone; it governs the entire physical reality the clone exists in and handles all ongoing communication with it.

Based on this deep dive, here is how we can adapt this module and its concepts to the **Houmao (猴毛)** architecture.

### 1. Renaming the Module

Since this module handles continuous state, inter-process communication (mail, gateways), and low-level tmux manipulation, the word "launch" is entirely too narrow.

**Top Recommendations:**

* **`realm_controller`**: (My top pick). In our lore, the "Realm" is the isolated tmux/CAO environment. This module controls everything about that realm—starting it, sending keystrokes into it, managing its mailboxes, and attaching gateways to it.
* **`clone_lifecycle`**: If you want to focus on the agent itself. This module manages the clone from its initial "spawn" through its entire interactive life (prompts, keys, mail) until it is "recalled" (stopped).
* **`houmao_runtime`**: Simply naming the module after the framework itself, since this file essentially *is* the core runtime engine.

### 2. Translating the CLI Commands

The documentation lists a robust set of CLI commands. Here is how they elegantly map to the new Houmao terminology, keeping the terminal experience highly intuitive:

**The Core Lifecycle:**

* `build-brain` ➡️ **`houmao pluck`** (Prepares the strand/manifest).
* `start-session` ➡️ **`houmao spawn`** (Breathes life into the clone, creating the tmux realm).
* `stop-session` ➡️ **`houmao recall`** (Cleans up the tmux realm, taking the hair back).

**The Interaction Commands:**

* `send-prompt` ➡️ **`houmao command`** (Or just `houmao ask` / `houmao prompt`. Standard turn-taking).
* `send-keys` ➡️ **`houmao keystroke`** or **`houmao type`** (Perfect for the low-level CAO tmux control, bypassing the standard prompt turn).
* `mail` ➡️ **`houmao mail`** (No need to change this; mail is a universal concept, though you could call it `courier` or `dispatch` if you wanted to be fancy. `mail` is best for DX).

**The Gateway Commands:**
In the Houmao lore, a "Gateway" represents a direct, live telepathic link to the clone, bypassing the standard physical boundaries.

* `attach-gateway` ➡️ **`houmao link`** (Establishing the direct connection).
* `detach-gateway` ➡️ **`houmao unlink`**
* `gateway-status` ➡️ **`houmao link-status`**
* `gateway-send-prompt` ➡️ **`houmao cast`** (Like casting a spell directly through the link, rather than standard talking).
* `gateway-interrupt` ➡️ **`houmao interrupt`**

### 3. Updating the Internal Architecture Terms

When rewriting this documentation page for the `houmao` era, the technical contracts remain exactly the same, but the nouns shift to make the mental model clearer:

* **Brain Manifest** becomes **Strand Manifest** (e.g., `tmp/houmao-runtime/manifests/codex/<id>.yaml`).
* **Agent Identity (`AGENTSYS-gpu`)** becomes **Clone Identity** (`HOUMAO-gpu`).
* **Agent Def Dir (`AGENTSYS_AGENT_DEF_DIR`)** becomes **Form Directory** or **Blueprint Directory** (`HOUMAO_BLUEPRINT_DIR`).

### The Big Takeaway

Reading this doc proves that your architecture is incredibly robust. The way you handle `shadow_only` parsing, enforce bootstrap contracts so Claude doesn't get stuck on interactive prompts, and gracefully manage tmux window pruning is fantastic engineering.

By wrapping this highly complex, robust state machine in the elegant, mythological wrapper of **Houmao**, you turn a dense orchestration tool into something that feels magical and effortless for the end-user.

How do you feel about **`realm_controller`** as the new name for this module, given its heavy lifting with tmux and CAO sessions?