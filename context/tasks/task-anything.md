we want to have a way to allow user-started TUI process to join our houmao system.

by "joining", we mean, that TUI process is just like any other process launched by houmao, except that it is started by user instead of houmao, in a way that houmao shall not care.

specifically, we want to have `houmao-mgr agents join <args>` command, which can be used to join any TUI process into houmao system, in that:
- this command should be run inside tmux session of the TUI process, assume TUI process is in window 0, and this command is being executed in other window of the same session
- assume the TUI process is already up and running
- houmao-mgr will detect the TUI process (claude code or codex), and then create necessary artifacts and metadata for this TUI process (registry, dirs, manifests, inject tmux envs, etc), so that houmao system can treat this TUI process as if it is launched by houmao itself
- optionally, user can provide a command string for launching the TUI process, so that houmao knows how to restart the TUI process when needed, this should be recorded somewhere.

headless agent can also join the houmao system similarly, in this way:
- still, must be inside a tmux session, call `houmao-mgr agents join --headless --launch-cmd <cmd-string-to-launch-agent> <other-args>` in one of the windows of the session
- then required artifacts and metadata will be created for this headless agent, and houmao system can treat this headless agent as if it is launched by houmao itself

in any case, if some required info to create artifacts and metadata is missing, the command should fail with proper error message, and you just define cli shape to require for enough info from user.
