/* Build docs/Sagar_Setu_Architecture.docx — the architecture submission, with both
   rendered diagrams embedded. Run scripts/plot_architecture.py first.

   NODE_PATH=<dir containing node_modules/docx> node scripts/build_architecture_doc.js
*/
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
  WidthType, AlignmentType, LevelFormat, ShadingType, ImageRun, PageBreak,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const FONT = "Calibri";
const PAGE_W = 620; // px at 96 dpi ≈ 6.5" of usable width

const p = (runs, opts = {}) =>
  new Paragraph({
    spacing: { after: 120, line: 276 },
    alignment: AlignmentType.JUSTIFIED,
    ...opts,
    children: (Array.isArray(runs) ? runs : [runs]).map((t) =>
      typeof t === "string" ? new TextRun({ text: t, font: FONT, size: 22 }) : t),
  });
const b = (t) => new TextRun({ text: t, font: FONT, size: 22, bold: true });
const i = (t) => new TextRun({ text: t, font: FONT, size: 22, italics: true });
const mono = (t) => new TextRun({ text: t, font: "Consolas", size: 19 });
const h1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 340, after: 150 }, children: [new TextRun({ text: t, font: FONT })] });
const h2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 240, after: 110 }, children: [new TextRun({ text: t, font: FONT })] });
const bullet = (runs) => new Paragraph({
  numbering: { reference: "bullets", level: 0 }, spacing: { after: 80, line: 276 },
  children: (Array.isArray(runs) ? runs : [runs]).map((t) => typeof t === "string" ? new TextRun({ text: t, font: FONT, size: 22 }) : t),
});

const cell = (content, w, head) =>
  new TableCell({
    width: { size: w, type: WidthType.DXA },
    shading: head ? { type: ShadingType.CLEAR, fill: "DCE6F1", color: "auto" } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: (Array.isArray(content) ? content : [content]).map((t) =>
      new Paragraph({
        spacing: { after: 0 },
        children: (Array.isArray(t) ? t : [t]).map((r) =>
          typeof r === "string" ? new TextRun({ text: r, font: FONT, size: 19, bold: !!head }) : r),
      })),
  });

const table = (widths, rows) =>
  new Table({
    width: { size: widths.reduce((a, c) => a + c, 0), type: WidthType.DXA },
    columnWidths: widths,
    rows: rows.map((r, ri) => new TableRow({ tableHeader: ri === 0, children: r.map((c, ci) => cell(c, widths[ci], ri === 0)) })),
  });

function image(file, widthPx) {
  const data = fs.readFileSync(path.join(ROOT, "docs", "architecture", file));
  // read the PNG header for intrinsic size
  const w = data.readUInt32BE(16), hgt = data.readUInt32BE(20);
  const height = Math.round((widthPx * hgt) / w);
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 120, after: 120 },
    children: [new ImageRun({ type: "png", data, transformation: { width: widthPx, height } })],
  });
}
const caption = (t) => new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { after: 220 },
  children: [new TextRun({ text: t, font: FONT, size: 18, italics: true, color: "555555" })],
});

const W = 9026;
const children = [];

