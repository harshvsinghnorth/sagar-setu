import { useMemo, useState } from "react";
import type { AskResult, Observation, Provenance } from "../api";

// Staleness is shown prominently: a forecast fetched six hours ago and one fetched six
// minutes ago must not look the same on screen (CLAUDE.md).
export function freshness(o: Observation, now: number): { cls: string; label: string } {
  if (o.provenance === "snapshot") return { cls: "old", label: "stored snapshot" };
  const ageMin = (now - Date.parse(o.fetched_at)) / 60000;
  if (o.provenance === "stale_cache") return { cls: "old", label: `older cache · ${fmtAge(ageMin)}` };
  if (ageMin < 15) return { cls: "fresh", label: `fetched ${fmtAge(ageMin)} ago` };
  if (ageMin < 120) return { cls: "recent", label: `fetched ${fmtAge(ageMin)} ago` };
  return { cls: "old", label: `fetched ${fmtAge(ageMin)} ago` };
}

function fmtAge(min: number): string {
  if (min < 1) return "<1 min";
  if (min < 60) return `${Math.round(min)} min`;
  if (min < 48 * 60) return `${(min / 60).toFixed(1)} h`;
  return `${Math.round(min / 1440)} d`;
}

const PROV: Record<Provenance, string> = { live: "live", cache: "cached (fresh)", stale_cache: "stale cache", snapshot: "snapshot" };

const LABEL: Record<string, string> = {
  significant_wave_height: "wave height", wave_period: "wave period", wave_direction: "wave dir", swell_height: "swell height",
  swell_period: "swell period", swell_direction: "swell dir", wind_wave_height: "wind-wave height", wind_wave_period: "wind-wave period",
  sea_surface_temperature: "sea temp", current_speed: "current", current_direction: "current dir", wind_speed: "wind", wind_gust: "gusts",
  wind_direction: "wind dir", visibility: "visibility", precipitation: "rain", weather_code: "weather code", cape: "CAPE",
  chlorophyll_a: "chlorophyll-a", sea_temperature_5m: "Argo temp 5 m", pfz_distance_km: "PFZ distance", pfz_bearing_deg: "PFZ bearing",
  imbl_distance_km: "boundary distance", imbl_bearing_deg: "boundary bearing", inside_india_eez: "inside EEZ",
  boundary_crossing_min: "crossing in", boundary_crossing_km: "crossing distance",
};

export default function Ledger({ result, highlight }: { result: AskResult; highlight: Set<string> }) {
  const [showAll, setShowAll] = useState(false);
  const now = Date.now();
  const obs = result.ledger.observations;

  // Default view: the rows the verdict cited plus one worst-case row per variable; the
  // full hourly series is behind "show all".
  const rows = useMemo(() => {
    if (showAll) return obs;
    const seen = new Set<string>();
    const keep: Observation[] = [];
    for (const o of obs) if (highlight.has(o.id)) { keep.push(o); seen.add(o.variable); }
    for (const o of obs) if (!seen.has(o.variable)) { keep.push(o); seen.add(o.variable); }
    return keep;
  }, [obs, highlight, showAll]);

  return (
    <section className="ledger">
      <header className="ledger-head">
        <h3>Evidence ledger</h3>
        <span className="muted">{obs.length} observations · {result.ledger.missing.length} missing</span>
        <span className="sources">
          {Object.entries(result.ledger.sources).map(([s, p]) => (
            <span key={s} className={`chip prov-${p}`}>{s} · {PROV[p]}</span>
          ))}
        </span>
        <button className="link" onClick={() => setShowAll((v) => !v)}>{showAll ? "show summary" : `show all ${obs.length}`}</button>
      </header>
      <div className="ledger-scroll">
        <table>
          <thead>
            <tr><th>id</th><th>variable</th><th className="num">value</th><th>valid for</th><th>freshness</th><th>source</th><th className="num">grid</th><th className="num">conf.</th></tr>
          </thead>
          <tbody>
            {rows.map((o) => {
              const f = freshness(o, now);
              return (
                <tr key={o.id} className={highlight.has(o.id) ? "cited" : ""} title={o.note ?? ""}>
                  <td className="mono">{o.id}</td>
                  <td>{LABEL[o.variable] ?? o.variable}</td>
                  <td className="num mono">{fmt(o.value)} <span className="unit">{o.unit}</span></td>
                  <td className="mono">{validFor(o.valid_time)}</td>
                  <td><span className={`fresh ${f.cls}`}>{f.label}</span></td>
                  <td className="src">{o.source}</td>
                  <td className="num">{o.distance_km ? `${o.distance_km} km` : "—"}</td>
                  <td className="num"><span className="conf"><i style={{ width: `${o.confidence * 100}%` }} /></span> {o.confidence.toFixed(2)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {result.ledger.missing.length > 0 && (
          <ul className="missing">
            {result.ledger.missing.map((m, i) => (
              <li key={i}><b>{LABEL[m.variable] ?? m.variable}</b> — not available: {m.reason}</li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

function fmt(v: number): string {
  return Math.abs(v) >= 100 ? v.toFixed(0) : Math.abs(v) >= 10 ? v.toFixed(1) : v.toFixed(2);
}

function validFor(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("en-IN", { timeZone: "Asia/Kolkata", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", hour12: false }) + " IST";
}
