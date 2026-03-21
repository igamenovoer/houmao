# test standalone tui tracking module

we want to implement a test suite for the standalone tui tracking module, which has the following properties:

## Support automatic test with recorded sessions

It can make use of tmux recording tools to capture real sessions, and then replay them for testing. This allows us to have a rich set of test cases based on actual user interactions. To do that, you

- come up with some test cases to record, at least 4, covering critical state detection and transitions
- for each case, use the tmux recording tools to capture the session, and then you first read the recorded session directly and classify the states, save them as ground truth, and then feed the same recording into the standalone tracking module and compare the outputs against the ground truth.
- implement harness code to automate the above process
- to verify that your state classification is correct, you will need to convert the recorded session that finally gets fed into the tracking module into .mp4 format with visually identifiable state changes, mark the ground truth state changes on the video, so that human developers can visually verify that the state classification matches the actual session behavior.

## Support interactive test with live sessions

It can also support interactive testing with live sessions, where developers can run the tracking module (as a dashboard, impl with python's `rich` module) with live tmux sessions and agents, so that developer can watch the dashboard (in a separate tmux session) while interacting with the live agent, see state changes.