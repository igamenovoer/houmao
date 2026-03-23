# Gateway Wake-Up Demo

Unread filesystem mailbox content is waiting for you.

When you process this message, write the current UTC time in RFC3339 format to `{{OUTPUT_FILE_PATH}}`.

Do not mark the message read until the file write succeeds.