// ---------------------------------------------------------------- title
children.push(
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 }, children: [new TextRun({ text: "Sagar Setu — Proposed System Architecture", font: FONT, size: 36, bold: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 }, children: [new TextRun({ text: "Conversational marine decision support for Indian small-craft fishermen", font: FONT, size: 24 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 }, children: [new TextRun({ text: "ISRO / INCOIS agentic marine intelligence problem statement · Smart India Hackathon 2026", font: FONT, size: 21, color: "555555" })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 300 }, children: [new TextRun({ text: "Harshvardhan Singh · September 2026", font: FONT, size: 21, color: "555555" })] }),
);

// ---------------------------------------------------------------- 1
children.push(h1("1 · What the system does"));
children.push(p("A fisherman types a question in his own language — “Is it safe to go out from Kochi tomorrow morning?”, “Where are the fish today?”, “How far is the Sri Lanka boundary on this heading?” — and receives an answer in that same language, with a map and the evidence behind every number in it."));
children.push(p([b("The system does not forecast the sea."), " It applies published small-craft safety thresholds to live government and open forecast data, and uses a language model only to understand the question and to explain the result. That distinction is what the architecture is organised around."]));

children.push(h1("2 · Architectural style and governing principles"));
children.push(p("The system is a layered architecture with a multi-agent orchestration tier and one cross-cutting data structure, the evidence ledger. There are eight layers; each depends only on the layer beneath it. Three principles decide every structural question in the design:"));
children.push(table([2900, 6126], [
  ["Principle", "Structural consequence"],
  ["A language model never decides whether it is safe to go to sea.", "The safety verdict is produced by a separate deterministic module that has no import from, and no dependency on, the model layer. The model layer sits above it and receives its output. The separation is structural, not a matter of discipline."],
  ["No number reaches the user unless it is in the evidence ledger first.", "Every tool returns Observation objects carrying value, source, validity time, distance and confidence — never bare floats. A verifier module re-reads the drafted answer and rejects any numeric claim not traceable to a ledger row."],
  ["Cache first, network second, snapshot always available.", "A single data-access chain sits between the tool belt and every external source, so all sources degrade identically and visibly. The system answers with the network unplugged, and says that it is doing so."],
]));

// ---------------------------------------------------------------- diagram
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h1("3 · Architecture diagram"));
children.push(image("architecture.png", PAGE_W));
children.push(caption("Figure 1 — Sagar Setu system architecture. Eight layers; the request path runs downward and the result path upward. The dashed red line marks the boundary above which models plan and explain and below which ordinary Python fetches and decides. A full-resolution copy is at docs/architecture/architecture.png."));

// ---------------------------------------------------------------- 4
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h1("4 · Component catalogue"));

children.push(h2("Layer 1 — Presentation (web/src · React 19 + Vite + TypeScript + MapLibre GL)"));
children.push(table([2500, 6526], [
  ["Component", "Responsibility"],
  ["App.tsx", "Session state, vessel class, question submission, consumption of the SSE event stream"],
  ["components/Verdict.tsx", "Renders the GO / CAUTION / DO NOT SAIL badge from the engine's result object — never parsed from the answer text, so prose cannot soften a verdict"],
  ["components/MapView.tsx", "MapLibre GL map: PFZ lines, EEZ, international boundaries, vessel track, predicted crossing point. Free OpenStreetMap raster tiles, so there is no access token that can fail during a demo"],
  ["components/Ledger.tsx", "The evidence table: each value with its source, validity time, distance to the grid node, a freshness chip and a confidence bar; rows the verdict cited are highlighted and listed first"],
  ["components/AgentTrace.tsx", "Live per-specialist progress and timings"],
  ["api.ts", "Typed client; hand-parses the SSE frame stream, since EventSource is GET-only"],
]));

children.push(h2("Layer 2 — API (src/marine/api.py · FastAPI + Server-Sent Events)"));
children.push(table([2500, 6526], [
  ["Endpoint", "Responsibility"],
  ["POST /ask", "Runs one question and streams agent → chunk → reset → result → done events, so agent progress and answer tokens reach the screen before the request completes"],
  ["GET /geo/static", "EEZ outline and the 23 international boundary segments, simplified to about 1 km — 228 KB instead of 3 MB — and cached in process"],
  ["GET /health", "Active model provider, snapshot age and the threshold tables, for the client status bar"],
  ["startup task", "Pre-warms the PFZ advisory and the five test harbours, so the first question does not pay the cold-fetch cost"],
]));

