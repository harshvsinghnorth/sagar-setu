import type { Verdict as V } from "../api";

// The badge is rendered from the engine's verdict, never parsed from the answer text, so
// prose cannot soften it (CLAUDE.md rule 1).
const STYLE: Record<V["label"], { cls: string; icon: string }> = {
  GO: { cls: "go", icon: "✓" },
  CAUTION: { cls: "caution", icon: "!" },
  "DO NOT SAIL": { cls: "nogo", icon: "✕" },
};
const LEVEL = ["GO", "CAUTION", "NO-GO"];

export default function VerdictCard({ v, window }: { v: V; window: string | null }) {
  const s = STYLE[v.label];
  return (
    <section className={`verdict ${s.cls}`}>
      <div className="verdict-row">
        <span className="badge"><span className="icon">{s.icon}</span>{v.label}</span>
        <span className="verdict-meta">
          {v.vessel_class} craft{window ? ` · ${window}` : ""}
          {v.status === "insufficient_data" && <span className="warn"> · insufficient data</span>}
        </span>
      </div>
      {v.reasons.length > 0 && (
        <ul className="reasons">{v.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>
      )}
      <details className="params">
        <summary>All {v.parameters.length} parameters · engine {v.computed_ms} ms</summary>
        <table>
          <tbody>
            {v.parameters.map((p) => (
              <tr key={p.parameter} className={p.status}>
                <td className="pname">{p.parameter}</td>
                <td className={`plevel l${p.level ?? "x"}`}>{p.level === null ? "—" : LEVEL[p.level]}</td>
                <td className="preason">{p.reason}{p.status === "proxy" && <em> (proxy)</em>}</td>
                <td className="pev mono">{p.evidence.join(" ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="calib">{v.calibration}</p>
      </details>
    </section>
  );
}
