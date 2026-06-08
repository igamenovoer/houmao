import { chromium, type Page } from "playwright";

const endpoint = "http://houmao-ag-ui.local/v1/ag-ui/runs";

const sseBody = [
  {
    type: "RUN_STARTED",
    threadId: "browser-thread",
    runId: "browser-run-1",
  },
  {
    type: "TEXT_MESSAGE_START",
    messageId: "browser-run-1:graphic-parent:0",
  },
  {
    type: "TOOL_CALL_START",
    toolCallId: "browser-run-1:graphic:0",
    toolCallName: "houmao_render_graphic",
    parentMessageId: "browser-run-1:graphic-parent:0",
  },
  {
    type: "TOOL_CALL_ARGS",
    toolCallId: "browser-run-1:graphic:0",
    delta: JSON.stringify({
      title: "Browser Smoke Graphic",
      format: "svg",
      content:
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 40"><rect width="80" height="40"></rect></svg>',
      altText: "Browser smoke SVG",
      metadata: { fixture: "ag-ui-browser-smoke" },
    }),
  },
  {
    type: "TOOL_CALL_END",
    toolCallId: "browser-run-1:graphic:0",
  },
  {
    type: "TEXT_MESSAGE_END",
    messageId: "browser-run-1:graphic-parent:0",
  },
  {
    type: "RUN_FINISHED",
    threadId: "browser-thread",
    runId: "browser-run-1",
  },
]
  .map((payload) => `data: ${JSON.stringify(payload)}\n\n`)
  .join("");

async function main() {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    await page.route(endpoint, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream; charset=utf-8",
        body: sseBody,
      });
    });

    await page.setContent(`
      <!doctype html>
      <html>
        <body>
          <main id="app"></main>
          <script>
            const endpoint = ${JSON.stringify(endpoint)};
            const app = document.getElementById("app");
            const tools = new Map();

            function payloadsFromSse(text) {
              return text
                .split("\\n\\n")
                .filter((frame) => frame.startsWith("data: "))
                .map((frame) => JSON.parse(frame.slice("data: ".length)));
            }

            function renderGraphic(args) {
              const section = document.createElement("section");
              section.dataset.testid = "graphic";
              const title = document.createElement("h1");
              title.dataset.testid = "graphic-title";
              title.textContent = args.title;
              const alt = document.createElement("p");
              alt.dataset.testid = "graphic-alt";
              alt.textContent = args.altText || args.title;
              section.append(title, alt);
              if (args.format === "svg" && typeof args.content === "string") {
                const holder = document.createElement("div");
                holder.dataset.testid = "graphic-svg";
                holder.innerHTML = args.content;
                section.append(holder);
              }
              app.append(section);
            }

            async function runSmoke() {
              const response = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  threadId: "browser-thread",
                  runId: "browser-run-1",
                  state: {},
                  messages: [{ id: "message-1", role: "user", content: "render" }],
                  tools: [],
                  context: [],
                  forwardedProps: {},
                }),
              });
              if (!response.ok) {
                throw new Error("AG-UI smoke endpoint returned " + response.status);
              }
              for (const payload of payloadsFromSse(await response.text())) {
                if (payload.type === "TOOL_CALL_START") {
                  tools.set(payload.toolCallId, {
                    name: payload.toolCallName,
                    argsText: "",
                  });
                } else if (payload.type === "TOOL_CALL_ARGS") {
                  tools.get(payload.toolCallId).argsText += payload.delta || "";
                } else if (payload.type === "TOOL_CALL_END") {
                  const tool = tools.get(payload.toolCallId);
                  if (tool.name === "houmao_render_graphic") {
                    renderGraphic(JSON.parse(tool.argsText));
                  }
                }
              }
            }

            runSmoke().catch((error) => {
              app.textContent = error.message;
            });
          </script>
        </body>
      </html>
    `);

    await page.waitForSelector("[data-testid='graphic-svg'] svg", { state: "visible" });
    await assertText(page, "[data-testid='graphic-title']", "Browser Smoke Graphic");
    await assertText(page, "[data-testid='graphic-alt']", "Browser smoke SVG");
    console.log("ag-ui-browser-smoke=PASS");
  } finally {
    await browser.close();
  }
}

async function assertText(page: Page, selector: string, expected: string) {
  const text = await page.locator(selector).textContent();
  if (text !== expected) {
    throw new Error(`Expected ${selector} text ${JSON.stringify(expected)}, got ${JSON.stringify(text)}.`);
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
