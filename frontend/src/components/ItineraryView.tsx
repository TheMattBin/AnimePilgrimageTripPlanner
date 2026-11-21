import type { GeneratedResponse, SceneAnalysis } from "../types/api";
import { MarkdownExport } from "./MarkdownExport";

interface ItineraryViewProps {
  response: GeneratedResponse | null;
  standaloneScene: SceneAnalysis | null;
}

function SceneCard({ scene }: { scene: SceneAnalysis }) {
  return (
    <section className="card scene-card">
      <div className="row-between">
        <h2>VLM Scene Identification</h2>
        <span className="badge">Confidence {(scene.confidence * 100).toFixed(0)}%</span>
      </div>
      <div className="scene-grid">
        <div>
          <span className="meta-label">Anime</span>
          <p className="meta-value">
            {scene.identified_anime || "Unidentified"}
            {scene.japanese_title ? ` (${scene.japanese_title})` : ""}
          </p>
        </div>
        <div>
          <span className="meta-label">Landmark Guess</span>
          <p className="meta-value">
            {scene.landmark_guess || "Unknown"}
            {scene.japanese_landmark ? ` (${scene.japanese_landmark})` : ""}
          </p>
        </div>
        <div>
          <span className="meta-label">City / Region</span>
          <p className="meta-value">{scene.city_or_region || "Japan"}</p>
        </div>
      </div>
      {scene.visual_clues.length > 0 && (
        <div className="clue-list">
          {scene.visual_clues.map((clue) => (
            <span key={clue} className="clue-tag">
              {clue}
            </span>
          ))}
        </div>
      )}
      {scene.camera_and_framing_tips && (
        <p className="scene-tip">
          <strong>Photo Framing Tip:</strong> {scene.camera_and_framing_tips}
        </p>
      )}
    </section>
  );
}

export function ItineraryView({ response, standaloneScene }: ItineraryViewProps) {
  const activeScene = response?.scene_analysis ?? standaloneScene;

  if (!response && !activeScene) {
    return null;
  }

  return (
    <div className="stack-lg">
      {activeScene && <SceneCard scene={activeScene} />}

      {response && response.response_type === "clarification" && (
        <section className="card notice warning">
          <h2>{response.title}</h2>
          <p>{response.introduction}</p>
          <ul>
            {response.disambiguation_questions.map((q) => (
              <li key={q}>{q}</li>
            ))}
          </ul>
        </section>
      )}

      {response && response.response_type === "error" && (
        <section className="card notice error">
          <h2>{response.title}</h2>
          <p>{response.introduction}</p>
        </section>
      )}

      {response && response.response_type === "itinerary" && response.travel_plan && (
        <>
          <section className="card summary-card">
            <div className="row-between">
              <div>
                <h2>{response.travel_plan.trip_title}</h2>
                <p className="muted">{response.introduction}</p>
              </div>
              <MarkdownExport response={response} />
            </div>

            <div className="kpi-grid">
              <div className="kpi">
                <span className="meta-label">Destination</span>
                <strong>{response.travel_plan.destination}</strong>
              </div>
              <div className="kpi">
                <span className="meta-label">Duration</span>
                <strong>{response.travel_plan.duration_days} day(s)</strong>
              </div>
              <div className="kpi">
                <span className="meta-label">Spots</span>
                <strong>{response.travel_plan.total_locations}</strong>
              </div>
              <div className="kpi">
                <span className="meta-label">Est. Total ({response.travel_plan.budget_level})</span>
                <strong>
                  ¥{(response.travel_plan.total_estimated_cost.total ?? 0).toLocaleString()}
                </strong>
              </div>
            </div>
          </section>

          {response.travel_plan.daily_itineraries.map((day) => (
            <section key={day.day} className="card day-card">
              <div className="row-between">
                <h3>{day.title || `Day ${day.day}`}</h3>
                <span className="badge">
                  Daily spend: ¥{(day.estimated_cost.total ?? 0).toLocaleString()}
                </span>
              </div>

              {day.notes.length > 0 && (
                <div className="day-notes">
                  {day.notes.map((note) => (
                    <p key={note} className="note-line">
                      {note}
                    </p>
                  ))}
                </div>
              )}

              <ol className="stop-list">
                {day.stops.map((stop) => (
                  <li key={`${day.day}-${stop.order}`} className="stop-item">
                    <div className="stop-header">
                      <span className="stop-time">
                        {stop.arrival_time}–{stop.departure_time}
                      </span>
                      <strong>
                        {stop.location.name}
                        {stop.location.japanese_name ? ` (${stop.location.japanese_name})` : ""}
                      </strong>
                    </div>
                    {stop.location.scene_description && (
                      <p className="stop-detail">
                        <strong>Scene:</strong> {stop.location.scene_description}
                      </p>
                    )}
                    {stop.location.real_world_address && (
                      <p className="stop-detail muted">{stop.location.real_world_address}</p>
                    )}
                    {stop.location.access_method && (
                      <p className="stop-detail">
                        <strong>Access:</strong> {stop.location.access_method}
                      </p>
                    )}
                    {stop.location.source_url && stop.location.source_url.startsWith("http") && (
                      <p className="stop-detail">
                        <a
                          href={stop.location.source_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Verification source
                        </a>
                      </p>
                    )}
                    {stop.travel_to_next_minutes !== null && (
                      <div className="transit-pill">
                        Next leg: ~{stop.travel_to_next_minutes} min
                        {stop.travel_mode_to_next ? ` via ${stop.travel_mode_to_next}` : ""}
                        {stop.travel_to_next_km !== null ? ` (${stop.travel_to_next_km} km)` : ""}
                      </div>
                    )}
                  </li>
                ))}
              </ol>
            </section>
          ))}

          {response.travel_plan.general_tips.length > 0 && (
            <section className="card">
              <h3>Pilgrimage Tips & Budget Breakdown</h3>
              <div className="cost-row">
                {Object.entries(response.travel_plan.total_estimated_cost)
                  .filter(([key]) => key !== "total")
                  .map(([key, value]) => (
                    <span key={key} className="clue-tag">
                      {key}: ¥{value.toLocaleString()}
                    </span>
                  ))}
              </div>
              <ul className="tips-list">
                {response.travel_plan.general_tips.map((tip) => (
                  <li key={tip}>{tip}</li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  );
}
