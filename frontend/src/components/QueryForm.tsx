import { useRef, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";

interface QueryFormProps {
  loading: boolean;
  openrouterConfigured: boolean;
  onSubmitText: (query: string) => void;
  onSubmitImage: (file: File, prompt: string, mode: "plan" | "analyze") => void;
}

const EXAMPLE_QUERIES = [
  "Plan a 3-day budget Your Name pilgrimage in Tokyo and Hida Takayama",
  "Weekend Bocchi the Rock! pilgrimage in Shimokitazawa",
  "2-day Sound! Euphonium trip in Uji, Kyoto",
  "Attack on Titan pilgrimage in Tokyo and Hita for 2 days",
];

export function QueryForm({
  loading,
  openrouterConfigured,
  onSubmitText,
  onSubmitImage,
}: QueryFormProps) {
  const [tab, setTab] = useState<"text" | "image">("text");
  const [query, setQuery] = useState("");
  const [imagePrompt, setImagePrompt] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleTextSubmit = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || loading) return;
    onSubmitText(trimmed);
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setSelectedFile(file);
    setPreviewUrl(file ? URL.createObjectURL(file) : null);
  };

  const handleImageAction = (mode: "plan" | "analyze") => {
    if (!selectedFile || loading) return;
    onSubmitImage(selectedFile, imagePrompt.trim(), mode);
  };

  return (
    <section className="card form-card">
      <div className="tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={tab === "text"}
          className={`tab ${tab === "text" ? "active" : ""}`}
          onClick={() => setTab("text")}
        >
          Text Request
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "image"}
          className={`tab ${tab === "image" ? "active" : ""}`}
          onClick={() => setTab("image")}
        >
          Screenshot Lookup (VLM)
        </button>
      </div>

      {tab === "text" ? (
        <form onSubmit={handleTextSubmit} className="stack">
          <label className="field-label" htmlFor="pilgrimage-query">
            Describe your anime pilgrimage (English or 日本語)
          </label>
          <textarea
            id="pilgrimage-query"
            rows={3}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. Plan a 3-day Your Name pilgrimage in Tokyo and Hida Takayama..."
            disabled={loading}
          />
          <div className="presets">
            {EXAMPLE_QUERIES.map((example) => (
              <button
                key={example}
                type="button"
                className="chip"
                onClick={() => setQuery(example)}
                disabled={loading}
              >
                {example}
              </button>
            ))}
          </div>
          <div className="actions">
            <button type="submit" className="btn-primary" disabled={loading || !query.trim()}>
              {loading ? "Planning itinerary..." : "Generate Pilgrimage Plan"}
            </button>
          </div>
        </form>
      ) : (
        <div className="stack">
          {!openrouterConfigured && (
            <div className="notice warning">
              Set <code>OPENROUTER_API_KEY</code> in <code>.env</code> to enable VLM screenshot
              identification.
            </div>
          )}
          <label className="field-label" htmlFor="screenshot-upload">
            Upload an anime screenshot or real-world pilgrimage photo (PNG, JPEG, WEBP)
          </label>
          <div
            className="dropzone"
            onClick={() => fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
            }}
          >
            <input
              ref={fileInputRef}
              id="screenshot-upload"
              type="file"
              accept="image/png,image/jpeg,image/webp,image/gif"
              onChange={handleFileChange}
              hidden
            />
            {previewUrl ? (
              <div className="preview-wrap">
                <img src={previewUrl} alt="Uploaded anime scene preview" className="preview-img" />
                <span className="muted">{selectedFile?.name} (click to replace)</span>
              </div>
            ) : (
              <span className="muted">Click to choose an anime screenshot (max 10 MB)</span>
            )}
          </div>

          <label className="field-label" htmlFor="image-prompt">
            Optional trip preferences or hint
          </label>
          <input
            id="image-prompt"
            type="text"
            value={imagePrompt}
            onChange={(e) => setImagePrompt(e.target.value)}
            placeholder="e.g. 2 days budget trip, or hint about the episode/city"
            disabled={loading}
          />

          <div className="actions">
            <button
              type="button"
              className="btn-primary"
              disabled={loading || !selectedFile || !openrouterConfigured}
              onClick={() => handleImageAction("plan")}
            >
              {loading ? "Analyzing & planning..." : "Identify & Plan Full Trip"}
            </button>
            <button
              type="button"
              className="btn-secondary"
              disabled={loading || !selectedFile || !openrouterConfigured}
              onClick={() => handleImageAction("analyze")}
            >
              Identify Scene Only
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
