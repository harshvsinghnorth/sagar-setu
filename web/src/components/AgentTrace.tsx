import type { AgentEvent } from "../api";

const NAMES: Record<string, string> = {
  planner: "Planner",
  ocean_weather: "Ocean & Weather",
  geospatial: "Geospatial & Boundary",
  analytics: "Analytics & Causal",
  risk_engine: "Risk engine",
  synthesis: "Synthesis & Verify",
  total: "Total",
};

export default function AgentTrace({ events, busy }: { events: AgentEvent[]; busy: boolean }) {
  if (events.length === 0 && !busy) return null;
  return (
    <ol className="trace">
      {events.map((e, i) => (
        <li key={i} className={e.status}>
          <span className="tnode">{NAMES[e.node] ?? e.node}</span>
          <span className="tms mono">{e.ms} ms</span>
          <span className="tdetail">{e.detail}</span>
        </li>
      ))}
      {busy && <li className="running"><span className="tnode">working…</span><span className="spinner" /></li>}
    </ol>
  );
}
