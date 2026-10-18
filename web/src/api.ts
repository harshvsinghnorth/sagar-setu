import type {} from "geojson";
// Types mirror src/marine/api.py. The verdict and the ledger come from the engine and the
// tools; the answer text comes from the model. The interface keeps them visibly separate.

export type Vessel = "traditional" | "motorised" | "mechanised";
export type Provenance = "live" | "cache" | "stale_cache" | "snapshot";

export interface Observation {
  id: string;
  variable: string;
  value: number;
  unit: string;
  source: string;
  valid_time: string;
  fetched_at: string;
  distance_km: number;
  confidence: number;
  note: string | null;
  provenance: Provenance;
  latency_ms: number | null;
}

export interface Missing {
  variable: string;
  reason: string;
  sources_tried: string[];
}

export interface ParameterVerdict {
  parameter: string;
  status: "evaluated" | "proxy" | "missing";
  level: 0 | 1 | 2 | null;
  value: number | null;
  unit: string | null;
  caution_at: number | null;
  no_go_at: number | null;
  reason: string;
  evidence: string[];
}

export interface Verdict {
  level: 0 | 1 | 2;
  label: "GO" | "CAUTION" | "DO NOT SAIL";
  status: "verdict" | "insufficient_data";
  vessel_class: Vessel;
  parameters: ParameterVerdict[];
  reasons: string[];
  data_gaps: string[];
  calibration: string;
  computed_ms: number;
}

export interface AgentEvent {
  node: string;
  status: "done" | "failed" | "started";
  ms: number;
  detail: string;
}

export interface AskResult {
  query: string;
  plan: {
    source: "fast_path" | "llm";
    intent: string;
    language: string;
    english_query: string;
    location: { name: string; lat: number; lon: number; sector_id?: string | null } | null;
    day: string;
    part: string;
    vessel: Vessel | null;
    heading_deg: number | null;
    speed_kt: number | null;
  };
  answer: { text: string; language: string; source: string; verified: boolean; unsupported: string[] };
  verdict: Verdict | null;
  window: string | null;
  degradation: string[];
  gaps: string[];
  ledger: { observations: Observation[]; missing: Missing[]; sources: Record<string, Provenance>; degraded: boolean };
  events: AgentEvent[];
  analytics?: { latest: number; unit: string; baseline_mean: number; baseline_sd: number; z_score: number; trend: string; interpretation: string };
  map: {
    location?: { lat: number; lon: number; name: string };
    pfz?: GeoJSON.FeatureCollection;
    pfz_bearings?: { rank: number; to: [number, number]; distance_km: number; bearing_deg: number; compass: string; state: string }[];
    nearest_imbl?: { name: string; other_state: string; distance_km: number; bearing_deg: number; compass: string; closest: [number, number]; zone: string };
    track?: { points: [number, number][]; crossing: [number, number] | null; boundary: string | null; minutes: number | null; within_horizon: boolean };
    route?: {
      found: boolean;
      reason: string | null;
      destination: string;
      dest: [number, number];
      points: [number, number][];
      distance_km: number;
      eta_min: number;
      min_imbl_km: number | null;
      direct_crosses_border: boolean;
      sea_state_source: string;
    };
    conditions?: Record<string, { value: number; unit: string; valid_time: string; provenance: Provenance }>;
  };
}

export interface StaticGeo {
  eez: GeoJSON.Feature;
  imbl: GeoJSON.FeatureCollection;
  harbours: GeoJSON.FeatureCollection;
}

export const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface AskHandlers {
  onAgent: (ev: AgentEvent) => void;
  onChunk: (text: string) => void;
  onReset: () => void;
  onResult: (r: AskResult) => void;
  onError: (msg: string) => void;
}

/** POST /ask and parse the SSE stream by hand (EventSource is GET-only). */
export async function askStream(
  body: { query: string; vessel?: Vessel; lat?: number; lon?: number; heading_deg?: number; speed_kt?: number },
  h: AskHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API}/ask`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) {
    h.onError(`API ${res.status}`);
    return;
  }
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let idx: number;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const frame = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      let event = "message";
      let data = "";
      for (const line of frame.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7);
        else if (line.startsWith("data: ")) data += line.slice(6);
      }
      if (!data) continue;
      const payload = JSON.parse(data);
      if (event === "agent") h.onAgent(payload);
      else if (event === "chunk") h.onChunk(payload.text);
      else if (event === "reset") h.onReset();
      else if (event === "result") h.onResult(payload);
      else if (event === "error") h.onError(payload.message);
    }
  }
}

export async function fetchStaticGeo(): Promise<StaticGeo> {
  const r = await fetch(`${API}/geo/static`);
  return r.json();
}

export async function fetchHealth(): Promise<{ ok: boolean; llm: string; snapshot_created_at: string | null }> {
  const r = await fetch(`${API}/health`);
  return r.json();
}

export interface BankQuestion {
  id: string;
  category: string;
  lang: string;
  style: string;
  q: string;
  en?: string;
  note?: string;
  last_run?: { understood: boolean; behaved: boolean } | null;
}

export interface QuestionBank {
  title: string;
  categories: Record<string, string>;
  questions: BankQuestion[];
  summary?: { understood: string; behaved: string; run_at: string } | null;
}

export async function fetchQuestionBank(): Promise<QuestionBank> {
  const r = await fetch(`${API}/question-bank`);
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}
