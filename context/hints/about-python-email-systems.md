# Python-based Email Systems: Libraries and Full-Scale Servers

Python offers a mature ecosystem for both building custom email logic and deploying full-scale, production-ready mail servers. This guide categorizes the most relevant tools for modern Python development.

## 1. Full-Scale Server Applications (Self-Hosted)

If the goal is to deploy a complete mail hosting environment, these Python-centric platforms are the industry standards.

- **[Modoboa](https://modoboa.org/):** A comprehensive mail hosting and management platform built with Django. It provides a modern web-based UI for managing domains, mailboxes, and aliases, and includes a built-in webmail client. It integrates with Postfix and Dovecot.
- **[Mailu](https://mailu.io/):** A Docker-based mail server stack where the administration interface and orchestration are written in Python (Flask). It is designed for easy containerized deployment and includes SMTP, IMAP, Antispam (Rspamd), and Antivirus (ClamAV).
- **[Mailman 3](https://www.list.org/):** The standard for managing electronic mailing lists. The modern version is a complete rewrite in Python 3, consisting of a core engine, a REST API, and a Django frontend.

## 2. Server-side Development Libraries

For building custom SMTP servers or handling incoming mail programmatically.

- **[aiosmtpd](https://github.com/aio-libs/aiosmtpd):** The modern, `asyncio`-based replacement for the legacy `smtpd` module. It is highly extensible via custom handlers to process incoming messages.
- **[Salmon](https://salmon-mail.readthedocs.io/):** A pure Python mail server framework designed to handle incoming mail similarly to how a web framework (like Flask or Django) handles HTTP requests, using routing and handlers.

### Example: Basic `aiosmtpd` Handler
```python
import asyncio
from aiosmtpd.controller import Controller

class ExampleHandler:
    async def handle_DATA(self, server, session, envelope):
        print(f"Receiving message from: {envelope.mail_from}")
        print(f"Message for: {envelope.rcpt_tos}")
        print(f"Message content:\n{envelope.content.decode('utf8', errors='replace')}")
        return '250 OK'

if __name__ == '__main__':
    handler = ExampleHandler()
    controller = Controller(handler, hostname='127.0.0.1', port=10025)
    controller.start()
    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        controller.stop()
```
*Source: [aiosmtpd Documentation](https://aiosmtpd.readthedocs.io/)*

## 3. Client-side Libraries (Sending & Receiving)

High-level libraries that simplify interaction with existing mail servers.

### Sending Emails (SMTP)
- **[Red Mail](https://red-mail.readthedocs.io/):** A user-friendly library for sending emails that handles HTML templates (Jinja2), attachments, and multi-part messages with minimal boilerplate.
- **[yagmail](https://github.com/kootenpv/yagmail):** Specifically optimized for Gmail, making sending emails as simple as a single function call.

### Receiving & Managing Emails (IMAP)
- **[IMAPClient](https://imapclient.readthedocs.io/):** A high-level, Pythonic wrapper for `imaplib` that simplifies complex IMAP operations like searching, fetching, and folder management.
- **[imap_tools](https://github.com/ikvk/imap_tools):** An alternative to IMAPClient that focuses on a very simple API for common tasks like parsing email bodies and attachments.

### Example: Fetching Emails with `IMAPClient`
```python
from imapclient import IMAPClient

with IMAPClient('imap.example.com') as client:
    client.login('user@example.com', 'password')
    client.select_folder('INBOX')
    
    # Search for unread messages
    messages = client.search(['UNSEEN'])
    
    for msgid, data in client.fetch(messages, ['ENVELOPE']).items():
        envelope = data[b'ENVELOPE']
        print(f"ID {msgid}: '{envelope.subject.decode()}' from {envelope.from_}")
```
*Source: [IMAPClient Documentation](https://imapclient.readthedocs.io/)*

## References
- [Official aiosmtpd Docs](https://aiosmtpd.readthedocs.io/)
- [Official Modoboa Docs](https://docs.modoboa.org/)
- [Official IMAPClient Docs](https://imapclient.readthedocs.io/)
- [Red Mail GitHub](https://github.com/Mause/redmail)
