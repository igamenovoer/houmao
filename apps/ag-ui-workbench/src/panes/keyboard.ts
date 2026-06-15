import type { KeyboardEvent } from "react";

export function submitOnShiftEnter(
  event: KeyboardEvent<HTMLTextAreaElement>,
  submit: () => void | Promise<void>,
): void {
  if (
    event.key !== "Enter" ||
    !event.shiftKey ||
    event.altKey ||
    event.ctrlKey ||
    event.metaKey ||
    event.repeat
  ) {
    return;
  }
  event.preventDefault();
  void submit();
}
