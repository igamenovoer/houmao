import type { GraphicArtifact } from "./types";

interface GraphicViewProps {
  artifact: GraphicArtifact;
  paneId: string;
}

const UNSAFE_INLINE_PATTERNS = [
  /<\s*script\b/i,
  /\son[a-z0-9_-]+\s*=/i,
  /javascript\s*:/i,
  /<\s*iframe\b/i,
];

export function GraphicView({ artifact, paneId }: GraphicViewProps) {
  const altText = artifact.altText || artifact.description || artifact.title;
  if (artifact.format !== "svg") {
    return (
      <div className="graphic-fallback" data-testid={`unsupported-graphic-${paneId}`}>
        Unsupported graphic format: {artifact.format}
      </div>
    );
  }
  const content = typeof artifact.content === "string" ? artifact.content : "";
  const safe = sanitizeSvg(content);
  if (!safe) {
    return (
      <div className="graphic-fallback" data-testid={`unsupported-graphic-${paneId}`}>
        Unsupported graphic format: unsafe_svg
      </div>
    );
  }
  return (
    <figure className="graphic" data-testid={`graphic-${paneId}`}>
      <figcaption>
        <strong>{artifact.title}</strong>
        <span>{altText}</span>
      </figcaption>
      <div className="graphic-svg" role="img" aria-label={altText} dangerouslySetInnerHTML={{ __html: safe }} />
    </figure>
  );
}

function sanitizeSvg(content: string): string | null {
  if (!content.toLowerCase().includes("<svg")) {
    return null;
  }
  if (UNSAFE_INLINE_PATTERNS.some((pattern) => pattern.test(content))) {
    return null;
  }
  return content;
}
