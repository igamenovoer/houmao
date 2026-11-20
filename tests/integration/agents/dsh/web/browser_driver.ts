/** Test-only native browser driver. Private sign-in data never enters its output. */
import { readFile, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { createInterface } from "node:readline";
import { chromium, type Browser, type BrowserContext, type Page } from "playwright";

type Command = {
  action: "connect" | "select" | "new" | "reload" | "model" | "submit" | "draft" | "answer" | "contains" | "click" | "stop" | "close";
  connection_file?: string;
  session_id?: string;
  text?: string;
  name?: string;
};

let browser: Browser | undefined;
let context: BrowserContext | undefined;
let page: Page | undefined;
let selected: string | undefined;
let stage = "initial";
let diagnosticDirectory: string | undefined;

function installedBrowser(): string {
  const explicit = process.env.HOUMAO_PLAYWRIGHT_CHROMIUM_EXECUTABLE;
  if (explicit !== undefined) {
    if (!existsSync(explicit)) throw new Error("missing_browser_executable");
    return explicit;
  }
  const bundled = chromium.executablePath();
  if (existsSync(bundled)) return bundled;
  // Bun's globally resolved API and bunx's CLI cache can use different patch
  // versions. Reuse the installed browser bundle instead of downloading one.
  const cache = join(homedir(), ".cache/ms-playwright");
  const candidates = [...new Bun.Glob("chromium-*/*/chrome").scanSync({ cwd: cache, absolute: true })];
  candidates.sort((left, right) => right.localeCompare(left, undefined, { numeric: true }));
  if (candidates.length === 0) throw new Error("missing_browser_executable");
  return candidates[0];
}

function requirePage(): Page {
  if (page === undefined) throw new Error("not_connected");
  return page;
}

async function selectSession(sessionId: string): Promise<void> {
  if (!/^[A-Za-z0-9_-]+$/.test(sessionId)) throw new Error("invalid_session");
  const target = requirePage().locator(`[data-row-key="session:${sessionId}"]`);
  const collapsed = requirePage().locator('[data-row-key^="workspace:"][aria-expanded=false]');
  for (let count = await collapsed.count(); count > 0; count--) {
    await collapsed.first().click();
  }
  await target.waitFor({ state: "visible" });
  await target.click();
  await requirePage().waitForFunction(
    (id) => document.querySelector(`[data-row-key="session:${id}"]`)?.getAttribute("aria-selected") === "true",
    sessionId,
  );
  selected = sessionId;
}

async function execute(command: Command): Promise<Record<string, unknown>> {
  stage = command.action;
  switch (command.action) {
    case "connect": {
      stage = "descriptor";
      if (page !== undefined || command.connection_file === undefined) throw new Error("invalid_connect");
      const connection = JSON.parse(await readFile(command.connection_file, "utf8"));
      diagnosticDirectory = dirname(command.connection_file);
      const origin = new URL(connection.origin);
      if (origin.protocol !== "http:" || !["127.0.0.1", "localhost", "[::1]"].includes(origin.hostname)
        || origin.username || origin.password || origin.search || origin.hash || origin.pathname !== "/") {
        throw new Error("invalid_origin");
      }
      let signIn: URL;
      if (connection.gateway_entry_url === undefined) {
        if (typeof connection.launch_token !== "string" || !connection.launch_token) throw new Error("missing_token");
        signIn = new URL(origin);
        signIn.searchParams.set("token", connection.launch_token);
      } else {
        signIn = new URL(connection.gateway_entry_url);
        if (signIn.protocol !== "http:" || signIn.hostname !== "127.0.0.1"
          || signIn.username || signIn.password || signIn.search || signIn.hash
          || signIn.pathname !== "/v1/web/enter" || connection.launch_token !== undefined) {
          throw new Error("invalid_gateway_entry");
        }
      }
      stage = "browser_launch";
      browser = await chromium.launch({ headless: true, executablePath: installedBrowser() });
      context = await browser.newContext({ locale: "en-US", viewport: { width: 1440, height: 1000 } });
      page = await context.newPage();
      page.setDefaultTimeout(30_000);
      stage = "sign_in";
      await page.goto(signIn.toString(), { waitUntil: "domcontentloaded" });
      await page.waitForURL((url) => url.origin === origin.origin && url.search === "" && url.hash === "");
      stage = "native_onboarding";
      await page.locator('[data-row-key^="workspace:"]').first().waitFor({ state: "visible" });
      const notice = page.getByRole("dialog", { name: "Preview Notice", exact: true });
      try {
        await notice.waitFor({ state: "visible", timeout: 2_000 });
        await notice.getByRole("button", { name: "Continue", exact: true }).click();
        await notice.waitFor({ state: "hidden" });
      } catch {
        if (await notice.isVisible()) throw new Error("onboarding_not_dismissed");
      }
      const credentialNotice = page.getByRole("dialog", { name: "Add an API key to get started", exact: true });
      try {
        await credentialNotice.waitFor({ state: "visible", timeout: 2_000 });
        await credentialNotice.getByRole("button", { name: "Configure later", exact: true }).click();
        await credentialNotice.waitFor({ state: "hidden" });
      } catch {
        if (await credentialNotice.isVisible()) throw new Error("credential_onboarding_not_dismissed");
      }
      stage = "native_selection";
      await selectSession(connection.native_session_id);
      return { ok: true, origin: origin.origin, session_id: selected, clean_url: true, browser_version: browser.version() };
    }
    case "select":
      await selectSession(command.session_id ?? "");
      return { ok: true, session_id: selected };
    case "new": {
      const previous = selected;
      await requirePage().locator('[data-row-key^="workspace:"]:not([data-row-key="workspace:"])').first().hover();
      await requirePage().getByRole("button", { name: /^New session in / }).first().click();
      await requirePage().waitForFunction(
        (id) => {
          const key = document.querySelector('[data-row-key^="session:"][aria-selected=true]')?.getAttribute("data-row-key");
          return key !== undefined && key !== null && key !== `session:${id}`;
        }, previous,
      );
      const key = await requirePage().locator('[data-row-key^="session:"][aria-selected=true]').getAttribute("data-row-key");
      if (key === null) throw new Error("missing_new_selection");
      selected = key.slice("session:".length);
      return { ok: true, session_id: selected };
    }
    case "reload":
      await requirePage().reload({ waitUntil: "domcontentloaded" });
      if (selected !== undefined) await selectSession(selected);
      return { ok: true, session_id: selected };
    case "model":
      await requirePage().getByRole("button", { name: /^Select model,/ }).click();
      await requirePage().getByRole("menuitem", { name: /^Model(?:\s|$)/ }).click();
      await requirePage().getByRole("menuitemradio", { name: command.name ?? "", exact: true }).click();
      await requirePage().waitForFunction((name) => document.querySelector('[aria-label^="Select model,"]')?.getAttribute("aria-label")?.includes(name ?? ""), command.name);
      return { ok: true, session_id: selected };
    case "submit":
    case "draft": {
      const active = requirePage();
      if (selected === undefined) throw new Error("missing_selection");
      const row = active.locator(`[data-row-key="session:${selected}"]`);
      if (await row.getAttribute("aria-selected") !== "true") throw new Error("selection_changed");
      const editor = active.locator("[data-composer-input][contenteditable=true]");
      await editor.fill(command.text ?? "");
      if (command.action === "submit") await editor.press("Enter");
      return { ok: true, session_id: selected };
    }
    case "contains":
      await requirePage().getByText(command.text ?? "", { exact: false }).filter({ visible: true }).first().waitFor({ state: "visible" });
      return { ok: true };
    case "answer": {
      const option = requirePage().getByRole("radio", { name: command.name ?? "", exact: true });
      await option.click();
      await option.press("Enter");
      return { ok: true, session_id: selected };
    }
    case "click":
      await requirePage().getByRole("button", { name: command.name ?? "", exact: true }).click();
      return { ok: true };
    case "stop":
      await requirePage().getByRole("button", { name: /^(Stop generating|停止生成)$/ }).click();
      return { ok: true, session_id: selected };
    case "close":
      await context?.close();
      await browser?.close();
      context = undefined;
      browser = undefined;
      page = undefined;
      selected = undefined;
      return { ok: true };
    default:
      throw new Error("unknown_action");
  }
}

const lines = createInterface({ input: process.stdin, crlfDelay: Infinity });
try {
  for await (const line of lines) {
    let action = "parse";
    try {
      const command: Command = JSON.parse(line);
      action = command.action;
      process.stdout.write(JSON.stringify(await execute(command)) + "\n");
    } catch (error) {
      // Playwright errors can include a navigation URL or page text. Never echo them.
      if (diagnosticDirectory !== undefined) {
        await writeFile(join(diagnosticDirectory, "browser-error.txt"), String(error), { mode: 0o600 });
        if (page !== undefined) await writeFile(join(diagnosticDirectory, "browser-dom.html"), await page.content(), { mode: 0o600 });
      }
      process.stdout.write(JSON.stringify({ ok: false, action, stage, error: "browser_action_failed" }) + "\n");
    }
  }
} finally {
  await context?.close();
  await browser?.close();
}
