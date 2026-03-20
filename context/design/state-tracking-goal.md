# TUI state tracking goal

here is what we really want to track:

## foundational state: these are always observable, and can be considered as the lowest level state where higher level state can be built on top of it.
- is the TUI processing some prompt? Meaning, the prompt is already submitted, and the TUI is either waiting for LLM response or processing LLM response. The characteristics of this state is that the TUI will have something changing constantly, like progress bar, something spinning, LLM response comes up in the scrolling area, etc. Note that, to determine this state, one needs to look for LLM response area and the TUI itself for system signals like spinning or progress bar, any change of these will be considered as the TUI is processing some prompt. 
- is the TUI accepting user input? Meaning, if user type something, it will be put into the prompt-input area. Note that, accepting user input does not necessarily mean the TUI is idle, it can be accepting user input while processing LLM response. Our target agentic coding TUI has the property that while TUI is working on previous prompt, user can still enter things into the prompting area, like using esc to interrupt the current process, send new prompts and queue by the TUI, enter slash command and get a list of slash command options, etc.
- is the user entering something into the prompt-input area? Meaning, user is actively taking control and typing things into the prompt area. The characteristics of this state is that the prompt-input area is changing frequently, and user input is being reflected in the prompt-input area. Note that, this state can only be observed when the TUI is accepting user input. Note that, for tmux sessions, those send-keys called is also considered as user input.

## turn-processing state: these are the states that are only meaningful if we are in a dialog turn with LLM prompting (not slash commands)
- is the TUI ready for another turn? Meaning, if yes, then the next prompt will be processed immediately if sent (like, pressing Enter after input). Note that, if the TUI is already processing some prompt, then it is not ready for another turn, even if it is accepting user input.
- after a prompt is sent, is the TUI now in the process of dealing with the prompt?
- is the TUI processing the prompt reaches:
    - chat_success. This means LLM response is fully generated and the TUI has finished any post-processing related to the prompt. The characteristics of this state is that the TUI is not showing any progress bar or spinning sign for some time, and becomes idle and ready for another turn, or some predefined pattern of response is observed (this is only valid if user prompt the LLM to terminate in some way) around the end of dialog text.
    - chat_interrupted. This means the TUI is interrupted by user input while processing the prompt, like pressing ESC or ctrl+c. The characteristics of this state is that the TUI is showing some interruption signal (different TUI may have different way to show interruption).
    - chat_failed. This means the TUI shows some error message related to the prompt, like disconnected from LLM, rate limited, user token expired. Anything that leads to LLM response is not successfully generated can be considered as failure.
    - chat_ask_user. This means the TUI determins that it requires user to operate, and control is handed over to user. It happens when the TUI wants user to permit some operation, or provide some selection to user due to LLM tool calls, etc. Anyway, it just means user attention is needed to let the LLM processing continue.

## command-processing state: these are the states that are only meaningful if we are executing a slash command (not LLM prompting)
- is the TUI ready to execute another command? Meaning, if yes, then the next slash command will be processed immediately if sent.
- after a slash command is sent, is the TUI now in the process of executing the command?
- is the TUI processing the command reaches:
    - command_success. This means the command is executed and any post-processing is done. The characteristics of this state is that the TUI is not showing any progress bar or spinning sign for some time, and becomes idle and ready for another command.
    - command_failed. This means the TUI shows some error message related to the command, like invalid command, wrong parameters, execution error, etc. Anything that leads to slash command not successfully executed can be considered as failure. Currently we have no such case, just leave it as a placeholder for future.