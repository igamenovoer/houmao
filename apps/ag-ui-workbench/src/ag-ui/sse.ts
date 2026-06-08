import type { AgUiEvent, RawTimelineEntry } from "./types";

interface SseFrameHandlers {
  onEvent: (event: AgUiEvent, raw: RawTimelineEntry) => void;
  onComment?: (raw: string) => void;
  onParseError: (raw: RawTimelineEntry) => void;
}

export class SseParser {
  private m_buffer = "";
  private m_counter = 0;

  constructor(private readonly m_handlers: SseFrameHandlers) {}

  feed(chunk: string): void {
    this.m_buffer += chunk.replace(/\r\n/g, "\n");
    while (true) {
      const boundary = this.m_buffer.indexOf("\n\n");
      if (boundary < 0) {
        return;
      }
      const frame = this.m_buffer.slice(0, boundary);
      this.m_buffer = this.m_buffer.slice(boundary + 2);
      this.processFrame(frame);
    }
  }

  finish(): void {
    if (this.m_buffer.trim()) {
      this.processFrame(this.m_buffer);
    }
    this.m_buffer = "";
  }

  private processFrame(frame: string): void {
    const lines = frame.split("\n");
    if (lines.every((line) => line.startsWith(":") || line.trim() === "")) {
      this.m_handlers.onComment?.(frame);
      return;
    }
    const dataLines = lines
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).replace(/^ /, ""));
    if (dataLines.length === 0) {
      return;
    }
    const data = dataLines.join("\n");
    const raw = this.rawEntry(frame, data);
    try {
      const parsed = JSON.parse(data) as unknown;
      if (!isAgUiEvent(parsed)) {
        this.m_handlers.onParseError({
          ...raw,
          parseError: "SSE data is JSON but not an AG-UI event object.",
        });
        return;
      }
      this.m_handlers.onEvent(parsed, { ...raw, event: parsed });
    } catch (error) {
      this.m_handlers.onParseError({
        ...raw,
        parseError: error instanceof Error ? error.message : "SSE JSON parse failed.",
      });
    }
  }

  private rawEntry(raw: string, data: string): RawTimelineEntry {
    this.m_counter += 1;
    return {
      id: `raw-${Date.now()}-${this.m_counter}`,
      receivedAt: new Date().toISOString(),
      raw,
      data,
    };
  }
}

function isAgUiEvent(value: unknown): value is AgUiEvent {
  return typeof value === "object" && value !== null && typeof (value as { type?: unknown }).type === "string";
}
