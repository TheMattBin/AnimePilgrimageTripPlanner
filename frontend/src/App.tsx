import { useEffect, useState } from "react";
import {
  analyzeScreenshot,
  createPlanFromImage,
  createTextPlan,
  fetchHealth,
} from "./api/client";
import { ItineraryView } from "./components/ItineraryView";
import { PilgrimageMap } from "./components/PilgrimageMap";
import { QueryForm } from "./components/QueryForm";
import type { GeneratedResponse, HealthResponse, SceneAnalysis } from "./types/api";

export function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [response, setResponse] = useState<GeneratedResponse | null>(null);
  const [standaloneScene, setStandaloneScene] = useState<SceneAnalysis | null>(null);

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  const handleTextSubmit = async (query: string) => {
    setLoading(true);
    setErrorMessage(null);
    setStandaloneScene(null);
    try {
      const result = await createTextPlan(query);
      setResponse(result);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Unexpected request error");
    } finally {
      setLoading(false);
    }
  };

  const handleImageSubmit = async (
    file: File,
    prompt: string,
    mode: "plan" | "analyze"
  ) => {
    setLoading(true);
    setErrorMessage(null);
    try {
      if (mode === "analyze") {
        setResponse(null);
        const scene = await analyzeScreenshot(file, prompt);
        setStandaloneScene(scene);
      } else {
        setStandaloneScene(null);
        const result = await createPlanFromImage(file, prompt);
        setResponse(result);
      }
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Unexpected image analysis error");
    } finally {
      setLoading(false);
    }
  };

  const itineraries = response?.travel_plan?.daily_itineraries ?? [];
  const fallbackLocations = response?.locations ?? [];

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <h1>Seichi Planner</h1>
          <p className="muted">
            Agentic Anime Pilgrimage Trip Planner · LangGraph + OpenRouter LLM/VLM
          </p>
        </div>
        <div className="status-pills">
          {health ? (
            <>
              <span className={`pill ${health.openrouter_configured ? "ok" : "warn"}`}>
                OpenRouter: {health.openrouter_configured ? health.llm_model : "fallback mode"}
              </span>
              <span className="pill">Search: {health.search_provider}</span>
            </>
          ) : (
            <span className="pill warn">API offline (start uv run pilgrimage-api)</span>
          )}
        </div>
      </header>

      <main className="main-grid">
        <div className="left-col">
          <QueryForm
            loading={loading}
            openrouterConfigured={health?.openrouter_configured ?? false}
            onSubmitText={handleTextSubmit}
            onSubmitImage={handleImageSubmit}
          />
          {errorMessage && (
            <div className="card notice error">
              <strong>Error:</strong> {errorMessage}
            </div>
          )}
          <ItineraryView response={response} standaloneScene={standaloneScene} />
        </div>

        <aside className="right-col">
          <PilgrimageMap itineraries={itineraries} fallbackLocations={fallbackLocations} />
        </aside>
      </main>
    </div>
  );
}