children.push(h2("Layer 3 — Orchestration (src/marine/graph.py · LangGraph state machine)"));
children.push(table([2100, 5426, 1500], [
  ["Node", "Responsibility", "Uses a model?"],
  ["Planner", "Language detection, translation, intent classification, location and time-window resolution, vessel / heading / speed extraction. Emits a typed task DAG. A deterministic fast path handles common English questions in about 50 ms with no model call at all.", "Only on the non-fast path"],
  ["Ocean & Weather", "Fans out the wave, wind, visibility and sea-state fetches concurrently; reduces each variable to its worst value in the window; flags disagreement between sources rather than averaging them", "No"],
  ["Geospatial & Boundary", "Position against the EEZ, nearest international boundary with bearing, PFZ bearing and distance, and the predictive crossing — projects heading and speed forward and warns before a crossing, not after", "No"],
  ["Analytics & Causal", "Chlorophyll against a multi-year daily baseline (z-score, trend); names a plausible mechanism as a hypothesis and never asserts causation the data cannot support", "No"],
  ["Risk", "Invokes the deterministic engine of Layer 4", "No"],
  ["Synthesis & Verify", "Builds the brief from the ledger, drafts the answer with the model, then verifies every number in it", "Draft only"],
]));
children.push(p([i("The three specialists are returned together by one conditional edge, so LangGraph executes them in a single superstep — concurrently. Parallelism is therefore a property of the emitted plan rather than of prompt wording.")]));

children.push(h2("Layer 4 — Decision (src/marine/risk/) — deterministic, no model"));
children.push(table([2100, 6926], [
  ["Module", "Responsibility"],
  ["thresholds.py", "Three vessel-class tables (traditional < 12 m, motorised 12–20 m, mechanised > 20 m) across seven parameters: significant wave height, sustained wind with gusts, sea steepness Hs/T², visibility, lightning proximity, cyclone cone and boundary crossing. Each table carries a calibration string, currently “provisional” pending INCOIS's published criteria."],
  ["rules.py", "evaluate(RiskInputs, VesselClass) → RiskVerdict. Grades each parameter, then takes the worst — never an average. A missing wave-height or wind value yields insufficient_data and can never produce GO. Returns a per-parameter breakdown carrying the ledger ids that produced each value."],
]));
children.push(p(["Runs in about 0.1 ms and is covered by 40 unit tests. It has no import from the agents package, which is what makes the separation structural."]));
children.push(p([b("Synthesis & Verify"), " is its counterpart above the line. It builds a one-page ", i("brief"), " from the ledger — the model's entire view of the data — has the model draft the answer in the user's language, then runs the verifier: every number in the draft, in Latin or Indic digits, must match a ledger value, a threshold or a window hour. An unsupported number triggers one corrective retry; failing that, a deterministic template answer ships instead."]));

children.push(h2("Layer 5 — Tool belt (src/marine/tools/)"));
children.push(p("Fifteen typed functions with Pydantic signatures — the only route by which anything, including the agents, reaches data. A malformed call fails loudly at the boundary rather than becoming a wrong number in an answer."));
children.push(table([1800, 7226], [
  ["Module", "Functions"],
  ["ocean.py", "get_wave_forecast, get_wind_forecast, get_visibility_forecast, get_sea_state, get_chlorophyll, get_argo_temperature, fan_out"],
  ["spatial.py", "get_pfz_advisory, check_position, predict_boundary_crossing"],
  ["safety.py", "assess_sailing_risk, safety_briefing, cyclone_status, lightning_status"],
  ["locations.py", "resolve_location — 5 test harbours, 16 curated ports, 1 223 INCOIS landing centres, an alias table and a deterministic Indic-script name table, with a guarded fuzzy match. Unknown names return nothing, never a guess."],
  ["windows.py", "named_window — “tomorrow morning” → 05:00–12:00 IST → UTC"],
]));

children.push(h2("Layer 6 — Geospatial library (src/marine/geo/)"));
children.push(p("Pure functions, no I/O: geodesy.py (great-circle distance, bearing, destination point, and a local equirectangular projection so geometry can be done in kilometres); boundaries.py (EEZ point-in-polygon, nearest boundary, forward projection to the first crossing); pfz.py (nearest INCOIS zone with distance, bearing and compass point)."));

children.push(h2("Layer 7 — Data access (src/marine/sources/)"));
children.push(p("One chain for every source: fresh cache → live network within a 2 s budget → stale cache → frozen snapshot, with confidence 0.95, 1.00, 0.70 and 0.50 respectively and a note explaining any degradation. The layer also provides per-source TTL and timeout, in-flight request de-duplication (wind and visibility share a single weather request), and a window-shift fallback when the snapshot does not cover the requested hours."));

