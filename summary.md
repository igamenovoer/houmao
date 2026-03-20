# Weekly Summary (2026-03-14 ~ 2026-03-20)

## Top 5 New Features

### 1. Houmao Server + srv-ctrl Pair

让 houmao 可以作为一个常驻后台服务运行，而不必每次都在本地直接拉起 agent 进程。外部程序（或其他 agent）通过 REST API 向 houmao-server 发指令、查状态、取结果，实现了"把 agent 当服务调用"的使用模式。这为后续构建多 agent 协作系统、headless 自动化流水线打开了入口。

### 2. Stalwart Mailbox Transport

让 agent 能够真正通过电子邮件收发消息。之前 mailbox 只能在本地进程间传递，现在接入了标准 SMTP/IMAP 协议，agent 可以给真实邮箱发邮件、从邮箱收邮件。这意味着 agent 的通信边界扩展到了任何支持电子邮件的系统，跨机器、跨网络的 agent 协作成为可能。

### 3. 本地 Email System Docker Stack

为开发和测试 mailbox 邮件功能提供了一套开箱即用的本地环境。一条命令启动完整的邮件服务器（Stalwart）+ Web 客户端（Cypht），自动完成账户创建和配置，并附带端到端冒烟测试脚本验证邮件能否正常收发。开发者无需依赖外部邮件服务就能在本地完整跑通邮件链路。

### 4. Rx-based Shadow Turn Monitor

解决了 houmao 在监控 agent 交互状态时容易出现"判断时机不对"的问题。原来的实现依赖固定的等待时间来判断 agent 是否完成了一轮响应，容易因时序不稳定而误判。新的 Rx 实现改为监听事件流、按信号驱动，让"agent 什么时候空闲、什么时候在处理"的判断更准确，减少了发送指令被丢失或撞车的情况。

### 5. Claude Code State Tracking Explore Harness

搞清楚了 Claude Code 在各种边界情况下的状态信号长什么样。通过 replay（回放录制的 tmux 输出）和 live（接真实进程）两种方式，系统性地测试了网络中断、进程被杀、信号模糊等异常场景，记录了每种情况下 Claude Code 实际输出的内容。这些探索结果是后续让 houmao 可靠地监控和驱动 Claude Code 的前提。
