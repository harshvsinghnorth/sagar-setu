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

const bullet = (c, level = 0) => new Paragraph({
  numbering: { reference: "bullets", level }, spacing: { after: 100, line: 276 }, children: runs(c),
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

const cell = (content, w, head, size) =>
  new TableCell({
    width: { size: w, type: WidthType.DXA },
    shading: head ? { type: ShadingType.CLEAR, fill: "DCE6F1", color: "auto" } : undefined,
    margins: { top: 70, bottom: 70, left: 110, right: 110 },
    children: [new Paragraph({
      spacing: { after: 0 }, alignment: head ? AlignmentType.CENTER : AlignmentType.LEFT,
      children: (Array.isArray(content) ? content : [content]).map((r) =>
        typeof r === "string" ? new TextRun({ text: r, font: FONT, size, bold: !!head }) : r),
    })],
  });

const table = (widths, rows, size = 18) =>
  new Table({
    width: { size: widths.reduce((a, c) => a + c, 0), type: WidthType.DXA },
    columnWidths: widths,
    rows: rows.map((r, ri) => new TableRow({
      tableHeader: ri === 0,
      children: r.map((c, ci) => cell(c, widths[ci], ri === 0, size)),
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

ch.push(h2("2.1  Operational ocean forecasting for Indian waters"));
ch.push(p("INCOIS operates the Ocean State Forecast (OSF) service, issuing wave height, period, direction, currents and sea-surface temperature for the Indian Ocean. Nair et al. [1] report the system's performance against wave-rider buoys, ship-mounted wave-height meters and satellite altimeters, finding a scatter index generally below 15 % for significant wave height, and a correlation of 0.98 with an RMS error of 0.35 m at Gopalpur during Cyclone Phailin. The service is operational, validated and publicly reachable — which is why this work consumes it rather than attempting to improve on it."));

ch.push(h2("2.2  Small-craft safety advisories"));
ch.push(p([
  "INCOIS's ", b("Small Vessel Advisory and Forecast Service (SVAS)"), " [2] is the closest existing product to the safety half of this work. It is an impact-based service that identifies potential vessel-overturning zones up to ", b("ten days in advance"), " using a ", b("Boat Safety Index"), " computed from significant wave height, wave steepness, directional spread and the rapid development of wind sea. Advisories are issued per vessel ", b("beam-width category — under 4 m, 6 m and 7 m"), " — covering the fishing fleets of all nine coastal states.",
]));
ch.push(p([
  "Two observations follow. First, SVAS validates the parameter choice made in this work: steepness and vessel size, not wave height alone, govern capsizing. An INCOIS presentation on small-craft advisories [3] notes that capsizing is ", i("not a phase-averaged phenomenon"), ", which is precisely why a threshold table rather than a regression is the defensible instrument. Second, SVAS is delivered as a colour-coded map on a web portal. It answers ", i("where"), ", for a reader who already knows to look, in English. It does not answer a question.",
]));

ch.push(h2("2.3  Fishing-zone advisories and their measured benefit"));
ch.push(p([
  "INCOIS issues Potential Fishing Zone (PFZ) advisories from sea-surface temperature and ocean-colour chlorophyll fronts. Pillai and Nair [4] validated these advisories along the Kerala coast over 2006–2010, using both catch data from active fishers and controlled experiments run simultaneously inside and outside notified zones. Catch per unit effort was higher inside the zones — roughly two to six times the catch, and two to seven times the monetary benefit. Reported multipliers vary widely between studies and most evidence comes from institute-affiliated researchers, so the effect size should be treated with caution — but the direction is consistent and the product has two decades of operational history. This work therefore ", b("consumes the PFZ advisory and does not attempt to re-derive it"), ".",
]));

ch.push(h2("2.4  The last-mile dissemination problem"));
ch.push(p("Delivery has been studied more than it has been solved. The Fisher Friend Mobile Application distributes advisories in nine Indian languages across seven coastal states; INCOIS operates multilingual SMS and a 24×7 helpline; a telecom pilot extended mobile signal roughly 30 km offshore specifically to carry ocean-state forecasts [5]. INCOIS's own service review notes that helpline numbers “need to be popularised among fishers.”"));
ch.push(p([
  "Every one of these channels is ", b("broadcast"), ". A bulletin is pushed; a map is published; an SMS arrives. None of them accepts ", i("“I am leaving Rameswaram at five tomorrow morning, heading ninety degrees at eight knots in a nine-metre boat — is that sensible?”"), " The information is multilingual, but the interaction is not conversational, and the specific combination of vessel, heading, time and place that determines the real answer cannot be expressed.",
]));

ch.push(h2("2.5  Machine-learned weather forecasting"));
ch.push(p("Data-driven global forecast models now match or exceed physics-based numerical weather prediction on headline scores — GraphCast [6] and Pangu-Weather [7] being the prominent examples. This literature is relevant chiefly as a road deliberately not taken. Training a competitive forecast model requires decades of reanalysis, substantial compute, and validation infrastructure that a student project cannot supply, and the operational product it would compete with is already validated and free. The contribution available here is in reasoning over official forecasts, not in replacing them."));

ch.push(h2("2.6  Language models as tool-using agents"));
ch.push(p("The technique that makes this work possible is the use of language models as planners that call external tools rather than as sources of fact. ReAct [8] interleaves reasoning traces with tool actions; Toolformer [9] shows models can learn when to call an API; retrieval-augmented generation [10] established the general pattern of grounding generation in retrieved external evidence rather than parametric memory."));

ch.push(h2("2.7  Domain advisory systems built on language models"));
ch.push(p("Two recent systems are the closest architectural relatives of this work."));
ch.push(p([
  b("ClimSight"), " (Kuznetsov et al. [11]) couples an LLM with local climate data through an agent-based architecture that routes queries to specialised modules, using retrieval to ground responses in climate models and reports. A subsequent extension, XCLIM-AI, couples the LLM interpretation layer with ", i("deterministic computation"), " of climate indicators, reporting that the largest gains in actionability and uncertainty reporting appear when deterministic indicator computation is integrated rather than generated. That finding is the single strongest external support for the architecture proposed here.",
]));
ch.push(p([
  b("WildfireGPT"), " (Xie et al. [12]) is a retrieval-augmented multi-agent LLM system for natural-hazard decision support, grounded in hazard projections, observational datasets and scientific literature, and evaluated across ten expert-led case studies.",
]));
ch.push(p([
  "Both ground their output in ", b("retrieved documents"), ", and both answer ", b("analytical"), " questions for planners and researchers. Neither issues an operational go/no-go decision to a layperson who will act on it within hours, and neither grounds in live numeric observations carrying per-value provenance.",
]));

ch.push(h2("2.8  Hallucination and the limits of grounding"));
ch.push(p([
  "Lin et al. [13] survey hallucination in LLM-based agents, proposing a taxonomy across the agent workflow — reasoning, execution, perception, memorisation and communication — and cataloguing eighteen triggering causes. They observe that agent errors can be “physically consequential” and cascade through long task chains. Related work on tool-use failure identifies ", b("tool bypass"), ", in which a model simulates a tool's output instead of calling it — a failure mode that defeats auditing precisely when auditing matters most.",
]));
ch.push(p([
  "This literature is why prompt instructions such as ", i("“only use the data provided”"), " are treated in this work as insufficient. The system is designed so that an unsupported number is ", b("mechanically removed"), ", not merely discouraged.",
]));

ch.push(h2("2.9  Indian-language NLP"));
ch.push(p("IndicTrans2 (Gala et al. [14]) is the first open translation model covering all 22 scheduled Indian languages, released with the Bharat Parallel Corpus Collection (230 M bitext pairs) and the IN22 benchmark. With Bhashini, the National Language Translation Mission's API layer, it makes multilingual operation a solved engineering problem rather than a research one — removing the usual excuse for shipping marine advisories in English."));

ch.push(h2("2.10  Forecast verification methodology"));
ch.push(p("Warning systems are conventionally scored with the 2×2 contingency table — probability of detection, false-alarm ratio, critical success index — as set out by Jolliffe and Stephenson [15]. This framework is adopted here, because the quantity a fisherman acts on is a categorical warning, not a wave height, and because misses and false alarms carry utterly different costs and must therefore be reported separately rather than merged into a single accuracy figure."));

ch.push(h2("2.11  Summary of reviewed systems"));
const col = [1750, 790, 900, 840, 1180, 1030, 1200, 1150];
ch.push(table(col, [
  ["System", "Conver-\nsational", "Indian\nlanguages", "Live\nnumeric\ndata", "Deterministic\nsafety verdict", "Per-number\nprovenance", "Safety + fish\n+ boundary", "Verdict-level\naccuracy"],
  ["INCOIS OSF [1]", N, "partial", Y, "n/a", N, N, "RMSE only"],
  ["INCOIS SVAS [2]", N, N, Y, Y, N, N, N],
  ["INCOIS PFZ [4]", N, Y + " (10)", Y, "n/a", N, N, "catch-based"],
  ["Fisher Friend app [5]", N, Y + " (9)", Y, N, N, "partial", N],
  ["ClimSight [11]", Y, N, "partial", N, "document", N, N],
  ["WildfireGPT [12]", Y, N, "partial", N, "document", N, "case studies"],
  [[b("Sagar Setu")], [b(Y)], [b(Y)], [b(Y)], [b(Y)], [b(Y)], [b(Y)], [b("POD/FAR/CSI")]],
], 16));
ch.push(caption("Table 1 — where the proposed system sits relative to reviewed work."));

// ------------------------------------------------------------------ 3
ch.push(new Paragraph({ children: [new PageBreak()] }));
ch.push(h1("3.  Research Gap"));
ch.push(quote([b("India has excellent marine data products and workable one-way delivery channels, but no published system lets a fisherman ask one question in his own language and receive a single operational decision — safety, fishing and boundary together — that is provably derived from those products rather than generated by a model.")]));
ch.push(p("Six specific gaps follow from the review."));
ch.push(bullet([b("G1 — Fragmentation. "), "Safety (SVAS), fishing zones (PFZ) and maritime boundaries are three separate products with three interfaces and no shared query. No published work reasons across all three for a single user question."]));
ch.push(bullet([b("G2 — Interaction mode. "), "All existing dissemination is broadcast: bulletins, SMS, map portals, helplines. None accepts a free-form query carrying the vessel, heading, speed and departure time that actually determine the answer."]));
ch.push(bullet([b("G3 — Language depth. "), "Existing products reach nine or ten languages as translated output. With IndicTrans2 [14] covering 22 languages, the limiting factor is no longer translation capability but the absence of a conversational marine system to attach it to."]));
ch.push(bullet([b("G4 — Verifiability. "), "ClimSight [11] and WildfireGPT [12] ground generation in retrieved documents. Agent hallucination surveys [13] show that fabrication and tool bypass remain open problems. No marine advisory system publishes a per-observation provenance ledger with a mechanical post-generation check that deletes unsupported numbers."]));
ch.push(bullet([b("G5 — Structural safety separation. "), "No published marine advisory architecture prevents the language model from making the go/no-go call. XCLIM-AI's deterministic-computation layer [11] is the nearest published idea, and it computes climate indicators for analysts, not operational safety verdicts for fishermen."]));
ch.push(bullet([b("G6 — Evaluation at the level of action. "), "Validation literature reports RMSE and scatter index for wave height [1]. A fisherman does not act on RMSE; he acts on a verdict. Hit rate and false-alarm ratio for the verdict itself are not reported anywhere in this domain."]));

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
ch.push(p("These values are provisional starting points. Calibrating them against the INCOIS Boat Safety Index parameter set [2] — which independently selects steepness, directional spread and beam width — is an identified task, not a completed one."));

ch.push(h2("4.4  Data sources"));
ch.push(table([2300, 4100, 2626], [
  ["Source", "Provides", "Access"],
  ["INCOIS ERDDAP", "SST, winds, currents, Argo profiles", "Open REST / griddap"],
  ["INCOIS PFZ", "Potential Fishing Zone advisories, 12 sectors", "Web product, scraped and cached"],
  ["Open-Meteo Marine", "Wave height/period/direction, swell, currents", "Free, no key — the reliability floor"],
  ["Copernicus Marine", "Chlorophyll-a, physics reanalysis", "Free account"],
  ["NOAA CoastWatch", "Chlorophyll-a fallback", "Open"],
  ["Marine Regions (VLIZ)", "Indian EEZ, IMBL, boundary polygons", "Static GeoJSON"],
  ["IMD", "Cyclone track, lightning, district warnings", [b("Pending access key")]],
], 18));
ch.push(p([
  "Every fetch follows a four-step chain: ", b("fresh cache → live (2 s budget) → stale cache → frozen snapshot"), ", with confidence 0.95 / 1.00 / 0.70 / 0.50 respectively. The system produces a complete, honest answer with the network unplugged, and says that it is doing so.",
], { spacing: { before: 160, after: 130 } }));

ch.push(h2("4.5  Tools and techniques"));
ch.push(p([
  "Python 3.11 · Pydantic · LangGraph · FastAPI with SSE streaming · xarray/netCDF4 · Shapely · httpx (async) · pytest · React 19 + Vite + MapLibre GL · model-agnostic LLM layer (Gemini free tier, Ollama, or none). Total external cost to date: ", b("₹0"), ".",
]));

ch.push(h2("4.6  Evaluation method"));
ch.push(p("Prediction: the verdict computed from the forecast available the evening before. Truth: the verdict computed from the same model's final analysis for that morning. Sample: 92 mornings × 5 harbours = 460 harbour-mornings per lead time, across the 2026 south-west monsoon. Scored with POD, FAR, CSI and a 3×3 confusion matrix [15]."));
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
  ["—", "Calibrate thresholds against INCOIS SVAS criteria [2]", [b("Blocked"), " — criteria not published numerically"]],
  ["—", "IMD API key for lightning and cyclone parameters", [b("Blocked"), " — requires institutional letter"]],
  ["—", "Buoy observations to replace analysis as evaluation truth", [b("Blocked"), " — requires INCOIS/NIOT data access"]],
], 18));

// ------------------------------------------------------------------ refs
ch.push(h1("References"));
[
  "B. T. M. Nair, P. Sirisha, K. G. Sandhya, et al., “Performance of the ocean state forecast system at Indian National Centre for Ocean Information Services,” Current Science, vol. 105, no. 2, pp. 175–181, 2013.",
  "Indian National Centre for Ocean Information Services, “Small Vessel Advisory and Forecast Services (SVAS),” INCOIS Ocean State Forecast portal. Available: https://incois.gov.in/portal/osf/SVA_overview.jsp",
  "A. N. Deshmukh, “Small Craft Advisory,” ITCOocean training material, INCOIS, Hyderabad.",
  "V. N. Pillai and P. G. Nair, “Potential fishing zone (PFZ) advisories — Are they beneficial to the coastal fisherfolk? A case study along Kerala coast, South India,” Biological Forum, vol. 2, no. 2, pp. 46–55, 2010.",
  "M. S. Swaminathan Research Foundation, “Fisher Friend Mobile Application,” and INCOIS multilingual advisory dissemination services. Available: https://incois.gov.in",
  "R. Lam, A. Sanchez-Gonzalez, M. Willson, et al., “Learning skillful medium-range global weather forecasting,” Science, vol. 382, no. 6677, pp. 1416–1421, 2023.",
  "K. Bi, L. Xie, H. Zhang, X. Chen, X. Gu, and Q. Tian, “Accurate medium-range global weather forecasting with 3D neural networks,” Nature, vol. 619, pp. 533–538, 2023.",
  "S. Yao, J. Zhao, D. Yu, et al., “ReAct: Synergizing reasoning and acting in language models,” in Proc. ICLR, 2023.",
  "T. Schick, J. Dwivedi-Yu, R. Dessì, et al., “Toolformer: Language models can teach themselves to use tools,” in Adv. Neural Inf. Process. Syst. (NeurIPS), vol. 36, 2023.",
  "P. Lewis, E. Perez, A. Piktus, et al., “Retrieval-augmented generation for knowledge-intensive NLP tasks,” in Adv. Neural Inf. Process. Syst. (NeurIPS), vol. 33, pp. 9459–9474, 2020.",
  "I. Kuznetsov, A. A. Jost, D. Pantiukhin, B. Shapkin, T. Jung, and N. Koldunov, “Transforming climate services with LLMs and multi-source data integration,” npj Climate Action, vol. 4, no. 1, art. 97, 2025. doi: 10.1038/s44168-025-00300-y",
  "Y. Xie, B. Jiang, T. Mallick, et al., “A RAG-based multi-agent LLM system for natural hazard resilience and adaptation,” arXiv:2504.17200, 2025.",
  "X. Lin, Y. Ning, J. Zhang, et al., “LLM-based agents suffer from hallucinations: A survey of taxonomy, methods, and directions,” arXiv:2509.18970, 2025.",
  "J. Gala, P. A. Chitale, R. AK, et al., “IndicTrans2: Towards high-quality and accessible machine translation models for all 22 scheduled Indian languages,” Transactions on Machine Learning Research (TMLR), 2023. arXiv:2305.16307",
  "I. T. Jolliffe and D. B. Stephenson, Forecast Verification: A Practitioner's Guide in Atmospheric Science, 2nd ed. Chichester, UK: Wiley-Blackwell, 2012.",
].forEach((t, n) => ch.push(ref(n + 1, t)));

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
