import { useRenderTool } from "@copilotkit/react-core";

type HoumaoGraphicFormat = "svg" | "html_fragment" | "image_url" | "image_data_uri" | "chart_json";

type HoumaoGraphicArtifact = {
  title: string;
  description?: string | null;
  format: HoumaoGraphicFormat;
  content?: unknown;
  contentUrl?: string | null;
  altText?: string | null;
  metadata?: Record<string, unknown>;
};

export function HoumaoGraphicRenderer() {
  useRenderTool({
    name: "houmao_render_graphic",
    render: ({ args }: { args: HoumaoGraphicArtifact }) => {
      if (args.format === "svg" && typeof args.content === "string") {
        return <div aria-label={args.altText ?? args.title} dangerouslySetInnerHTML={{ __html: args.content }} />;
      }

      if (args.format === "html_fragment" && typeof args.content === "string") {
        return <div aria-label={args.altText ?? args.title} dangerouslySetInnerHTML={{ __html: args.content }} />;
      }

      if (args.format === "image_url" && args.contentUrl) {
        return <img src={args.contentUrl} alt={args.altText ?? args.title} />;
      }

      if (args.format === "image_data_uri" && typeof args.content === "string") {
        return <img src={args.content} alt={args.altText ?? args.title} />;
      }

      if (args.format === "chart_json") {
        return <pre aria-label={args.altText ?? args.title}>{JSON.stringify(args.content, null, 2)}</pre>;
      }

      return null;
    },
  });

  return null;
}
