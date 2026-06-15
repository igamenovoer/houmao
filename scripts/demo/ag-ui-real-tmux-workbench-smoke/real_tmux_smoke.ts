import { execFile } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { promisify } from "node:util";

import { chromium, type Locator, type Page } from "playwright";

const execFileAsync = promisify(execFile);

interface TerminalDiagnostics {
  tmuxPaneSize: string;
  terminalHost: BoxMetrics | null;
  xterm: BoxMetrics | null;
  xtermScreen: BoxMetrics | null;
  xtermRows: BoxMetrics | null;
  dataset: {
    cols?: string;
    rows?: string;
  };
  renderedRowCount: number;
}

interface BoxMetrics {
  width: number;
  height: number;
  top: number;
  left: number;
}

const workbenchUrl = process.env.HMWB_WORKBENCH_URL?.trim() || "http://127.0.0.1:5177";
const sessionName = requiredEnv("HMWB_TMUX_SESSION");
const evidenceDir = path.resolve(
  process.cwd(),
  process.env.HMWB_REAL_TMUX_EVIDENCE_DIR?.trim() ||
    `../../tmp/ag-ui-real-tmux-smoke-${new Date().toISOString().replace(/[:.]/g, "-")}`,
);

await mkdir(evidenceDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 820 } });

try {
  await page.goto(workbenchUrl);
  await page.getByTestId("add-tmux-pane").click();
  const houmaoOnly = page.getByTestId("tmux-houmao-only-tmux-1");
  if (await houmaoOnly.isChecked()) {
    await houmaoOnly.uncheck();
  }
  await page.getByTestId("tmux-picker-toggle-tmux-1").click();
  await page.getByTestId("tmux-search-tmux-1").fill(sessionName);
  await page.getByTestId(`tmux-session-${safeTestToken(sessionName)}`).click();

  const terminal = page.getByTestId("tmux-terminal-tmux-1");
  await waitForMeasuredTerminal(terminal);
  await page.screenshot({ path: path.join(evidenceDir, "before-scroll.png"), fullPage: true });
  const beforeScroll = await terminalDiagnostics(page);

  await terminal.hover();
  await page.mouse.wheel(0, -2400);
  await page.waitForTimeout(350);
  await page.screenshot({ path: path.join(evidenceDir, "after-scroll.png"), fullPage: true });
  const afterScroll = await terminalDiagnostics(page);

  await page.setViewportSize({ width: 1320, height: 900 });
  await waitForMeasuredTerminal(terminal);
  await page.waitForTimeout(350);
  await page.screenshot({ path: path.join(evidenceDir, "after-resize.png"), fullPage: true });
  const afterResize = await terminalDiagnostics(page);

  await writeFile(
    path.join(evidenceDir, "summary.json"),
    `${JSON.stringify(
      {
        workbenchUrl,
        sessionName,
        beforeScroll,
        afterScroll,
        afterResize,
      },
      null,
      2,
    )}\n`,
    "utf8",
  );
  console.log(`real-tmux-workbench-smoke=PASS evidence=${evidenceDir}`);
} finally {
  await browser.close();
}

async function waitForMeasuredTerminal(terminal: Locator): Promise<void> {
  await terminal.waitFor({ state: "visible", timeout: 15_000 });
  await terminal.page().waitForFunction(
    (testId) => {
      const host = document.querySelector<HTMLElement>(`[data-testid="${testId}"]`);
      return Boolean(host?.dataset.tmuxCols && host.dataset.tmuxRows);
    },
    await terminal.getAttribute("data-testid"),
    { timeout: 15_000 },
  );
}

async function terminalDiagnostics(page: Page): Promise<TerminalDiagnostics> {
  const tmuxPaneSize = await currentTmuxPaneSize(sessionName);
  const dom = await page.evaluate(() => {
    const host = document.querySelector<HTMLElement>('[data-testid="tmux-terminal-tmux-1"]');
    const xterm = host?.querySelector<HTMLElement>(".xterm") ?? null;
    const screen = host?.querySelector<HTMLElement>(".xterm-screen") ?? null;
    const rows = host?.querySelector<HTMLElement>(".xterm-rows") ?? null;
    const renderedRows = rows?.querySelectorAll(":scope > div").length ?? 0;
    return {
      terminalHost: box(host),
      xterm: box(xterm),
      xtermScreen: box(screen),
      xtermRows: box(rows),
      dataset: {
        cols: host?.dataset.tmuxCols,
        rows: host?.dataset.tmuxRows,
      },
      renderedRowCount: renderedRows,
    };

    function box(element: HTMLElement | null): BoxMetrics | null {
      if (!element) {
        return null;
      }
      const rect = element.getBoundingClientRect();
      return {
        width: rect.width,
        height: rect.height,
        top: rect.top,
        left: rect.left,
      };
    }
  });
  return {
    tmuxPaneSize,
    ...dom,
  };
}

async function currentTmuxPaneSize(targetSession: string): Promise<string> {
  try {
    const { stdout } = await execFileAsync("tmux", [
      "list-panes",
      "-t",
      targetSession,
      "-F",
      "#{pane_width}x#{pane_height}",
    ]);
    return stdout.split("\n").find(Boolean)?.trim() || "";
  } catch (error) {
    return `tmux list-panes failed: ${errorMessage(error)}`;
  }
}

function requiredEnv(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) {
    throw new Error(`Set ${name}.`);
  }
  return value;
}

function safeTestToken(value: string): string {
  return (
    value
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9_.-]+/g, "-")
      .replace(/^-+|-+$/g, "") || "session"
  );
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
