Here is a complete draft for your project's README introduction, followed by a breakdown of exactly why this concept serves as the perfect foundation for your architecture.

---

### Project Introduction Draft

# Houmao (猴毛)

**Dynamic, loosely-coupled AI agent orchestration for the command line.**

In the classic epic *Journey to the West*, Sun Wukong (The Monkey King) possesses a legendary ability: when facing a monumental task or an overwhelming army, he plucks a handful of his own magical hair (**Houmao**), blows the breath of life onto it, and instantly creates hundreds of independent, fully capable clones of himself.

**Houmao** brings this mythos to your terminal.

Rather than forcing agents into rigid, hard-coded execution graphs, Houmao treats AI orchestration as a dynamic, decentralized deployment. You take a single, powerful intelligence (your backend LLM, like Claude, Codex, or Gemini), apply a specific system prompt (the breath of life), and instantly spawn an independent, CLI-based agent operating in its own session.

Whether you need a swift coder, a meticulous reviewer, or a strategic planner, they all stem from the same source. You define the roles, issue the command, and watch your troop fan out to conquer your codebase in parallel.

**Key Features:**

* **One Source, Infinite Forms:** Use a single backend model to power a diverse team of specialized agents through markdown-driven role definitions.
* **True Independence:** Agents run as real CLI tool instances (backed by tmux or CAO), complete with their own state and execution environments.
* **Dynamic Formations:** Avoid the overhead of static agent graphs. Spin up exactly the clones you need, right when you need them.

---

### Why "Houmao" is the Perfect Architectural Metaphor

Choosing a name for an open-source project is about finding a concept that instantly communicates *how the software actually works*. Here is why **Houmao** aligns flawlessly with your technical design:

* **The "One-to-Many" Backend Model:** In many frameworks, setting up ten agents feels like configuring ten entirely different software stacks. In your framework, the underlying "brain" (the LLM API connection) is identical. The clones are physically just copies of Wukong. The metaphor perfectly communicates that developers only need to configure their core model once to spawn an entire team.
* **The "Breath of Life" (System Prompts):** Wukong's hair does nothing until he blows on it. In your architecture, a standard CLI process sits idle until it is injected with a `Role` (your system prompts and blueprints). The context is what transforms a generic model into a specialized worker.
* **Loosely-Coupled Autonomy:** Wukong does not micromanage the muscles of every single clone. He gives them a directive, and they fight autonomously. This mirrors your framework's avoidance of rigid, LangGraph-style orchestration. Your agents operate in their own isolated tmux/CAO realms, executing tasks independently based on their given forms.
* **Lightweight Spawning:** Plucking a hair is effortless and fast. It signals to users that spinning up a new agent in this framework is designed to be a low-friction, lightweight CLI command, not a heavy deployment process.

Would you like to explore how to structure the "Getting Started" or "Quickstart" section of the documentation using this new terminology?