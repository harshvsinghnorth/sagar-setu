import { useEffect, useMemo, useRef, useState } from "react";
import { askStream, fetchHealth, fetchQuestionBank, fetchStaticGeo, type AgentEvent, type AskResult, type QuestionBank as Bank, type StaticGeo, type Vessel } from "./api";
import MapView from "./components/MapView";
import QuestionBank from "./components/QuestionBank";
import Ledger from "./components/Ledger";
import VerdictCard from "./components/Verdict";
import AgentTrace from "./components/AgentTrace";
import "./styles.css";

interface Turn {
  id: number;
  query: string;
  text: string;
  events: AgentEvent[];
  result: AskResult | null;
  error: string | null;
  busy: boolean;
}

const EXAMPLES = [
  "Is it safe to go out from Kochi tomorrow morning?",
  "நாளை காலை இராமேஸ்வரத்தில் இருந்து 90 டிகிரி திசையில் 8 நாட் வேகத்தில் போகலாமா?",
  "क्या कल सुबह वेरावल से समुद्र में जाना सुरक्षित है?",
  "Where are the fish near Paradip today?",
  "How far is the Sri Lanka border from Rameswaram if I head 90 at 8 knots?",
  "What is the best route from Kochi to the fishing zone?",
];

export default function App() {
  const [geo, setGeo] = useState<StaticGeo | null>(null);
  const [health, setHealth] = useState<{ llm: string; snapshot_created_at: string | null } | null>(null);
  const [vessel, setVessel] = useState<Vessel>(() => (localStorage.getItem("vessel") as Vessel) || "traditional");
  const [query, setQuery] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [bank, setBank] = useState<Bank | null>(null);
  const [showBank, setShowBank] = useState(false);
  const abort = useRef<AbortController | null>(null);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchStaticGeo().then(setGeo).catch(() => setGeo(null));
    fetchHealth().then(setHealth).catch(() => setHealth(null));
    fetchQuestionBank().then(setBank).catch(() => setBank(null));
  }, []);
  useEffect(() => { localStorage.setItem("vessel", vessel); }, [vessel]);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }); }, [turns]);

  const latest = useMemo(() => [...turns].reverse().find((t) => t.result)?.result ?? null, [turns]);
  const cited = useMemo(() => {
    const s = new Set<string>();
    for (const p of latest?.verdict?.parameters ?? []) for (const id of p.evidence) s.add(id);
    return s;
  }, [latest]);

  const busy = turns.some((t) => t.busy);

  async function submit(q: string) {
    const text = q.trim();
    if (!text || busy) return;
    setQuery("");
    const id = Date.now();
    setTurns((ts) => [...ts, { id, query: text, text: "", events: [], result: null, error: null, busy: true }]);
    const upd = (f: (t: Turn) => Turn) => setTurns((ts) => ts.map((t) => (t.id === id ? f(t) : t)));
    abort.current = new AbortController();
    try {
      await askStream(
        { query: text, vessel },
        {
          onAgent: (ev) => upd((t) => ({ ...t, events: [...t.events, ev] })),
          onChunk: (c) => upd((t) => ({ ...t, text: t.text + c })),
          onReset: () => upd((t) => ({ ...t, text: "" })),
          onResult: (r) => upd((t) => ({ ...t, result: r, text: r.answer.text })),
          onError: (m) => upd((t) => ({ ...t, error: m })),
        },
        abort.current.signal,
      );
    } catch (e) {
      upd((t) => ({ ...t, error: e instanceof Error ? e.message : String(e) }));
    } finally {
      upd((t) => ({ ...t, busy: false }));
    }
  }

  return (
    <div className="app">
      <aside className="chat">
        <header className="brand">
          <h1>Sagar Setu <span className="sub">सागर सेतु</span></h1>
          <p className="tag">Ask about the sea in your language. Every number shown has a source.</p>
          <div className="status">
            <span className={`dot ${health ? "ok" : "bad"}`} />
            {health ? <>model: {health.llm}</> : "API offline"}
            {bank && (
              <button className={`bank-open ${showBank ? "on" : ""}`} onClick={() => setShowBank((s) => !s)}>
                Question bank ({bank.questions.length})
              </button>
            )}
            <label className="vessel">
              boat
              <select value={vessel} onChange={(e) => setVessel(e.target.value as Vessel)}>
                <option value="traditional">traditional (&lt;12 m)</option>
                <option value="motorised">motorised (12–20 m)</option>
                <option value="mechanised">mechanised (&gt;20 m)</option>
              </select>
            </label>
          </div>
        </header>

        <div className="turns">
          {showBank && bank && (
            <QuestionBank
              bank={bank}
              disabled={busy}
              onClose={() => setShowBank(false)}
              onAsk={(q) => { setShowBank(false); submit(q); }}
            />
          )}
          {!showBank && turns.length === 0 && (
            <div className="examples">
              <p className="muted">Try:</p>
              {EXAMPLES.map((e) => (
                <button key={e} className="example" onClick={() => submit(e)}>{e}</button>
              ))}
            </div>
          )}
          {!showBank && turns.map((t) => (
            <div key={t.id} className="turn">
              <div className="q">{t.query}</div>
              <AgentTrace events={t.events} busy={t.busy && !t.result} />
              {t.result?.verdict && <VerdictCard v={t.result.verdict} window={t.result.window} />}
              {t.result?.degradation.length ? (
                <div className="banner degraded">
                  <b>Some data is not current:</b> {t.result.degradation.join("; ")}
                </div>
              ) : null}
              <div className={`a ${t.result ? "final" : "streaming"}`} lang={t.result?.answer.language}>
                {t.text || (t.busy ? "…" : "")}
              </div>
              {t.result && (
                <div className="meta muted">
                  {t.result.plan.language.toUpperCase()} · {t.result.plan.intent} · plan {t.result.plan.source === "fast_path" ? "deterministic" : "model"} ·
                  answer {t.result.answer.source.startsWith("template") ? "template" : "model"} · {t.result.answer.verified ? "all numbers verified against the ledger" : "unverified"}
                  {t.result.gaps.length > 0 && <> · not checked: {t.result.gaps.map((g) => g.split(":")[0]).join(", ")}</>}
                </div>
              )}
              {t.result?.analytics && (
                <div className="analytics">
                  chlorophyll-a {t.result.analytics.latest} {t.result.analytics.unit} · baseline {t.result.analytics.baseline_mean} (sd {t.result.analytics.baseline_sd}) · z = {t.result.analytics.z_score} · {t.result.analytics.trend}
                  <div className="muted">{t.result.analytics.interpretation}</div>
                </div>
              )}
              {t.error && <div className="banner error">{t.error}</div>}
            </div>
          ))}
          <div ref={bottom} />
        </div>

        <form className="ask" onSubmit={(e) => { e.preventDefault(); submit(query); }}>
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Is it safe off Kochi tomorrow morning? · நாளை கடலுக்கு போகலாமா? · कल समुद्र में जाना सुरक्षित है?" disabled={busy} autoFocus />
          <button type="submit" disabled={busy || !query.trim()}>{busy ? "…" : "Ask"}</button>
        </form>
      </aside>

      <main className="right">
        <MapView geo={geo} result={latest} />
        {latest ? <Ledger result={latest} highlight={cited} /> : (
          <section className="ledger empty">
            <h3>Evidence ledger</h3>
            <p className="muted">Ask a question. Every value used in the answer will be listed here with its source, the time it is valid for, how far the nearest data point is, and how fresh it is.</p>
            {health?.snapshot_created_at && <p className="muted">Offline fallback snapshot: {new Date(health.snapshot_created_at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })} IST</p>}
          </section>
        )}
      </main>
    </div>
  );
}
