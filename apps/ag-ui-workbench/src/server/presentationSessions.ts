import {
  safeMetadata,
  type PresentationSessionCreateRequest,
  type PresentationSessionView,
} from "../shared/workbenchProtocol";

export class PresentationSessionRegistry {
  private readonly m_sessions = new Map<string, PresentationSessionView>();
  private m_nextSessionIndex = 1;

  create(request: PresentationSessionCreateRequest = {}): PresentationSessionView {
    const now = new Date().toISOString();
    const session: PresentationSessionView = {
      sessionId: `presentation-${this.m_nextSessionIndex++}`,
      paneId: request.paneId?.trim() || null,
      kind: request.kind?.trim() || "generic",
      metadata: request.metadata ? safeMetadata(request.metadata) : {},
      createdAtUtc: now,
      updatedAtUtc: now,
      owner: "workbench-local-server",
    };
    this.m_sessions.set(session.sessionId, session);
    return { ...session, metadata: { ...session.metadata } };
  }

  list(): PresentationSessionView[] {
    return [...this.m_sessions.values()].map((session) => ({
      ...session,
      metadata: { ...session.metadata },
    }));
  }

  get(sessionId: string): PresentationSessionView | null {
    const session = this.m_sessions.get(sessionId);
    return session ? { ...session, metadata: { ...session.metadata } } : null;
  }

  dispose(sessionId: string): boolean {
    return this.m_sessions.delete(sessionId);
  }

  disposePane(paneId: string): number {
    let removed = 0;
    for (const [sessionId, session] of this.m_sessions.entries()) {
      if (session.paneId === paneId) {
        this.m_sessions.delete(sessionId);
        removed += 1;
      }
    }
    return removed;
  }

  clear(): void {
    this.m_sessions.clear();
  }

  diagnostics(): {
    owner: "workbench-local-server";
    sessionCount: number;
    paneCount: number;
    datasourceContentsStoredInBrowser: false;
  } {
    return {
      owner: "workbench-local-server",
      sessionCount: this.m_sessions.size,
      paneCount: new Set([...this.m_sessions.values()].map((session) => session.paneId).filter(Boolean))
        .size,
      datasourceContentsStoredInBrowser: false,
    };
  }
}
