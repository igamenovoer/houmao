"""Send a local test message through Stalwart and verify it is readable over IMAP."""

from __future__ import annotations

import argparse
import imaplib
import smtplib
import subprocess
import time
from email.message import EmailMessage
from pathlib import Path

from provision_stalwart import StackConfig, load_stack_config


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        default=Path(__file__).with_name(".env"),
        type=Path,
        help="Path to the compose-local env file.",
    )
    parser.add_argument(
        "--timeout-seconds",
        default=15,
        type=int,
        help="Maximum time to wait for the test message to appear in IMAP.",
    )
    return parser


def run_command(args: list[str]) -> str:
    """Run a command and return its stdout."""

    result = subprocess.run(args, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def stalwart_container_ip(env_file: Path) -> str:
    """Return the Docker-network IP address for the Stalwart container."""

    compose_file = env_file.with_name("compose.yaml")
    container_id = run_command(
        [
            "docker",
            "compose",
            "--env-file",
            str(env_file),
            "-f",
            str(compose_file),
            "ps",
            "-q",
            "stalwart",
        ]
    )
    if not container_id:
        raise RuntimeError("Could not determine the Stalwart container ID.")

    container_ip = run_command(
        [
            "docker",
            "inspect",
            "-f",
            "{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
            container_id,
        ]
    )
    if not container_ip:
        raise RuntimeError("Could not determine the Stalwart container IP address.")
    return container_ip


def send_and_verify_mail(config: StackConfig, container_ip: str, timeout_seconds: int) -> str:
    """Send a message through SMTP submission and verify it appears in IMAP."""

    subject = f"houmao-smoke-{int(time.time())}"
    message = EmailMessage()
    message["From"] = config.seed_mailbox_email
    message["To"] = config.seed_mailbox_email
    message["Subject"] = subject
    message.set_content("houmao email-system smoke test")

    with smtplib.SMTP(container_ip, config.submission_port, timeout=10) as smtp:
        smtp.ehlo()
        smtp.login(config.seed_mailbox_name, config.seed_mailbox_password)
        smtp.send_message(message)

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        with imaplib.IMAP4(container_ip, config.imap_port) as imap:
            imap.login(config.seed_mailbox_name, config.seed_mailbox_password)
            status, _ = imap.select("INBOX")
            if status != "OK":
                raise RuntimeError("Failed to select the seeded mailbox INBOX.")

            status, data = imap.search(None, "SUBJECT", subject)
            if status == "OK" and data and data[0].strip():
                return subject
        time.sleep(1)

    raise RuntimeError(f"Sent test message was not found in IMAP: {subject}")


def main() -> int:
    """Run the mail-flow smoke test."""

    args = build_parser().parse_args()
    config = load_stack_config(args.env_file)
    container_ip = stalwart_container_ip(args.env_file)
    subject = send_and_verify_mail(config, container_ip, args.timeout_seconds)
    print(f"Verified SMTP submission and IMAP delivery for {config.seed_mailbox_email}: {subject}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