children.push(h2("Layer 8 — External data sources"));
children.push(table([2100, 4326, 2600], [
  ["Source", "Provides", "Status"],
  ["INCOIS GeoServer WFS", "Potential Fishing Zone advisory, sector polygons, 1 223 landing centres", "Live, daily"],
  ["Open-Meteo", "Waves, swell, wind, gusts, visibility, SST, currents — hourly, 8 days", "Live; the reliability floor of every chain"],
  ["Copernicus Marine", "Chlorophyll-a forecast plus a five-year daily baseline", "Live, pre-fetched — 11 s to open, so never in the request path"],
  ["NOAA CoastWatch", "VIIRS chlorophyll, about 4 km", "Live; fallback behind Copernicus"],
  ["Marine Regions (VLIZ)", "EEZ polygon and 23 international boundary segments", "Static, committed to the repository"],
  ["INCOIS ERDDAP (Argo)", "Gridded temperature, 1°", "Live but about six weeks stale — weak cross-check only"],
  ["IMD", "Cyclone track and cone, lightning, district warnings", "Blocked — institutional API key pending. Reported as an explicit gap in every verdict rather than silently omitted."],
]));

// ---------------------------------------------------------------- 5 ledger
children.push(h1("5 · The evidence ledger — the cross-cutting component"));
children.push(p("Not a layer but a structure threaded through all of them, and the single most important data structure in the system."));
children.push(new Paragraph({ spacing: { after: 40 }, children: [mono("class Observation(BaseModel):")] }));
for (const line of [
  "    variable: str          # \"significant_wave_height\"",
  "    value: float",
  "    unit: str              # \"m\"",
  "    source: str            # \"open_meteo/marine\"",
  "    valid_time: datetime   # when the value is FOR",
  "    fetched_at: datetime   # when we got it",
  "    distance_km: float     # query point to nearest grid node",
  "    confidence: float      # lowered when we fell down the chain",
  "    note: str | None       # \"served from snapshot, network unavailable\"",
  "    provenance: Literal[\"live\", \"cache\", \"stale_cache\", \"snapshot\"]",
]) children.push(new Paragraph({ spacing: { after: 0 }, children: [mono(line)] }));
children.push(new Paragraph({ spacing: { after: 140 }, children: [] }));
children.push(p(["A companion ", mono("MissingObservation"), " records a variable the system tried to obtain and could not, with the reason — so the answer can say “I could not check cyclone warnings” instead of quietly dropping the parameter."]));
children.push(p("The ledger serves three consumers, and this is what ties the architecture together:"));
children.push(bullet(["the ", b("risk engine"), " reads the worst value per parameter from it;"]));
children.push(bullet(["the ", b("brief"), " handed to the language model is built only from it;"]));
children.push(bullet(["the ", b("verifier"), " rejects any number in the drafted answer that is not in it."]));
children.push(p([i("Provenance and confidence flow up from the data-access chain, so the interface can display staleness without guessing — a value fetched six hours ago and one fetched six minutes ago do not look alike on screen.")]));

// ---------------------------------------------------------------- 6 interactions
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h1("6 · How the components interact"));
children.push(image("request_flow.png", PAGE_W));
children.push(caption("Figure 2 — the measured path of one question through the system, warm cache, 22 September 2026."));
children.push(p("Control flow runs downward through the layers; data flow returns upward, but only after passing through the evidence ledger and the verifier. There is no path by which the model layer can write a value into a verdict."));
children.push(p([b("Measured end to end: 7.9 s"), " for a Tamil question, of which 7.4 s is the two model calls on a free tier. An English question skips the planner call and completes in about 3.6 s. With no model configured at all, the same pipeline answers in English from deterministic templates in about 0.4 s — everything the verdict actually depends on takes under a second."]));

