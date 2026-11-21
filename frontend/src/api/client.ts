import type { GeneratedResponse, HealthResponse, SceneAnalysis } from "../types/api";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: string };
    if (typeof data.detail === "string" && data.detail.trim()) {
      return data.detail;
    }
  } catch {
    // Fall through to status text
  }
  return `Request failed with HTTP ${response.status}`;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/api/health`);
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return (await response.json()) as HealthResponse;
}

export async function createTextPlan(query: string): Promise<GeneratedResponse> {
  const response = await fetch(`${API_BASE}/api/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return (await response.json()) as GeneratedResponse;
}

export async function analyzeScreenshot(
  file: File,
  hint = ""
): Promise<SceneAnalysis> {
  const form = new FormData();
  form.append("image", file);
  form.append("hint", hint);

  const response = await fetch(`${API_BASE}/api/scene/analyze`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return (await response.json()) as SceneAnalysis;
}

export async function createPlanFromImage(
  file: File,
  prompt = ""
): Promise<GeneratedResponse> {
  const form = new FormData();
  form.append("image", file);
  form.append("prompt", prompt);

  const response = await fetch(`${API_BASE}/api/plan/from-image`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return (await response.json()) as GeneratedResponse;
}
