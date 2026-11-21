/**
 * Strict TypeScript contracts mirroring `src/anime_pilgrimage/models.py` and `api.py`.
 */

export interface Coordinates {
  lat: number;
  lng: number;
}

export interface PilgrimageLocation {
  name: string;
  japanese_name: string;
  anime_title: string;
  city: string;
  prefecture: string;
  real_world_address: string;
  coordinates: Coordinates | null;
  description: string;
  scene_description: string;
  episode_reference: string;
  access_method: string;
  nearby_attractions: string[];
  best_visit_time: string;
  photography_notes: string;
  etiquette_notes: string;
  source_url: string;
  confidence_score: number;
}

export interface ScheduledStop {
  order: number;
  location: PilgrimageLocation;
  arrival_time: string;
  departure_time: string;
  visit_duration_minutes: number;
  activity: string;
  travel_to_next_minutes: number | null;
  travel_to_next_km: number | null;
  travel_mode_to_next: string | null;
}

export interface DailyItinerary {
  day: number;
  title: string;
  city_focus: string;
  date: string | null;
  stops: ScheduledStop[];
  locations: string[];
  activities: string[];
  travel_times: number[];
  total_travel_time: number;
  total_visit_time: number;
  estimated_cost: Record<string, number>;
  notes: string[];
}

export interface TravelPlan {
  trip_title: string;
  destination: string;
  regions: string[];
  duration_days: number;
  total_locations: number;
  daily_itineraries: DailyItinerary[];
  total_estimated_cost: Record<string, number>;
  budget_level: string;
  transportation_mode: string;
  accommodation_suggestions: string[];
  general_tips: string[];
  emergency_contacts: Record<string, string>;
}

export interface SceneAnalysis {
  identified_anime: string;
  japanese_title: string;
  confidence: number;
  landmark_guess: string;
  japanese_landmark: string;
  city_or_region: string;
  visual_clues: string[];
  camera_and_framing_tips: string;
  suggested_search_queries: string[];
  notes: string;
}

export type ResponseType = "itinerary" | "clarification" | "error";

export interface GeneratedResponse {
  response_type: ResponseType;
  title: string;
  introduction: string;
  main_content: string;
  markdown_content: string;
  summary: string;
  recommendations: string[];
  disambiguation_needed: boolean;
  disambiguation_questions: string[];
  confidence: number;
  travel_plan: TravelPlan | null;
  locations: PilgrimageLocation[];
  scene_analysis: SceneAnalysis | null;
  metadata: Record<string, unknown>;
}

export interface HealthResponse {
  status: string;
  version: string;
  openrouter_configured: boolean;
  llm_model: string;
  vlm_model: string;
  search_provider: string;
}
