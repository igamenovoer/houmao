import { Terminal } from "./xterm.mjs";
import { FitAddon } from "./addon-fit.mjs";

const viewport = document.getElementById("terminal-viewport");
const terminalHost = document.getElementById("terminal");
const status = document.getElementById("connection");
const restart = document.getElementById("restart");
const { mode, entryPath } = viewport.dataset;
const interactive = mode === "interact";
const maxBufferedInput = 1024 * 1024;
const maxInputFrame = 16 * 1024;
const encoder = new TextEncoder();

function grantFromUrl(url) {
  const fragment = new URLSearchParams(url.hash.slice(1));
  const ticket = fragment.get("ticket");
  return fragment.size === 1 && /^[A-Za-z0-9_-]{16,256}$/.test(ticket ?? "") ? ticket : null;
}

async function connectionGrant() {
  const current = new URL(location.href);
  const ticket = grantFromUrl(current);
  if (current.hash) {
    history.replaceState(null, "", entryPath);
    if (!ticket) throw new Error("Invalid terminal link");
    return ticket;
  }
  const response = await fetch(`${entryPath}/ticket`, {
    method: "POST",
    mode: "same-origin",
    credentials: "omit",
    cache: "no-store",
    redirect: "error",
  });
  if (!response.ok) {
    if (interactive && (response.status === 401 || response.status === 403)) {
      const refusal = await response.json();
      const code = refusal?.detail?.error_code;
      if ((response.status === 401 && code === "proof_required") ||
          (response.status === 403 && code === "insufficient_authority")) return null;
    }
    throw new Error("Terminal unavailable");
  }
  const receipt = await response.json();
  const url = new URL(receipt.url);
  const issuedTicket = grantFromUrl(url);
  if (
    receipt.mode !== mode || url.origin !== current.origin || url.pathname !== entryPath ||
    url.username || url.password || url.search || !issuedTicket
  ) throw new Error("Invalid terminal link");
  return issuedTicket;
}

function showDisconnected(message) {
  status.textContent = message;
  restart.hidden = false;
}

function connect(ticket) {
  const url = new URL(`${entryPath}/stream`, location.origin);
  url.protocol = location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(url);
  socket.binaryType = "arraybuffer";
  let ready = false;
  let terminal;
  let resizeObserver;

  function sendControl(message) {
    if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(message));
  }

  function sendInput(bytes) {
    if (!ready || socket.readyState !== WebSocket.OPEN) return;
    if (bytes.length + socket.bufferedAmount > maxBufferedInput) {
      socket.close(1009);
      return;
    }
    for (let offset = 0; offset < bytes.length; offset += maxInputFrame) {
      socket.send(bytes.subarray(offset, offset + maxInputFrame));
    }
  }

  function showTerminal({ cols, rows }) {
    if (ready || !Number.isInteger(cols) || cols < 1 || !Number.isInteger(rows) || rows < 1) {
      socket.close(1002);
      return;
    }
    terminal = new Terminal({
      cols,
      rows,
      disableStdin: !interactive,
      cursorBlink: interactive,
      fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace",
      fontSize: 14,
      theme: { background: "#13171c", foreground: "#ebeff3", cursor: "#b3def6" },
    });
    terminal.open(terminalHost);
    ready = true;
    status.textContent = "Connected";

    if (interactive) {
      const fit = new FitAddon();
      terminal.loadAddon(fit);
      terminal.onData((data) => sendInput(encoder.encode(data)));
      terminal.onBinary((data) => sendInput(Uint8Array.from(data, (byte) => byte.charCodeAt(0))));
      terminal.onResize(({ cols, rows }) => sendControl({ type: "resize", cols, rows }));
      resizeObserver = new ResizeObserver(() => fit.fit());
      resizeObserver.observe(terminalHost);
      fit.fit();
      terminal.focus();
    }
  }

  socket.addEventListener("open", () => sendControl({ type: "grant", ticket }), { once: true });
  socket.addEventListener("message", ({ data }) => {
    if (data instanceof ArrayBuffer) {
      if (ready) terminal.write(new Uint8Array(data), () => sendControl({ type: "ack", bytes: data.byteLength }));
      return;
    }
    try {
      const message = JSON.parse(data);
      if (message.type === "ready") showTerminal(message);
    } catch {
      socket.close(1002);
    }
  });
  socket.addEventListener("close", () => {
    resizeObserver?.disconnect();
    if (terminal) terminal.options.disableStdin = true;
    showDisconnected(ready ? "Disconnected" : "Terminal unavailable");
    ready = false;
  }, { once: true });
  window.addEventListener("pagehide", () => socket.close(), { once: true });
}

async function initialize() {
  try {
    const ticket = await connectionGrant();
    if (ticket) {
      restart.hidden = true;
      restart.href = entryPath;
      restart.textContent = "Open again";
      status.textContent = "Connecting…";
      connect(ticket);
    } else {
      showDisconnected("Administrator sign-in required");
      restart.href = `${entryPath}/login`;
      restart.textContent = "Sign in";
      window.addEventListener("hashchange", initialize, { once: true });
    }
  } catch {
    showDisconnected("Terminal unavailable");
  }
}

await initialize();