// ---------------------------------------------------------------- 7 decisions
children.push(h1("7 · Key design decisions and the alternatives rejected"));
children.push(table([2500, 2600, 3926], [
  ["Decision", "Alternative rejected", "Reason"],
  ["Deterministic rule engine for the verdict", "An ML classifier, or letting the model decide", "No labelled dataset of small-craft outcomes exists; a safety verdict must be auditable line by line; and the thresholds belong to INCOIS and IMD, not to us"],
  ["Worst-of combination, never a weighted average", "A utility function over the seven parameters", "Averaging is how a system sends someone out under a thunderhead because the waves were calm"],
  ["Evidence ledger plus a verifier pass", "Trusting the model's output, or checking facts afterwards", "Makes hallucination structurally impossible for numeric claims rather than merely unlikely"],
  ["Four agents: planner, three specialists, synthesis", "The nine roles in the problem statement implemented as nine processes", "Those are capabilities, not processes; a naive nine-agent chain costs about 40 s and looks broken. Missing capabilities belong in the tool belt as ordinary Python."],
  ["Model behind a provider interface", "Hard-coding one vendor's SDK", "The model does only language work, so it is swappable by configuration — Gemini free tier by default, Ollama for offline, Anthropic optional. Total project cost stays at zero."],
  ["Deterministic fast path in the planner", "Every question through the model", "Keeps common English questions at about 50 ms of planning on a free tier whose round trip is 2.8 s"],
  ["Consume INCOIS's PFZ product", "Train a fishing-zone model of our own", "INCOIS has two decades of validation against catch data; our contribution is reasoning over it, not replacing it"],
  ["Snapshot fallback committed to the repository", "Requiring connectivity", "The system must give a complete, honestly-labelled answer with the network unplugged"],
]));

// ---------------------------------------------------------------- 8 NFR
children.push(h1("8 · Non-functional properties and deployment"));
children.push(bullet([b("Latency. "), "Target about 2.4 s to first token. Achieved for English (0.4 s deterministic, 3.6 s with the model); Indic-script questions run about 8 s on the free model tier. Mitigations in place: the planner fast path, pre-warmed caches, concurrent fan-out, and token streaming so the answer appears as it is written."]));
children.push(bullet([b("Degradation. "), "Four-step fallback per source; provenance and confidence surfaced to the interface; missing feeds named explicitly in the answer rather than omitted."]));
children.push(bullet([b("Testability. "), "115 tests, none requiring the network or a model. The risk engine and geospatial library have real unit tests with real fixtures; agent behaviour has smoke tests driven by a scripted fake model, including one that invents numbers in order to prove the verifier catches them."]));
children.push(bullet([b("Cost. "), "Every data source is free, the model runs on a free tier, and hosting is a laptop. Nothing in the architecture requires paid infrastructure."]));
children.push(bullet([b("Evaluation. "), "A separate harness scores the verdict computed from yesterday's forecast against the analysis of what the morning actually brought, across 460 harbour-mornings, plus a prospective daily log. Day-ahead do-not-sail warnings: 94 % hit rate at a 3 % false-alarm ratio."]));
children.push(p([b("Deployment"), " for the demonstration is two processes on one machine:"]));
children.push(new Paragraph({ spacing: { after: 0 }, children: [mono("uv run uvicorn marine.api:app --reload      # API, orchestration, engine — port 8000")] }));
children.push(new Paragraph({ spacing: { after: 140 }, children: [mono("cd web && npm run dev                       # interface — port 5173")] }));
children.push(p("data/static/ (boundaries, sectors, landing centres) and data/snapshots/ (a week of real data for five harbours) are committed, so a fresh clone runs offline. data/cache/ is local and ignored by version control. The only configuration is a .env file, and every key in it is optional."));

// ---------------------------------------------------------------- build
const doc = new Document({
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 30, bold: true, color: "1F3864", font: FONT }, paragraph: { spacing: { before: 340, after: 150 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 25, bold: true, color: "2E5395", font: FONT }, paragraph: { spacing: { before: 240, after: 110 }, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [{ properties: { page: { margin: { top: 1160, bottom: 1160, left: 1160, right: 1160 } } }, children }],
});

Packer.toBuffer(doc).then((buf) => {
  const out = path.join(ROOT, "docs", "Sagar_Setu_Architecture.docx");
  fs.writeFileSync(out, buf);
  console.log("wrote", out, (buf.length / 1e6).toFixed(2), "MB");
});
