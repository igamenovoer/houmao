Yes — and for **your own child process**, non-root is often enough.

What you **cannot** usually do without sudo is change host-level firewall, qdisc/`tc`, routes, or interface state, because those are `CAP_NET_ADMIN` operations. ([man7.org][1])

For a subprocess you own, the two best non-root approaches are:

### 1) Best for testing exception handling: inject syscall failures with `strace`

If your real goal is “make the child see a network I/O error and verify its handler,” this is usually the cleanest method. `strace` supports syscall tampering with `--inject=...:error=...:when=...`, and it can inject faults into selected syscalls without needing actual packet loss or firewall changes. `strace` works via `ptrace`; under common Yama settings, direct parent→child tracing is allowed even when broader attach is restricted. ([man7.org][2])

Examples:

```bash
# make the first connect() fail
strace -f \
  -e inject=connect:error=ECONNREFUSED:when=1 \
  ./child

# make the first recvfrom() fail
strace -f \
  -e inject=recvfrom:error=ECONNRESET:when=1 \
  ./child

# make every recvmsg() starting from the 3rd one fail
strace -f \
  -e inject=recvmsg:error=ETIMEDOUT:when=3+ \
  ./child
```

If the program is already running:

```bash
strace -p "$PID" -f \
  -e inject=recvfrom:error=ECONNRESET:when=1
```

That affects the **next matching syscall**, not traffic already sitting in the kernel. `strace` can also inject delays on syscall entry/exit, which is handy for timeout-path testing. ([man7.org][2])

A practical note: many libraries do socket I/O via `read`/`write` or `recvmsg`/`sendmsg`, not just `recvfrom`/`sendto`. So first trace what the child actually uses, then inject on that syscall.

### 2) Best for breaking a real live socket: duplicate the child’s FD and `shutdown()` it

If you want to break an **actual existing connection** rather than fake an errno, Linux has a non-root path for your own child:

* `/proc/<pid>/fd` shows the child’s open FDs; socket entries appear like `socket:[inode]`. ([man7.org][3])
* `pidfd_getfd()` can duplicate one of the child’s file descriptors into your process, subject to ptrace-style permission checks. The duplicate refers to the **same open file description** / underlying socket object. ([man7.org][4])
* `shutdown(fd, SHUT_RDWR)` shuts down the full-duplex connection on that socket. ([man7.org][5])

So the pattern is:

1. find the child’s socket FD in `/proc/<pid>/fd`
2. duplicate it into the harness with `pidfd_getfd()`
3. call `shutdown(SHUT_RDWR)` on the duplicate

That will usually wake a blocked network call or cause subsequent I/O to fail/EOF on the child, depending on protocol and timing. Permission for `pidfd_getfd()` is explicitly governed by a ptrace access check. ([man7.org][4])

### Important nuance if the child inherited the socket from you

If **your harness created the socket and passed it to the child**, keep your copy. Then `shutdown()` on your copy is the simplest solution.

But **closing** your copy alone is usually **not enough**. Duplicated/inherited FDs refer to the same open file description, and that object stays alive until all references are gone. Linux also notes that a blocking I/O call may even complete after another thread closes its descriptor. So use `shutdown()`, not just `close()`, when you want an immediate disruption signal. ([man7.org][6])

### What I would do

If you want a predictable test matrix for handlers, use `strace --inject` and choose the exact errno you want.

If you want to test behavior of a **real established socket**, use `pidfd_getfd + shutdown()` or, even better, design the harness so the child talks through a proxy/socket you control.

If you want, tell me whether the child **inherits the socket** or **opens it itself**, and I’ll give you the exact shell/Python snippet for that case.

[1]: https://man7.org/linux/man-pages/man7/capabilities.7.html?utm_source=chatgpt.com "capabilities(7) - Linux manual page"
[2]: https://man7.org/linux/man-pages/man1/strace.1.html "strace(1) - Linux manual page"
[3]: https://man7.org/linux/man-pages/man5/proc_pid_fd.5.html?utm_source=chatgpt.com "proc_pid_fd(5) - Linux manual page"
[4]: https://man7.org/linux/man-pages/man2/pidfd_getfd.2.html "pidfd_getfd(2) - Linux manual page"
[5]: https://man7.org/linux/man-pages/man2/shutdown.2.html?utm_source=chatgpt.com "shutdown(2) - Linux manual page"
[6]: https://man7.org/linux/man-pages/man2/dup.2.html "dup(2) - Linux manual page"
