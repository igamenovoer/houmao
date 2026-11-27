/** Exercise the real bundled browser transport on an isolated tmux fixture. */
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const playwright = await import("playwright").catch(() => null);
if (!playwright) process.exit(77);
const { chromium } = playwright;

const [origin, signerPath] = process.argv.slice(2);
const viewPath = "/v1/terminal/view";
const interactPath = "/v1/admin/terminal/attach";
const browserCache = join(homedir(), ".cache/ms-playwright");
const explicitBrowser = process.env.HOUMAO_PLAYWRIGHT_CHROMIUM_EXECUTABLE;
const fallback = existsSync(browserCache)
  ? [...new Bun.Glob("chromium-*/*/chrome").scanSync({ cwd: browserCache, absolute: true })]
      .sort((a, b) => b.localeCompare(a, undefined, { numeric: true }))[0]
  : undefined;
const executablePath = explicitBrowser ?? (
  existsSync(chromium.executablePath()) ? chromium.executablePath() : fallback
);
if (!executablePath || !existsSync(executablePath)) process.exit(77);
const browser = await chromium.launch({ executablePath });

function verify(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

try {
  const context = await browser.newContext({ viewport: { width: 1100, height: 680 } });
  const foreign: string[] = [];
  await context.route("**/*", async (route) => {
    const address = new URL(route.request().url());
    if (address.origin === origin) await route.continue();
    else {
      foreign.push(address.origin);
      await route.abort();
    }
  });
  const deniedAdmin = await context.request.post(`${origin}${interactPath}/ticket`);
  verify(deniedAdmin.status() === 401 || deniedAdmin.status() === 403, "Unsigned admin ticket was issued");
  const view = await context.newPage();
  const browserErrors: string[] = [];
  view.on("pageerror", (error) => browserErrors.push(error.message));
  view.setDefaultTimeout(8000);
  await view.goto(origin + viewPath);
  await view.locator("#connection").getByText("Connected").waitFor();
  await view.locator(".xterm-rows").getByText("owned-terminal", { exact: false }).waitFor();
  verify(await view.locator("#mode").textContent() === "Read-only", "Viewer mode label differs");
  verify(await view.locator(".xterm-helper-textarea").getAttribute("aria-label") !== null, "Terminal input lacks a label");
  await view.evaluate(async (path) => {
    // Simulate an altered client sending an input frame through the viewer WebSocket.
    const response = await fetch(`${path}/ticket`, { method: "POST" });
    const grant = new URL((await response.json()).url);
    const ticket = new URLSearchParams(grant.hash.slice(1)).get("ticket");
    const url = new URL(`${path}/stream`, location.href);
    url.protocol = "ws:";
    await new Promise<void>((resolve, reject) => {
      const socket = new WebSocket(url);
      socket.addEventListener("open", () => socket.send(JSON.stringify({ type: "grant", ticket })));
      socket.addEventListener("message", ({ data }) => {
        if (typeof data === "string" && JSON.parse(data).type === "ready") {
          socket.send(new TextEncoder().encode("unexpected-viewer-input\r"));
        }
      });
      socket.addEventListener("close", ({ code }) => {
        if (code === 1008) resolve();
        else reject(new Error("Viewer input did not trigger a policy close"));
      });
      setTimeout(() => {
        socket.close();
        reject(new Error("Viewer input was not rejected"));
      }, 5000);
    });
  }, viewPath);
  verify(!((await view.locator(".xterm-rows").textContent()) ?? "").includes("unexpected-viewer-input"), "Read-only input reached tmux");
  await view.close();

  const interactive = await context.newPage();
  interactive.on("pageerror", (error) => browserErrors.push(error.message));
  interactive.setDefaultTimeout(8000);
  await interactive.goto(`${origin}${interactPath}`);
  const signIn = interactive.getByRole("link", { name: "Sign in" });
  await signIn.waitFor();
  verify(await signIn.getAttribute("href") === `${interactPath}/login`, "Incorrect admin login entry");
  await signIn.click();
  await interactive.locator("#key-path").fill(signerPath);
  await interactive.getByRole("button", { name: "Start Login" }).click();
  const signingCommand = interactive.locator("#signing-command");
  await signingCommand.waitFor();
  const approved = Bun.spawnSync(["/bin/sh", "-c", await signingCommand.inputValue()]);
  verify(approved.exitCode === 0, "Generated admin OpenSSH proof was rejected");
  await interactive.locator("#connection").getByText("Connected").waitFor();
  await interactive.locator(".xterm-rows").getByText("owned-terminal", { exact: false }).waitFor();
  verify(interactive.url() === origin + interactPath, "The terminal retained its one-time link secret");
  await interactive.keyboard.type("typed ");
  await interactive.locator(".xterm-helper-textarea").evaluate((node) => {
    const clipboard = new DataTransfer();
    clipboard.setData("text/plain", "paste-café");
    node.dispatchEvent(new ClipboardEvent("paste", { clipboardData: clipboard, bubbles: true, cancelable: true }));
  });
  await interactive.keyboard.press("Enter");
  await interactive.locator(".xterm-rows").getByText("typed paste-café", { exact: false }).waitFor();

  const clientSize = async () => {
    const clients = (await (await context.request.get(`${origin}/health`)).json()) as string;
    return clients.split("\n").find((client) => client && !client.includes("control-mode"))?.split("\t")[0];
  };
  const originalSize = await clientSize();
  verify(originalSize && /^\d+x\d+$/.test(originalSize), "Interactive fixture did not have one active client");
  await interactive.setViewportSize({ width: 710, height: 420 });
  const deadline = Date.now() + 5000;
  let resized = await clientSize();
  while (resized === originalSize && Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, 25));
    resized = await clientSize();
  }
  verify(resized && /^\d+x\d+$/.test(resized) && resized !== originalSize, "Browser resize did not reach tmux");
  await interactive.close();
  verify(foreign.length === 0, "Browser requested an external resource");
  verify(browserErrors.length === 0, browserErrors.join("\n"));
} finally {
  await browser.close();
}
