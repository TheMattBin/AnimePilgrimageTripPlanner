import { useState } from "react";
import type { GeneratedResponse } from "../types/api";

interface MarkdownExportProps {
  response: GeneratedResponse;
}

function triggerDownload(filename: string, content: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function MarkdownExport({ response }: MarkdownExportProps) {
  const [copied, setCopied] = useState(false);

  const slug = response.title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_|_$/g, "") || "pilgrimage_plan";

  const handleCopy = async () => {
    await navigator.clipboard.writeText(response.markdown_content || response.main_content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="export-bar">
      <button type="button" className="btn-secondary" onClick={handleCopy}>
        {copied ? "Copied Markdown!" : "Copy Markdown"}
      </button>
      <button
        type="button"
        className="btn-secondary"
        onClick={() =>
          triggerDownload(
            `${slug}.md`,
            response.markdown_content || response.main_content,
            "text/markdown;charset=utf-8"
          )
        }
      >
        Download .md
      </button>
      <button
        type="button"
        className="btn-secondary"
        onClick={() =>
          triggerDownload(
            `${slug}.json`,
            JSON.stringify(response, null, 2),
            "application/json;charset=utf-8"
          )
        }
      >
        Download .json
      </button>
    </div>
  );
}
