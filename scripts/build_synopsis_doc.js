/* Build docs/Sagar_Setu_Synopsis.docx — the mid-term synopsis report.
   Content is mirrored from docs/synopsis.md; edit both together.

   NODE_PATH=<dir containing node_modules/docx> node scripts/build_synopsis_doc.js
   SYNOPSIS_OUT=<path> overrides the output location.
*/
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
  WidthType, AlignmentType, LevelFormat, ShadingType, ImageRun, PageBreak, BorderStyle,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const FONT = "Calibri";
const PAGE_W = 605;

// ------------------------------------------------------------------ helpers
const runs = (xs, size = 21) =>
  (Array.isArray(xs) ? xs : [xs]).map((t) =>
    typeof t === "string" ? new TextRun({ text: t, font: FONT, size }) : t);

const p = (c, opts = {}) =>
  new Paragraph({ spacing: { after: 130, line: 276 }, ...opts, children: runs(c) });
const b = (t) => new TextRun({ text: t, font: FONT, size: 21, bold: true });
const i = (t) => new TextRun({ text: t, font: FONT, size: 21, italics: true });
const mono = (t) => new TextRun({ text: t, font: "Consolas", size: 17 });

const h1 = (t) => new Paragraph({
  heading: HeadingLevel.HEADING_1, spacing: { before: 300, after: 140 },
  children: [new TextRun({ text: t, font: FONT })],
});
const h2 = (t) => new Paragraph({
  heading: HeadingLevel.HEADING_2, spacing: { before: 220, after: 100 },
  children: [new TextRun({ text: t, font: FONT })],
});

/** "Limitation for this problem" paragraph — the bridge from each study to the gap. */
const lim = (t) => new Paragraph({
  spacing: { before: 40, after: 150, line: 276 },
  indent: { left: 300 },
  border: { left: { style: BorderStyle.SINGLE, size: 12, color: "B03A2E", space: 10 } },
  children: [new TextRun({ text: "Limitation for this problem.  ", font: FONT, size: 21, bold: true, color: "8E2B21" }),
             new TextRun({ text: t, font: FONT, size: 21, color: "5A2A24" })],
});

const quote = (c) => new Paragraph({
  spacing: { before: 140, after: 160, line: 288 },
  indent: { left: 420, right: 300 },
  border: { left: { style: BorderStyle.SINGLE, size: 18, color: "1F3864", space: 14 } },
  children: runs(c, 22),
});

const code = (lines) => new Paragraph({
  spacing: { before: 120, after: 150 },
  shading: { type: ShadingType.CLEAR, fill: "F4F4F2", color: "auto" },
  indent: { left: 240 },
  children: lines.flatMap((l, n) => (n ? [new TextRun({ break: 1 }), mono(l)] : [mono(l)])),
});

const cell = (content, w, head, size, center) =>
  new TableCell({
    width: { size: w, type: WidthType.DXA },
    shading: head ? { type: ShadingType.CLEAR, fill: "DCE6F1", color: "auto" } : undefined,
    margins: { top: 70, bottom: 70, left: 100, right: 100 },
    children: [new Paragraph({
      spacing: { after: 0 }, alignment: head || center ? AlignmentType.CENTER : AlignmentType.LEFT,
      children: (Array.isArray(content) ? content : [content]).map((r) =>
        typeof r === "string" ? new TextRun({ text: r, font: FONT, size, bold: !!head }) : r),
    })],
  });

const table = (widths, rows, size = 18, centerFrom = 99) =>
  new Table({
    width: { size: widths.reduce((a, c) => a + c, 0), type: WidthType.DXA },
    columnWidths: widths,
    rows: rows.map((r, ri) => new TableRow({
      tableHeader: ri === 0,
      children: r.map((c, ci) => cell(c, widths[ci], ri === 0, size, ci >= centerFrom)),
    })),
  });

function image(file, widthPx) {
  const data = fs.readFileSync(path.join(ROOT, "docs", "architecture", file));
  const w = data.readUInt32BE(16), hgt = data.readUInt32BE(20);
  return new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { before: 130, after: 90 },
    children: [new ImageRun({ type: "png", data, transformation: { width: widthPx, height: Math.round((widthPx * hgt) / w) } })],
  });
}
const caption = (t) => new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { after: 200 },
  children: [new TextRun({ text: t, font: FONT, size: 17, italics: true, color: "555555" })],
});

const ref = (n, t) => new Paragraph({
  spacing: { after: 100, line: 264 }, indent: { left: 420, hanging: 420 },
  children: [new TextRun({ text: `[${n}]  `, font: FONT, size: 19, bold: true }),
             ...runs(t, 19)],
});

const Y = "✓", N = "✗";
const ch = [];

// ------------------------------------------------------------------ title page
ch.push(
  new Paragraph({ spacing: { before: 900, after: 60 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "SAGAR SETU", font: FONT, size: 52, bold: true, color: "1F3864" })] }),
  new Paragraph({ spacing: { after: 420 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "An Agentic, Evidence-Grounded Marine Advisory System\nfor Indian Small-Craft Fishermen", font: FONT, size: 28 })] }),
  new Paragraph({ spacing: { after: 700 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Synopsis Report  ·  Mid-Term Review", font: FONT, size: 24, color: "555555" })] }),
  new Paragraph({ spacing: { after: 40 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Harshvardhan Singh", font: FONT, size: 24, bold: true })] }),
  new Paragraph({ spacing: { after: 40 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Supervisor: Ms. Anusha Chhabra", font: FONT, size: 22 })] }),
  new Paragraph({ spacing: { after: 300 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "13 October 2026", font: FONT, size: 22, color: "555555" })] }),
  new Paragraph({ spacing: { after: 0 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Submitted for the ISRO / INCOIS agentic marine intelligence problem statement,\nSmart India Hackathon 2026", font: FONT, size: 19, italics: true, color: "555555" })] }),
  new Paragraph({ children: [new PageBreak()] }),
);

// ------------------------------------------------------------------ abstract
ch.push(h1("Abstract"));
ch.push(p("India's ocean information agency, INCOIS, publishes some of the best small-craft marine guidance in the world — a validated wave and wind forecast, a boat-specific capsizing advisory, and a satellite-derived fishing-zone advisory with two decades of catch validation behind it. A fisherman preparing to leave harbour at four in the morning nevertheless has to open three separate web products, read them in English or as colour-coded maps, and combine them in his head. This work asks whether a conversational agent can do that combining for him — in his own language, over a single question — without ever being the thing that decides whether he goes to sea."));
ch.push(p([
  "The proposed system, ", b("Sagar Setu"), ", places a language model on both sides of a deterministic core. A planner interprets the question and dispatches parallel data fetches; a fixed, unit-tested rule engine applies published small-craft thresholds and returns the verdict; a second model pass explains that verdict in the user's language; and a mechanical verifier deletes any number in the generated answer that is not present in an evidence ledger of fetched observations. Every value the user sees carries its source, its valid time, its distance from the query point and its staleness.",
]));
ch.push(p([
  "A working implementation answers questions at five harbours spanning the Arabian Sea, the Bay of Bengal and the Andamans. On a 92-day, 460-harbour-morning backtest across the 2026 south-west monsoon, the day-ahead ", i("do-not-sail"), " verdict achieved a ", b("93.9 % hit rate at a 3.1 % false-alarm ratio"), ", with no dangerous morning ever graded ", i("go"), ".",
]));

// ------------------------------------------------------------------ 1
ch.push(h1("1.  Introduction and Problem Definition"));
ch.push(h2("1.1  Context"));
ch.push(p("Marine fishing supports roughly four million people along India's 11,098 km coastline, the large majority of them operating craft under twelve metres. These are open or partly-decked boats, often without radar, weather fax or reliable offshore connectivity. The decision that matters is made once a day, in the dark, before the boat leaves: go, or stay. A wrong decision in one direction costs a day's income; in the other it can cost the boat and the crew."));
ch.push(p([
  "Two further decisions ride alongside it. ", i("Where should I fish?"), " — the difference between a full hold and a wasted tank of diesel. And, in the Palk Bay and Gulf of Mannar, ", i("where is the border?"), " — Indian fishermen are detained by the Sri Lankan Navy for crossing the International Maritime Boundary Line every year, and the boundary is invisible at sea.",
]));
ch.push(p("India already produces the information needed for all three. The gap is not data. The gap is the last two hundred metres between a government web portal and a man standing on a beach at 4 a.m. holding a low-cost Android phone."));

ch.push(h2("1.2  Problem statement"));
ch.push(quote("Given a free-form question asked in any of India's scheduled languages, produce a single, trustworthy operational answer — safety verdict, fishing guidance and boundary warning together — derived verifiably from official marine data products, delivered inside a latency budget short enough to be used before a boat leaves, and degrading honestly and visibly when data sources are slow or unreachable."));
ch.push(quote([b("The language model must never be the component that decides whether it is safe to go to sea.")]));

ch.push(h2("1.3  Objectives"));
ch.push(table([760, 8266], [
  ["#", "Objective"],
  [[b("O1")], "Integrate safety, fishing-zone and maritime-boundary information, currently published as three disconnected products, behind one conversational interface."],
  [[b("O2")], "Design an architecture in which the safety verdict is produced by deterministic, unit-tested rules, structurally outside the language model's reach."],
  [[b("O3")], "Build an evidence ledger recording provenance, valid time, spatial distance and staleness for every observation, and a verifier that mechanically removes any generated number absent from it."],
  [[b("O4")], "Support question-answering in Indian languages end to end, beginning with Tamil and Hindi."],
  [[b("O5")], "Guarantee a complete, honest answer under source failure through a cache → live → stale-cache → snapshot fallback chain that declares its own degradation."],
  [[b("O6")], "Evaluate the system at the level the user acts on — the verdict — using standard warning-verification statistics (POD, FAR, CSI) rather than model-fit metrics alone."],
], 19));

// ------------------------------------------------------------------ 2
ch.push(new Paragraph({ children: [new PageBreak()] }));
ch.push(h1("2.  Literature Review"));
ch.push(p("Eight studies were selected from a wider survey of twenty, on two criteria: each bears directly on one component of the system, and preference was given to recent work — half of the eight were published in 2023 or later. They fall into two groups. The first covers the fisherman's three information needs and the systems already built to meet them. The second covers the language-model techniques this work depends on, and their known failure modes."));

ch.push(h2("2.1  Localised marine weather for small-boat fishers"));
ch.push(p("Kurup et al. [1] tested whether a localised marine weather service could support safer artisanal fishing on the coast of Kerala. Using the Weather Research and Forecasting (WRF) model downscaled to a 5 km grid, and issuing forecasts for 25 km × 25 km zones, they found three coastal sub-regions with distinct wind regimes, and that such localised forecasts complement the official forecasts, which are issued for large ocean areas. The study establishes that a small-boat decision needs local, not regional, information."));
ch.push(lim("The output is a better forecast — of wind. Turning it, together with waves, visibility and storm risk, into a go / no-go decision for a particular boat is still left to the fisherman."));

ch.push(h2("2.2  Fishing-zone advisories"));
ch.push(p("Sarangi et al. [2] generated Potential Fishing Zones for the western Bay of Bengal from six satellite-derived parameters — chlorophyll, sea-surface-temperature fronts, relative winds, current vectors, Ekman transport and eddies — using feature propagation to keep forecasts available under cloud. Validated against Fishery Survey of India catch data for 2016–2018, chlorophyll (food availability) correlated most strongly with catch, followed by fronts and eddies."));
ch.push(lim("The result is a zone map, with no connection to sea safety, to the user's boat, or to the maritime boundary. The study also shows what producing a validated PFZ product properly requires — which is why this work consumes the INCOIS PFZ advisory rather than re-deriving it."));

ch.push(h2("2.3  Decision-support systems already serving Indian fishers"));
ch.push(p("Two systems are the closest existing relatives of this work."));
ch.push(p([
  b("Thoondil"), " (Saka et al. [3]) was developed by the National Centre for Coastal Research and put into operation by the Tamil Nadu Department of Fisheries after a series of cyclones. It pairs a web-GIS dashboard for administrators, which tracks fishers at sea and supports two-way communication, with an Android app offering offline maps with routes to the nearest port, weather information, potential fishing zones and incident reporting. It is available in the local language, passed 15,000 downloads within months, and has been extended to Kozhikode in Kerala.",
]));
ch.push(p([
  "The ", b("Fisher Friend Mobile Application"), " (Anabel et al. [4]), developed by the M. S. Swaminathan Research Foundation with INCOIS, is a decision-support system for small-scale fishers that brings together potential fishing zones with GPS navigation, ocean-state forecasts, danger-zone and disaster alerts and market prices in several Indian languages.",
]));
ch.push(p("Together they show that mobile delivery, local language and the combination of weather with fishing zones work in practice, and that a state government will operate such a tool."));
ch.push(lim("Both are menu-and-screen applications: the fisherman navigates categories and combines the layers himself. Neither is described as accepting a free-form question about a specific boat, place and time, issuing a vessel-specific go / no-go verdict, or showing the source of each number it displays."));

ch.push(h2("2.4  The maritime boundary problem"));
ch.push(p("Vincent [5] analyses the persistent Palk Bay fishing conflict across the India–Sri Lanka International Maritime Boundary Line and argues that it requires joint Indo–Sri Lankan governance. The study establishes that the boundary problem is recurring and structural rather than incidental."));
ch.push(lim("It is a governance analysis and offers no aid to the individual fisherman. This work does not address the political dispute; it addresses the narrower technical need of knowing how far the boundary is and whether the current heading will cross it."));

ch.push(h2("2.5  Grounding language models in external evidence"));
ch.push(p("Retrieval-augmented generation (Lewis et al. [6]) combines a language model's parametric memory with passages retrieved at query time, improving factual question answering and addressing the difficulty language models have in providing provenance and updating their knowledge. This is the principle the system rests on: tomorrow's wave height cannot come from a model's training data and must be fetched when the question is asked."));
ch.push(lim("Retrieval grounds answers in text passages, not live numeric observations, and does not by itself guarantee that every generated claim is supported."));

ch.push(h2("2.6  Hallucination persists despite retrieval"));
ch.push(p([
  "RAGTruth (Niu et al. [7]) is a corpus of nearly 18,000 naturally generated responses from a range of language models working in retrieval-augmented settings, manually annotated for hallucination at both case and word level. It benchmarks hallucination rates across models and shows that ", b("unsupported content persists even when the correct evidence has been retrieved"), ".",
]));
ch.push(lim("If retrieval does not guarantee faithfulness, a safety decision cannot be delegated to the model. This is the direct justification for the architecture's two research choices: the verdict comes from fixed rules, and every number in the generated answer is checked mechanically against the evidence ledger."));

ch.push(h2("2.7  Indian-language translation"));
ch.push(p("IndicTrans2 (Gala et al. [8]) is the first open translation model covering all 22 scheduled Indian languages, released with the Bharat Parallel Corpus Collection (230 M sentence pairs) and the IN22 benchmark."));
ch.push(lim("Translation capability is no longer the bottleneck; no fisher-facing system yet offers conversation through it."));

ch.push(h2("2.8  Summary of reviewed work"));
ch.push(table([1950, 930, 880, 900, 900, 1060, 1060, 1020], [
  ["Work", "Small-boat safety info", "Fishing zones", "Border awareness", "Indian languages", "Answers a free-form question", "Go / no-go by fixed rules", "Every number verified"],
  ["Kurup et al. [1]", Y + " (wind)", N, N, "—", N, N, N],
  ["Sarangi et al. [2]", N, Y, N, N, N, N, N],
  ["Thoondil — Saka et al. [3]", Y, Y, "—", Y, N, N, N],
  ["Fisher Friend — Anabel et al. [4]", Y, Y, "partial", Y, N, N, N],
  ["RAG systems [6], [7]", N, N, N, "partial", Y, N, N],
  ["IndicTrans2 [8]", N, N, N, Y, N, N, N],
  [[b("Sagar Setu (proposed)")], [b(Y)], [b(Y)], [b(Y)], [b(Y)], [b(Y)], [b(Y)], [b(Y)]],
], 16, 1));
ch.push(caption("Table 1 — ✓ addressed · ✗ not addressed · — not described in the reviewed source. Vincent [5] establishes the boundary problem but proposes no tool, so is not tabulated."));

// ------------------------------------------------------------------ 3
ch.push(new Paragraph({ children: [new PageBreak()] }));
ch.push(h1("3.  Research Gap"));
ch.push(quote([b("The reviewed work addresses the parts of the problem separately — localised weather, fishing zones, the boundary, mobile delivery, retrieval-grounded language models. We found no published system that lets a fisherman ask one question in his own language and receive a single operational decision — safety, fishing and border together — that is derived verifiably from official data rather than generated by a model.")]));
ch.push(p("Six specific gaps follow from the review."));
const gapP = (code, title, refs, text) => p([b(`${code} — ${title} ${refs}.  `), text], { spacing: { after: 110, line: 276 } });
ch.push(gapP("G1", "Fragmentation", "[1]–[5]", "Kurup et al. address wind, Sarangi et al. fishing zones, Vincent the boundary. Thoondil and Fisher Friend bundle several of these, but as separate screens that the fisherman must read and combine himself."));
ch.push(gapP("G2", "Interaction mode", "[3], [4]", "The existing systems are menu-driven. Neither accepts a free-form question carrying the vessel, place, heading and departure time that actually determine the answer."));
ch.push(gapP("G3", "Language depth", "[3], [4], [8]", "Existing apps offer local-language content. With IndicTrans2 covering 22 languages, the limit is no longer translation but the absence of a conversational fisher system to attach it to."));
ch.push(gapP("G4", "Verifiability", "[6], [7]", "Retrieval grounds answers in evidence, but RAGTruth shows unsupported content persists even with retrieval. No fisher-facing system shows per-number provenance or checks its numbers mechanically."));
ch.push(gapP("G5", "Structural safety separation", "[6], [7]", "Given G4, any system that lets a language model generate the safety call inherits its hallucination risk. No reviewed system keeps the go / no-go decision in tested, deterministic rules separate from the model."));
ch.push(gapP("G6", "Evaluation at the level of action", "[1], [2]", "Kurup et al. validate a forecast and Sarangi et al. validate zones against catch. Neither evaluates a go / no-go decision — the thing a fisherman acts on — with warning statistics such as hit rate and false-alarm ratio [10]."));
ch.push(table([3700, 1900, 3426], [
  ["Gap", "Evidence", "Objective"],
  ["G1  Fragmentation", "[1]–[5]", [b("O1"), "  one conversational interface"]],
  ["G2  Broadcast / menu interaction", "[3], [4]", [b("O1"), "  one conversational interface"]],
  ["G3  Language depth", "[3], [4], [8]", [b("O4"), "  Indian-language Q&A"]],
  ["G4  Verifiability", "[6], [7]", [b("O3"), "  evidence ledger + verifier"]],
  ["G5  Safety separation", "[6], [7]", [b("O2"), "  deterministic safety verdict"]],
  ["G6  Evaluation stops at the forecast", "[1], [2]", [b("O6"), "  verdict-level evaluation"]],
  ["Constraint: unreliable connectivity at sea (Thoondil ships offline maps for this reason)", "[3]", [b("O5"), "  honest degradation"]],
], 18));

// ------------------------------------------------------------------ 4
ch.push(h1("4.  Proposed Methodology"));
ch.push(h2("4.1  Architecture"));
ch.push(p("Five stages, with the language model deliberately confined to the first, second and fourth."));
ch.push(image("architecture.png", PAGE_W));
ch.push(caption("Figure 1 — system architecture. The red line is the design's load-bearing constraint."));

ch.push(h2("4.2  The evidence ledger"));
ch.push(p("No tool returns a bare float. Every value is an Observation:"));
ch.push(code([
  "class Observation(BaseModel):",
  "    variable: str        # \"significant_wave_height\"",
  "    value: float",
  "    unit: str            # \"m\"",
  "    source: str          # \"open_meteo/mfwam\"",
  "    valid_time: datetime # what the value is FOR",
  "    fetched_at: datetime # when we got it",
  "    distance_km: float   # query point to nearest grid node",
  "    confidence: float    # lowered when we fall down the source chain",
  "    note: str | None     # \"served from snapshot, network unavailable\"",
]));
ch.push(p("A typical briefing records about 130 observations. The ledger is rendered in the interface beneath every answer, with staleness shown prominently — a six-hour-old forecast and a six-minute-old one must not look alike on screen."));

ch.push(h2("4.3  The deterministic risk engine"));
ch.push(p("Seven parameters, three vessel classes (traditional < 12 m, motorised 12–20 m, mechanised > 20 m), evaluated as a pure function in under 50 ms:"));
ch.push(table([2750, 1600, 2300, 2376], [
  ["Parameter", "Go", "Caution", "Do not sail"],
  ["Significant wave height", "< 1.5 m", "1.5 – 2.5 m", "> 2.5 m"],
  ["Sustained wind", "< 19 kt", "19 – 27 kt", "> 27 kt"],
  ["Sea steepness (Hs/T²)", "low", "short-period swell", "breaking-sea regime"],
  ["Lightning proximity", "none < 50 km", "50 – 100 km closing", "any strike < 50 km"],
  ["Cyclone cone of uncertainty", "no intersect", "intersect 72 – 120 h", "intersect < 48 h"],
  ["Visibility", "> 5 km", "2 – 5 km", "< 2 km"],
], 18));
ch.push(p([
  b("The worst parameter decides. Never an average."), " Averaging across six parameters is how a system sends a boat out under a thunderhead because the waves happened to be calm. Missing wave or wind data can never produce a ", i("go"), ".",
], { spacing: { before: 160, after: 130 } }));
ch.push(p("These values are provisional starting points. INCOIS's Small Vessel Advisory Service [9] computes a Boat Safety Index from wave height, wave steepness, directional spread and the rapid growth of wind sea, issued per vessel beam-width class (< 4 m, 6 m, 7 m). It independently selects steepness and vessel size, as this work does, and is the calibration target; its numeric thresholds are not published, so calibration is an identified task, not a completed one."));

ch.push(h2("4.4  Data sources"));
ch.push(table([2500, 4000, 2526], [
  ["Source", "Provides", "Access"],
  ["Open-Meteo Marine + Weather", "Wave height/period/direction, swell, currents, wind, gusts, visibility", "Free, no key — the reliability floor"],
  ["INCOIS PFZ (GeoServer WFS)", "Daily Potential Fishing Zone advisories by sector", "Open, cached daily"],
  ["INCOIS static layers", "14 PFZ sectors, 1,223 named landing centres", "Open, committed"],
  ["Marine Regions (VLIZ)", "Indian EEZ, IMBL, boundary polygons", "Static GeoJSON"],
  ["NOAA CoastWatch", "Chlorophyll-a", "Open"],
  ["Copernicus Marine", "Chlorophyll-a, physics", "Free account"],
  ["IMD", "Cyclone track, lightning, district warnings", [b("Pending access key")]],
  ["INCOIS ERDDAP", "SST and chlorophyll archive", "Open, but stale (SST ends 2011) — not used"],
], 18));
ch.push(p([
  "Every fetch follows a four-step chain: ", b("fresh cache → live (2 s budget) → stale cache → frozen snapshot"), ", with confidence 0.95 / 1.00 / 0.70 / 0.50 respectively. The system produces a complete, honest answer with the network unplugged, and says that it is doing so.",
], { spacing: { before: 160, after: 130 } }));

ch.push(h2("4.5  Tools and techniques"));
ch.push(p([
  "Python 3.11 · Pydantic · LangGraph · FastAPI with SSE streaming · xarray/netCDF4 · Shapely · httpx (async) · pytest · React 19 + Vite + MapLibre GL · model-agnostic LLM layer (Gemini free tier, Ollama, or none). Total external cost to date: ", b("₹0"), ".",
]));

ch.push(h2("4.6  Evaluation method"));
ch.push(p("Prediction: the verdict computed from the forecast available the evening before. Truth: the verdict computed from the same model's final analysis for that morning. Sample: 92 mornings × 5 harbours = 460 harbour-mornings per lead time, across the 2026 south-west monsoon. Scored with POD, FAR, CSI and a 3×3 confusion matrix [10]."));
ch.push(p([
  "This is forecast-versus-analysis, which is an ", b("upper bound"), " on true skill; no public INCOIS or NIOT buoy feed is available to us. The harness runs unchanged against buoy data if access is obtained — this is the single most valuable thing the department could help secure.",
]));

// ------------------------------------------------------------------ 5
ch.push(new Paragraph({ children: [new PageBreak()] }));
ch.push(h1("5.  Progress and Preliminary Results"));
ch.push(p("Four of six planned phases are complete: data-source verification and snapshotting; the typed tool belt and risk engine; the LangGraph agent system with planner and verifier; and the FastAPI + MapLibre interface. The implementation is approximately 4,700 lines of Python and 630 of TypeScript, with 115 passing unit tests concentrated on the risk and geospatial modules."));
ch.push(p([b("Verdict skill, 92 days × 5 harbours, pooled (do-not-sail event):")], { spacing: { before: 170, after: 120 } }));
ch.push(table([1900, 900, 1600, 2000, 1200, 1426], [
  ["Forecast lead", "n", "Hit rate (POD)", "False-alarm ratio", "CSI", "3-way agreement"],
  [[b("1 day ahead")], "460", [b("93.9 %")], [b("3.1 %")], "91.2 %", "93.5 %"],
  ["2 days ahead", "460", "97.0 %", "17.9 %", "80.0 %", "90.2 %"],
  ["3 days ahead", "460", "90.9 %", "30.2 %", "65.2 %", "85.0 %"],
], 19));
ch.push(p([
  "The two day-ahead misses were graded ", i("caution"), ", never ", i("go"), " — the asymmetry the worst-of rule is designed to produce. Skill degrades with lead time mainly through false alarms, which argues for presenting the day-ahead verdict as the decision and longer leads as outlook.",
], { spacing: { before: 170, after: 130 } }));
ch.push(p("Measured end-to-end latency for a Tamil question is approximately 8 s, of which the two language-model stages account for 7.4 s and the safety decision for 0.0001 s."));
ch.push(image("flow.png", PAGE_W));
ch.push(caption("Figure 2 — one Tamil question, measured end to end."));

// ------------------------------------------------------------------ 6
ch.push(h1("6.  Remaining Work"));
ch.push(table([1100, 5400, 2526], [
  ["Phase", "Work", "Status"],
  ["5", "Bhashini round trip with IndicTrans2 fallback; A* route optimisation; causal productivity query", "In progress"],
  ["6", "Offline hardening, error states, five-location regression, rehearsal", "Pending"],
  ["—", "Calibrate thresholds against INCOIS SVAS criteria [9]", [b("Blocked"), " — criteria not published numerically"]],
  ["—", "IMD API key for lightning and cyclone parameters", [b("Blocked"), " — requires institutional letter"]],
  ["—", "Buoy observations to replace analysis as evaluation truth", [b("Blocked"), " — requires INCOIS/NIOT data access"]],
], 18));

// ------------------------------------------------------------------ refs
ch.push(h1("References"));
ch.push(h2("Literature reviewed"));
const LIT = [
  "P. H. Kurup, S. Abhilash, S. Mavath, V. K. Mini, N. Alamirew, and M. Martin, “Validation of localised coastal wind forecasts for artisan fishers of southwestern India,” Weather, vol. 79, no. 7, pp. 231–241, 2024. doi: 10.1002/wea.4554",
  "R. K. Sarangi, M. Jishad, R. Sharma, et al., “Multiple ocean parameter-based potential fishing zone (PFZ) location generation and validation in the Western Bay of Bengal,” Environmental Monitoring and Assessment, vol. 196, no. 1, art. 98, 2024. doi: 10.1007/s10661-023-12259-6",
  "S. K. Saka, A. E. Mathew, V. Ganesh, et al., “A Web-GIS and mobile-based application for a safe ocean for fishers,” Marine Technology Society Journal, vol. 55, no. 3, pp. 50–57, 2021. doi: 10.4031/MTSJ.55.3.10",
  "N. J. Anabel, S. Velvizhi, and D. Suvitha, “Fisher Friend Mobile Application: a decision support system for small scale fishers in India,” CSI Transactions on ICT, vol. 6, no. 3–4, pp. 257–267, 2018. doi: 10.1007/s40012-018-0212-1",
  "S. Vincent, “Palk Bay fishing problem requires Indo-Sri Lankan joint-governance,” Maritime Affairs: Journal of the National Maritime Foundation of India, vol. 16, no. 2, pp. 71–88, 2020. doi: 10.1080/09733159.2020.1838717",
  "P. Lewis, E. Perez, A. Piktus, et al., “Retrieval-augmented generation for knowledge-intensive NLP tasks,” in Adv. Neural Inf. Process. Syst. (NeurIPS), vol. 33, pp. 9459–9474, 2020.",
  "C. Niu, Y. Wu, J. Zhu, S. Xu, K. Shum, R. Zhong, J. Song, and T. Zhang, “RAGTruth: A hallucination corpus for developing trustworthy retrieval-augmented language models,” in Proc. 62nd Annu. Meeting Assoc. Comput. Linguistics (ACL), vol. 1, pp. 10862–10878, 2024.",
  "J. Gala, P. A. Chitale, R. AK, et al., “IndicTrans2: Towards high-quality and accessible machine translation models for all 22 scheduled Indian languages,” Transactions on Machine Learning Research (TMLR), 2023. arXiv:2305.16307",
];
LIT.forEach((t, n) => ch.push(ref(n + 1, t)));
ch.push(h2("Methodology references"));
[
  "Indian National Centre for Ocean Information Services, “Small Vessel Advisory and Forecast Services (SVAS),” INCOIS Ocean State Forecast portal. Available: https://incois.gov.in/portal/osf/SVA_overview.jsp",
  "I. T. Jolliffe and D. B. Stephenson, Forecast Verification: A Practitioner's Guide in Atmospheric Science, 2nd ed. Chichester, UK: Wiley-Blackwell, 2012.",
].forEach((t, n) => ch.push(ref(LIT.length + n + 1, t)));

// ------------------------------------------------------------------ build
const doc = new Document({
  styles: {
    default: { document: { run: { font: FONT, size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, color: "1F3864", font: FONT },
        paragraph: { spacing: { before: 300, after: 140 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 23, bold: true, color: "2E5A96", font: FONT },
        paragraph: { spacing: { before: 220, after: 100 }, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: "bullets", levels: [
    { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 460, hanging: 240 } } } },
  ] }] },
  sections: [{ properties: { page: { margin: { top: 1100, bottom: 1100, left: 1120, right: 1120 } } }, children: ch }],
});

Packer.toBuffer(doc).then((buf) => {
  const out = process.env.SYNOPSIS_OUT || path.join(ROOT, "docs", "Sagar_Setu_Synopsis.docx");
  fs.writeFileSync(out, buf);
  console.log("wrote", out, (buf.length / 1e6).toFixed(2), "MB");
});
