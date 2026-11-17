/* Build the final project report: docs/Sagar_Setu_Project_Report.docx
   Layout modelled on the department's sample report (contents → introduction → literature
   review → methodology (state-space search, CSP, CSP instance) → implementation → results →
   discussion → conclusion → references).

   NODE_PATH=<dir containing node_modules/docx> node scripts/build_report.js
   Page numbers in the contents are read from docs/report/toc_pages.json, which
   scripts/report_toc_pages.ps1 writes after rendering the document once in Word.
*/
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType,
  AlignmentType, HeadingLevel, LevelFormat, ShadingType, BorderStyle, PageBreak, TabStopType,
  Footer, PageNumber, VerticalAlign,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const FIG = path.join(ROOT, "docs", "report", "figures");
const ARCH = path.join(ROOT, "docs", "architecture");
const OUT = process.env.REPORT_OUT || path.join(ROOT, "docs", "Sagar_Setu_Project_Report.docx");
const TOC_FILE = path.join(ROOT, "docs", "report", "toc_pages.json");
// PowerShell writes UTF-8 with a byte-order mark; strip it before parsing.
const PAGES = fs.existsSync(TOC_FILE)
  ? JSON.parse(fs.readFileSync(TOC_FILE, "utf8").replace(/^﻿/, ""))
  : {};

const FONT = "Arial";
const PAGE_W = 11906, MARGIN = 1440, TEXT_W = PAGE_W - 2 * MARGIN; // A4, 1 inch margins
const TEXT_PX = Math.round((TEXT_W / 1440) * 96); // usable width in px at 96 dpi
const LINE = 360; // 1.5 line spacing

// ---------------------------------------------------------------- inline markup
// **bold**, *italic*, __underline__
function runs(text, base = {}) {
  text = text.replace(/\\\*/g, "\u0001"); // "\*" is a literal asterisk (A\* search)
  const lit = (s) => s.replace(/\u0001/g, "*");
  return parts(text, base).map((r) => r(lit));
}
function parts(text, base) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) { const s = text.slice(last, m.index); out.push((f) => new TextRun({ ...base, text: f(s) })); }
    const t = m[0];
    if (t.startsWith("**")) out.push((f) => new TextRun({ ...base, text: f(t.slice(2, -2)), bold: true }));
    else if (t.startsWith("__")) out.push((f) => new TextRun({ ...base, text: f(t.slice(2, -2)), underline: {} }));
    else out.push((f) => new TextRun({ ...base, text: f(t.slice(1, -1)), italics: true }));
    last = m.index + t.length;
  }
  if (last < text.length) { const s = text.slice(last); out.push((f) => new TextRun({ ...base, text: f(s) })); }
  return out;
}

const P = (text, opts = {}) =>
  new Paragraph({
    alignment: opts.align ?? AlignmentType.JUSTIFIED,
    spacing: { line: LINE, after: opts.after ?? 200 },
    keepNext: opts.keepNext,
    children: runs(text, opts.run),
  });
const lead = (label, text) => P(`**${label} :** ${text}`); // "Problem : …" style of the sample
const H1 = (text) =>
  new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, children: [new TextRun(text)] });
const H1same = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(text)] });
const H2 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(text)] });
const H3 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(text)] });
const sub = (text) =>
  new Paragraph({ spacing: { before: 120, after: 80 }, keepNext: true, children: [new TextRun({ text, bold: true })] });

let listId = 0;
const numberingConfigs = [];
function list(items, ordered = false, align = AlignmentType.JUSTIFIED) {
  const ref = `list${listId++}`;
  numberingConfigs.push({
    reference: ref,
    levels: [
      { level: 0, format: ordered ? LevelFormat.DECIMAL : LevelFormat.BULLET, text: ordered ? "%1." : "●",
        alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } }, run: ordered ? {} : { size: 16 } } },
      { level: 1, format: LevelFormat.BULLET, text: "○", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 1440, hanging: 360 } }, run: { size: 16 } } },
    ],
  });
  return items.map((it) => {
    const [text, level] = Array.isArray(it) ? it : [it, 0];
    return new Paragraph({
      numbering: { reference: ref, level },
      alignment: align,
      spacing: { line: LINE, after: 60 },
      children: runs(text),
    });
  });
}
const bullets = (items) => list(items, false);
const numbered = (items) => list(items, true);

// ---------------------------------------------------------------- figures
function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}
let figNo = 0;
function figure(file, caption, widthFrac = 0.95) {
  figNo++;
  const { w, h } = pngSize(file);
  const width = Math.round(TEXT_PX * widthFrac);
  const height = Math.round((width * h) / w);
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 120, after: 60 },
      keepNext: true,
      children: [new ImageRun({ type: "png", data: fs.readFileSync(file), transformation: { width, height },
        altText: { title: `Figure ${figNo}`, description: caption, name: path.basename(file) } })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 240 },
      children: [new TextRun({ text: `Figure ${figNo}: `, bold: true, size: 20 }), ...runs(caption, { size: 20 })],
    }),
  ];
}

// ---------------------------------------------------------------- tables
const border = { style: BorderStyle.SINGLE, size: 4, color: "999999" };
const borders = { top: border, bottom: border, left: border, right: border };
let tabNo = 0;
function table(head, rows, widths, caption, size = 18) {
  tabNo++;
  const total = widths.reduce((a, b) => a + b, 0);
  const scaled = widths.map((x) => Math.floor((x / total) * TEXT_W));
  scaled[scaled.length - 1] += TEXT_W - scaled.reduce((a, b) => a + b, 0);
  const cell = (text, isHead, i) =>
    new TableCell({
      borders,
      width: { size: scaled[i], type: WidthType.DXA },
      verticalAlign: VerticalAlign.CENTER,
      shading: isHead ? { fill: "E7EEF7", type: ShadingType.CLEAR, color: "auto" } : undefined,
      margins: { top: 60, bottom: 60, left: 90, right: 90 },
      children: [new Paragraph({ alignment: i === 0 ? AlignmentType.LEFT : AlignmentType.CENTER,
        children: runs(text, { size, bold: isHead || undefined }) })],
    });
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 80 }, keepNext: true,
      children: [new TextRun({ text: `Table ${tabNo}: `, bold: true, size: 20 }), ...runs(caption, { size: 20 })] }),
    new Table({
      width: { size: TEXT_W, type: WidthType.DXA },
      columnWidths: scaled,
      rows: [
        new TableRow({ tableHeader: true, children: head.map((t, i) => cell(t, true, i)) }),
        ...rows.map((r) => new TableRow({ cantSplit: true, children: r.map((t, i) => cell(t, false, i)) })),
      ],
    }),
    new Paragraph({ spacing: { after: 200 }, children: [] }),
  ];
}

// ---------------------------------------------------------------- contents
const TOC = [
  ["1.", "Introduction"],
  ["2.", "Literature Review"],
  ["3.", "Methodology"],
  ["4.", "Sagar Setu as a State-Space Search"],
  ["5.", "Sagar Setu as a Constraint Satisfaction Problem"],
  ["6.", "CSP for a Particular Instance"],
  ["7.", "System Architecture"],
  ["8.", "Implementation"],
  ["a.", "Deterministic Rule-Based Safety Engine", 1],
  ["b.", "A* Route Search", 1],
  ["c.", "Agents: Planner, Specialists and Verifier", 1],
  ["d.", "Evidence Ledger and Data Layer", 1],
  ["e.", "Cyclone and Lightning Checks", 1],
  ["f.", "Indian Languages and Offline Operation", 1],
  ["9.", "Results / Performance"],
  ["10.", "Discussion"],
  ["11.", "Conclusion and Future Work"],
  ["12.", "References"],
];
function tocPage() {
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 },
      children: [new TextRun({ text: "Table of Contents", bold: true, size: 32 })] }),
    ...TOC.map(([n, title, level]) =>
      new Paragraph({
        tabStops: [{ type: TabStopType.RIGHT, position: TEXT_W }],
        indent: { left: level ? 1440 : 360, hanging: 360 },
        spacing: { after: 140 },
        children: [new TextRun({ text: `${n}\t${title}` }), new TextRun({ text: `\t${PAGES[title] ?? ""}` })],
      })
    ),
  ];
}
// Contents tabs: number at the hanging indent, title, page number right-aligned.

// ---------------------------------------------------------------- cover
function cover() {
  const c = (text, size, opts = {}) =>
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: opts.after ?? 160 },
      children: [new TextRun({ text, size, bold: opts.bold, italics: opts.italics, color: opts.color })] });
  return [
    new Paragraph({ spacing: { before: 1800 }, children: [] }),
    c("Sagar Setu", 56, { bold: true, color: "1F4E79", after: 120 }),
    c("सागर सेतु", 32, { color: "1F4E79", after: 480 }),
    c("An Agentic, Evidence-Grounded Marine Advisory System", 28, { bold: true, after: 60 }),
    c("for Indian Small-Craft Fishermen", 28, { bold: true, after: 960 }),
    c("Project Report", 26, { after: 960 }),
    c("Submitted by", 22, { italics: true, after: 60 }),
    c("Harshvardhan Singh", 26, { bold: true, after: 480 }),
    c("Under the guidance of", 22, { italics: true, after: 60 }),
    c("Ms. Anusha Chhabra", 26, { bold: true, after: 960 }),
    c("[Department name]", 22, { after: 60 }),
    c("[Institution name]", 22, { after: 60 }),
    c("November 2026", 22),
  ];
}

// ================================================================ CONTENT
const content = [];
const add = (...xs) => xs.forEach((x) => (Array.isArray(x) ? content.push(...x) : content.push(x)));

// ---------------------------------------------------------------- 1 Introduction
add(H1("Introduction"));
add(sub("What is Sagar Setu ?"));
add(P("Sagar Setu (\"bridge to the sea\") is a conversational decision-support system for India's small-craft fishermen. A fisherman asks a question in his own language — *\"Is it safe to go out from Kochi tomorrow morning?\"*, *\"Where are the fish near Paradip today?\"*, *\"Will I cross the Sri Lanka border if I head east at 8 knots?\"* — and the system fetches live marine data from Indian government and international sources, reasons across it, and answers in the same language with a **clear verdict (GO, CAUTION or DO NOT SAIL)**, a map, and the evidence behind every number."));
add(sub("Problem Statement"));
add(P("India already publishes the information a fisherman needs before leaving harbour — wave and wind forecasts, potential fishing zone (PFZ) advisories and maritime boundaries — but as separate web products, maps and bulletins, mostly in English. The fisherman must read them and combine them himself, in the dark, before dawn. The problem is therefore stated as: **given a free-form question in an Indian language, produce one trustworthy operational answer — safety, fishing and border together — derived verifiably from official data, fast enough to be used before the boat leaves, and honest when sources fail.** One constraint shapes the whole design: **the language model must never be the component that decides whether it is safe to go to sea.**"));
add(sub("Objective"));
add(P("The aim is to develop an AI system that answers a fisherman's question in his own language by combining safety, fishing-zone and border information into one answer, where:"));
add(numbered([
  "the safety verdict is produced by fixed, tested rules, never by the language model;",
  "every number shown is traceable to an evidence ledger and checked mechanically;",
  "the answer is available in English, Tamil, Hindi and Malayalam;",
  "the system keeps answering, and says so, when the network or a data source fails; and",
  "the verdict is evaluated with standard warning-verification statistics.",
]));
add(figure(path.join(FIG, "screen_kochi_safety.png"),
  "Sagar Setu answering \"Is it safe to go out from Kochi tomorrow morning?\" — the verdict card, the explanation, the map of fishing zones and the evidence ledger."));
add(sub("Motivation"));
add(P("Marine fishing supports roughly four million people along India's 11,098 km coastline, most of them on boats under twelve metres — open or partly decked craft, usually without radar, weather fax or reliable signal offshore. Every morning, before dawn, the same decision is made: *go, or stay*. A wrong decision one way costs a day's income; the other way it can cost the boat and the crew. Two further questions ride alongside it: *where are the fish?* — the difference between a full hold and a wasted tank of diesel — and, in the Palk Bay and the Gulf of Mannar, *where is the border?* Indian fishermen are detained every year for crossing the International Maritime Boundary Line (IMBL), which is invisible at sea."));
add(P("The data to answer all three questions exists. What is missing is the last step between a government web portal and a fisherman on a beach at 4 a.m. holding an inexpensive Android phone. Recent progress in language models makes a conversational interface possible, but these models are known to state unsupported facts even when given the right evidence [7] — which is unacceptable for a safety decision. The motivation of this project is to show that both can be had at once: the convenience of a conversational AI and the reliability of a fixed safety rulebook."));
add(sub("Significance"));
add(P("The project has implications for safety, livelihoods and the trustworthy use of AI:"));
add(bullets([
  "**Safety at sea.** A single, vessel-specific go / no-go verdict replaces the work of reading several products, and it is backed by cyclone and official lightning-warning checks.",
  "**Livelihood.** Bearing and distance to the day's fishing zones, and a safe route to them, save fuel and time.",
  "**Border protection.** Predictive geofencing warns *before* the boat's heading crosses the IMBL, not after.",
  "**Trustworthy AI.** The architecture demonstrates a pattern for safety-critical assistants: the model plans and explains, while fixed rules decide and a verifier checks every number.",
  "**Zero cost.** Every data source and tool used is free; the system runs on a laptop.",
]));
add(sub("Challenges"));
add(P("Developing Sagar Setu involved several difficulties:"));
add(bullets([
  "**Unreliable data sources.** Government servers are slow, change shape, or serve stale data — on 13 November 2026 the INCOIS fishing-zone service returned a 70-day-old advisory. Every source therefore needed a timeout, a fallback and an honest label.",
  "**Connectivity at sea and at demonstrations.** The system had to give a complete, honestly labelled answer with the network unplugged.",
  "**Language.** Questions arrive in Tamil, Hindi, Malayalam and mixed Hindi-English, with place names inflected by case endings.",
  "**Model hallucination.** Language models can introduce numbers that are not in the data; these had to be caught mechanically.",
  "**Restricted official feeds.** The India Meteorological Department (IMD) API requires an access key that could not be obtained within the project, so free alternatives for cyclones and lightning had to be found and validated.",
  "**Geometry.** Coastlines, islands and the IMBL had to be represented precisely enough to route a boat around them.",
]));
add(sub("Novelty Proposed"));
add(P("The novelty lies in the combination and in the discipline of the design. A language model sits on **both sides** of a deterministic core: it interprets the question and explains the answer, but a unit-tested rule engine decides safety using a **worst-of rule** (one do-not-sail parameter makes the whole verdict do-not-sail; nothing is averaged). An **evidence ledger** records the source, valid time, distance and freshness of every value, and a **verifier** rejects any number in the generated answer that is not in it. The system adds **predictive border warnings**, an **A\\* route search** that keeps the boat inside Indian waters and grades the whole route, **cyclone and official lightning-warning checks** from free sources, and a **deterministic Tamil, Hindi and Malayalam path that works offline**. Finally, the verdict is **evaluated the way warnings are evaluated** — hit rate, false-alarm ratio and critical success index — rather than by model-fit metrics alone."));

// ---------------------------------------------------------------- 2 Literature review
add(H1("Literature Review"));
add(P("Eight studies were selected from a wider survey of twenty, each bearing directly on one component of the system, with preference for recent work."));
add(P("In the paper [1], Kurup et al. tested whether localised marine weather forecasts could support safer artisanal fishing on the Kerala coast. Using the Weather Research and Forecasting (WRF) model downscaled to a 5 km grid and issuing forecasts for 25 km × 25 km zones, they identified three coastal sub-regions with distinct wind regimes and showed that localised forecasts complement the official ones, which cover large ocean areas. The study establishes that a small-boat decision needs local information; however, it produces a better wind *forecast* and leaves the go / no-go decision to the fisherman."));
add(P("Sarangi et al. in paper [2] generated Potential Fishing Zones for the western Bay of Bengal from six satellite-derived parameters — chlorophyll, sea-surface-temperature fronts, relative winds, current vectors, Ekman transport and eddies — and validated them against Fishery Survey of India catch data for 2016–2018. Chlorophyll correlated most strongly with catch. The result is a zone map with no link to sea safety, the user's boat or the border, and it shows the effort a validated PFZ product requires; this is why Sagar Setu **consumes** the official INCOIS PFZ advisory rather than re-deriving it."));
add(P("The paper [3] by Saka et al. describes **Thoondil**, a web-GIS and mobile application operated by the Tamil Nadu Department of Fisheries after a series of cyclones. It offers offline maps with routes to the nearest port, weather information, fishing zones and incident reporting in the local language, and passed 15,000 downloads within months. Similarly, the **Fisher Friend Mobile Application** in paper [4] by Anabel et al., developed by the M. S. Swaminathan Research Foundation with INCOIS, combines fishing zones, GPS navigation, ocean-state forecasts, alerts and market prices in several Indian languages. Both prove that mobile delivery in local languages works, but both are menu-and-screen applications: the fisherman navigates categories and combines the layers himself, and neither issues a vessel-specific go / no-go verdict from a free-form question."));
add(P("Vincent in paper [5] analyses the persistent Palk Bay fishing conflict across the India–Sri Lanka IMBL and argues for joint Indo–Sri Lankan governance, establishing that the boundary problem is recurring and structural. The study offers no aid to the individual fisherman; Sagar Setu addresses the narrower technical need of knowing how far the boundary is and whether the current heading will cross it."));
add(P("Lewis et al. in paper [6] introduced retrieval-augmented generation (RAG), which combines a language model's parametric memory with documents retrieved at query time, improving factual question answering and provenance. This is the principle Sagar Setu rests on — tomorrow's wave height cannot come from a model's training data and must be fetched when the question is asked. RAG, however, grounds answers in text passages and does not by itself guarantee that every generated claim is supported."));
add(P("The paper [7], RAGTruth by Niu et al., is a corpus of nearly 18,000 responses from several language models in retrieval-augmented settings, annotated word by word for hallucination. It shows that **unsupported content persists even when the correct evidence has been retrieved**. This is the direct justification for Sagar Setu's two central design choices: the safety verdict comes from fixed rules, and every number in the generated answer is checked mechanically against the evidence ledger."));
add(P("Finally, Gala et al. in paper [8] released IndicTrans2, the first open translation model covering all 22 scheduled Indian languages, together with a 230-million-sentence parallel corpus and the IN22 benchmark. It shows that translation is no longer the bottleneck for Indian-language services; what was missing was a conversational fisher-facing system to attach it to."));
add(table(
  ["Work", "Safety info", "Fishing zones", "Border", "Indian languages", "Free-form question", "Verdict by fixed rules", "Every number verified"],
  [
    ["Kurup et al. [1]", "✓ (wind)", "✗", "✗", "—", "✗", "✗", "✗"],
    ["Sarangi et al. [2]", "✗", "✓", "✗", "✗", "✗", "✗", "✗"],
    ["Thoondil [3]", "✓", "✓", "—", "✓", "✗", "✗", "✗"],
    ["Fisher Friend [4]", "✓", "✓", "partial", "✓", "✗", "✗", "✗"],
    ["RAG systems [6], [7]", "✗", "✗", "✗", "partial", "✓", "✗", "✗"],
    ["IndicTrans2 [8]", "✗", "✗", "✗", "✓", "✗", "✗", "✗"],
    ["**Sagar Setu**", "**✓**", "**✓**", "**✓**", "**✓**", "**✓**", "**✓**", "**✓**"],
  ],
  [22, 10, 10, 9, 11, 12, 13, 13],
  "Comparison of the reviewed work (✓ addressed, ✗ not addressed, — not described).",
  16,
));
add(P("The reviewed work therefore addresses the parts of the problem separately — localised weather, fishing zones, the boundary, mobile delivery and retrieval-grounded language models. No published system was found that lets a fisherman ask one question in his own language and receive a single operational decision — safety, fishing and border together — derived verifiably from official data rather than generated by a model."));

// ---------------------------------------------------------------- 3 Methodology
add(H1("Methodology"));
add(P("Sagar Setu combines two kinds of reasoning. Questions are interpreted and answers explained by a language model, while safety and navigation are decided by classical AI techniques: a **rule-based system** for the verdict and **informed search (A\\*)** for routes. This section formulates the navigation problem as a state-space search and the safety and route-legality problems as constraint satisfaction, then shows a concrete instance and the overall architecture."));
add(H2("Sagar Setu as a State-Space Search"));
add(lead("Problem", "Finding the safest legal sea route from a harbour to a fishing zone."));
add(P("**Problem Description :** A fisherman wants to reach the day's fishing zone. The route must stay inside India's Exclusive Economic Zone (EEZ), keep a safety margin from the IMBL, never cross land, and avoid water that is already at a do-not-sail level for his boat. Among the legal routes it should be the cheapest, where cost reflects both travel time and the sea state on each leg. The problem has two objectives:"));
add(numbered([
  "**Legality and safety :** never leave Indian waters, never come within 2 km of the IMBL, never cross land, and avoid do-not-sail water whenever any route can.",
  "**Efficiency :** minimise travel time made good, inflated by the sea state the boat would face on each heading.",
]));
add(lead("State-space Representation", "The sea around the trip is discretised into a grid of cells about 2 km wide (0.02°). Each cell is classified as open Indian sea, land, foreign waters, or within the IMBL margin, and each is linked to the nearest forecast node for wave height, period, wind and current."));
add(lead("State", "The cell the boat currently occupies, (i, j)."));
add(lead("Initial State", "The harbour cell. Harbours sit on land in the map data, so the start is snapped to the nearest passable cell (within 12 km) that is connected to the destination — this avoids starting in an enclosed lagoon such as Kochi's backwaters."));
add(lead("Goal State", "The cell of the target fishing zone — the nearest INCOIS PFZ by default, or a named one (\"PFZ #2\")."));
add(lead("Actions", "Move to one of the eight neighbouring cells (N, NE, E, SE, S, SW, W, NW), if that cell is passable."));
add(lead("Transition Model", "Given state (i, j) and action (di, dj), the next state is (i + di, j + dj), provided the new cell is passable."));
add(lead("Path Cost", "The sum over steps of *travel time × sea-state penalty*. Travel time is the step distance divided by the speed made good (boat speed plus the current component along the heading). The penalty is at least 1 and grows with wave height, wind and wave steepness relative to the boat's caution thresholds, more so when the sea is on the bow than astern."));
add(lead("Heuristic", "Great-circle distance to the goal divided by the highest possible speed (boat speed plus the strongest current). Because every penalty is at least 1, the heuristic never over-estimates the remaining cost, so it is **admissible** and A\\* returns an optimal path on the grid."));
add(lead("Objective", "Reach the goal cell with minimum path cost while satisfying every constraint, then grade the conditions along the whole route with the safety engine."));
add(lead("Search Algorithm", "A\\* search [11] over the grid, followed by string-pulling smoothing that removes unnecessary waypoints only when the straight segment between them stays in passable cells and does not touch land on the exact coastline."));

add(H2("Sagar Setu as a Constraint Satisfaction Problem"));
add(P("A Constraint Satisfaction Problem (CSP) is defined by three elements:"));
add(numbered(["Variables", "Domains", "Constraints"]));
add(P("The **safety verdict** maps naturally onto this structure, although, as with many real systems, it is solved by direct evaluation rather than by search."));
add(lead("Variables", "The seven safety parameters for the boat's sailing window: significant wave height, sustained wind (with gusts), sea steepness (Hs/T²), visibility, lightning, cyclone proximity and the maritime boundary."));
add(lead("Domains", "Each parameter takes a level in {GO, CAUTION, DO NOT SAIL}, or *missing* when no data could be obtained."));
add(lead("Constraints", "Each parameter's level is fixed by its threshold band for the boat's class (for example, wave height ≥ 2.5 m ⇒ DO NOT SAIL for a traditional craft). The overall verdict V must equal the **worst** parameter level — never an average. If wave height or wind is missing, V can never be GO. For a route, every parameter is taken at its worst point along the route."));
add(P("Because every constraint is functional — the value of each variable is determined by the data, and V by the variables — the verdict is computed in a single forward pass in well under a millisecond. **Route legality**, on the other hand, is a genuine constraint problem over grid cells, and is formulated in the next section."));
add(P("**Backtracking :** Classical CSP solvers assign variables one at a time and backtrack on a dead end. In Sagar Setu the verdict needs no backtracking because no choice is involved. Route search does explore alternatives, but A\\* handles this through its priority queue: a dead end is simply never expanded further, and the next-cheapest frontier node is taken instead."));

add(H2("CSP for a Particular Instance"));
add(P("Consider a boat leaving Rameswaram harbour for a point in the Gulf of Mannar. Rameswaram sits on an island joined to the mainland, with the Dhanushkodi spit running towards Sri Lanka, so the straight line between the two points crosses land, and the IMBL lies only about 23 km to the east."));
add(sub("Variables :"));
add(P("Each variable represents a cell of the search grid, indexed by row and column, Cell[i][j]. For this trip the grid has 45 × 36 cells covering 8.7°–9.6° N and 78.9°–79.6° E."));
add(sub("Domains :"));
add(P("The domain of each cell is the set of its possible classes:"));
add(bullets([
  "0 : open Indian sea (passable)",
  "1 : land (Natural Earth 1:10m coastline [16])",
  "2 : another country's waters (outside India's EEZ [15])",
  "3 : Indian sea within 2 km of the IMBL",
  "4 : Indian sea at a do-not-sail level for this boat",
]));
add(P("Thus the domain can be defined as the set {0, 1, 2, 3, 4}."));
add(sub("Constraints :"));
add(bullets([
  "Every cell on the route must be of class 0; class 4 is allowed only if no route avoids it, and the answer then says so.",
  "Consecutive route cells must be neighbours (one of the eight moves).",
  "Each straight leg of the final, smoothed route must not touch land on the exact coastline — a 2 km cell would otherwise step over a spit less than 1 km wide.",
  "The route starts at the harbour (snapped to open water) and ends at the destination cell.",
  "The route never enters class 2 and never passes through class 3, so it stays at least 2 km inside the IMBL at every point.",
]));
add(figure(path.join(FIG, "fig_grid_instance.png"),
  "The constraint instance off Rameswaram. A* finds a 65 km route around the Dhanushkodi spit, staying at least 7 km inside the IMBL, where the straight line would cross land.", 0.92));

add(H2("System Architecture"));
add(P("The architecture separates *understanding and explaining*, which use a language model, from *deciding*, which never does. It has five stages around a shared evidence ledger (Figure 3):"));
add(numbered([
  "**Understand the question (AI) :** detect the language; resolve the place to coordinates; extract the day, time, boat class, heading and speed; emit a typed task plan.",
  "**Collect the data :** three specialists run concurrently — Ocean & Weather, Geospatial & Boundary, and Analytics — together with the cyclone and lightning checks. Every value is written to the evidence ledger.",
  "**Decide if it is safe (no AI) :** the deterministic risk engine applies the threshold table with the worst-of rule.",
  "**Write the answer (AI) :** explain the verdict in the user's language, using only ledger values.",
  "**Check every number (no AI) :** the verifier rejects a draft containing any number not in the ledger; the model gets one retry, after which a fixed template answer is used.",
]));
add(figure(path.join(ARCH, "architecture.png"), "System architecture: AI above the dashed line, fixed rules below it, and the evidence ledger shared by every stage.", 0.72));
add(figure(path.join(ARCH, "flow.png"), "One real Tamil question traced through the five stages, with the time taken by each.", 0.95));

// ---------------------------------------------------------------- 8 Implementation
add(H1("Implementation"));
add(P("The system is implemented in Python 3.11 (back end, about 8,600 lines) and TypeScript (web interface, about 900 lines), with about 2,250 lines of automated tests. The implementation uses six major techniques:"));
add(bullets([
  "Deterministic rule-based safety engine",
  "A\\* route search",
  "Agents: planner, specialists and verifier",
  "Evidence ledger and fault-tolerant data layer",
  "Cyclone and lightning checks",
  "Indian-language and offline operation",
]));
add(table(
  ["Layer", "Technology"],
  [
    ["Language", "Python 3.11, TypeScript"],
    ["Agents and orchestration", "LangGraph state machine; Pydantic-typed tools"],
    ["Language model", "Google Gemini (free tier) with automatic fallback models; none required offline"],
    ["Web service", "FastAPI with Server-Sent Events streaming"],
    ["Geospatial", "Shapely, NumPy; Natural Earth coastline; Marine Regions EEZ and IMBL"],
    ["Interface", "React, Vite, MapLibre GL (OpenStreetMap tiles)"],
    ["Testing and tooling", "pytest (221 tests), ruff, uv"],
    ["Data sources", "Open-Meteo marine and weather, INCOIS PFZ, NOAA chlorophyll, GDACS cyclones, NDMA SACHET warnings"],
  ],
  [26, 74],
  "Technology stack. Every component is free to use.",
));

add(H3("Deterministic Rule-Based Safety Engine"));
add(P("The safety engine is a rule-based agent: its behaviour is fixed by a set of predefined condition-action rules applied to the current state of the environment. It is written in plain Python with no model involved, is fully unit-tested, and evaluates a verdict in about 0.1 ms. Its key components are:"));
add(bullets([
  "**Environment :** the sea and weather around the harbour during the sailing window, the boat's class, position and heading, and the hazard feeds.",
  "**Perception :** the engine reads the worst value of each parameter over the window from the evidence ledger (for example, the highest wave and the lowest visibility), never a raw percept.",
  "**Decision Making :** each parameter is graded against the threshold table for the boat's class, and the worst grade becomes the verdict.",
  "**Actuation :** the verdict, with the reason for each non-GO parameter and the ledger entries behind it, is passed to the answer stage and shown on the verdict card.",
]));
add(table(
  ["Parameter", "GO", "CAUTION", "DO NOT SAIL"],
  [
    ["Significant wave height", "< 1.5 m", "1.5 – 2.5 m", "≥ 2.5 m"],
    ["Sustained wind", "< 19 kt", "19 – 27 kt", "≥ 27 kt"],
    ["Sea steepness Hs/T²", "< 0.04", "0.04 – 0.06", "≥ 0.06"],
    ["Visibility", "> 5 km", "2 – 5 km", "≤ 2 km"],
    ["Cyclone (forecast cone or wind area reaches the harbour)", "beyond 120 h", "48 – 120 h", "within 48 h"],
    ["Official lightning warning", "none within 50 km", "within 50 km", "covers the harbour"],
    ["Maritime boundary on the current heading", "not within 3 h", "1.5 – 3 h", "within 90 min, or already outside"],
  ],
  [40, 18, 20, 22],
  "Safety rules for a traditional craft (< 12 m). The motorised and mechanised classes have their own tables.",
));
add(P("Three further rules complete the engine. **Worst-of wins:** one DO NOT SAIL parameter makes the whole verdict DO NOT SAIL, however benign the others are. **Missing data is never reassuring:** if wave height or wind is unavailable, the verdict cannot be GO. **Gusts escalate wind:** gusts reaching the do-not-sail wind speed raise a GO wind grade to CAUTION. The traditional-craft thresholds are the project specification's starting values; the tables for larger boats are the project's own extrapolation, and the verdict card states which applies."));

add(H3("A* Route Search"));
add(P("A\\* is an informed search algorithm that finds an optimal path between two points on a graph by combining the cost already incurred with an admissible estimate of the remaining cost [11]. It suits this problem because the sea grid has obstacles (land, foreign waters, the IMBL margin) and non-uniform step costs (sea state)."));
add(sub("Working :"));
add(numbered([
  "**Grid construction :** cells of 0.02° are classified as land (Natural Earth 1:10m — a cell is land if land touches any part of it), outside India's EEZ, or within 2 km of the IMBL, and linked to the nearest forecast node.",
  "**Forecast grid :** wave, wind and current forecasts are fetched for up to 300 points around the trip in a single request.",
  "**Snapping :** the harbour and destination are snapped to the nearest passable cells that are connected to each other.",
  "**Search :** A\\* with a priority queue expands the cell with the lowest f = g + h, where g is the sea-state-weighted travel time so far and h the admissible time-to-goal estimate. It first searches with do-not-sail cells forbidden, and only if that fails allows them and reports it.",
  "**Smoothing :** waypoints are removed while the straight segment between them stays in passable water and touches no land on the exact coastline.",
  "**Grading :** the wave, wind and period at every node along the route are written to the ledger and graded by the safety engine, so the verdict covers the whole trip, not only the harbour.",
]));

add(H3("Agents: Planner, Specialists and Verifier"));
add(P("The agents are orchestrated as a LangGraph state machine. There are four, each with a single responsibility, plus the risk engine as a plain function in the graph:"));
add(bullets([
  "**Planner :** turns the question into a typed plan — intent (safety, conditions, fishing zones, border, route, chlorophyll, general knowledge, off-topic or clarification), place, day, time, boat class, heading and speed — and a task graph with independent fetches marked to run in parallel. Common English, Tamil, Hindi and Malayalam questions are planned by deterministic keyword rules; others go to the language model with a schema and one corrective retry.",
  "**Ocean & Weather :** fetches waves, wind, visibility and sea state concurrently with the cyclone and lightning checks, and summarises the worst value of each variable in the window.",
  "**Geospatial & Boundary :** finds the nearest fishing zones with bearing and distance, checks the position against the EEZ and IMBL, projects the heading forward to predict a border crossing *before* it happens, and runs the route search.",
  "**Analytics & Causal :** compares the latest chlorophyll with its recent baseline and names a possible mechanism without asserting causation.",
  "**Synthesis & Verify :** drafts the answer in the user's language from a brief containing only ledger values and the verdict, then the verifier scans every number (including Tamil, Devanagari and Malayalam digits) against the ledger and blocks safety words where no verdict was computed. A rejected draft gets one retry; if that also fails, a fixed template answer — valid by construction — is used.",
]));

add(H3("Evidence Ledger and Data Layer"));
add(P("No tool returns a bare number. Every value becomes an *Observation* recording the variable, value and unit, the source, the time it is valid for, when it was fetched, the distance from the query point to the data point, a confidence and a note. A typical safety answer records 120–150 observations, all shown in the interface with their freshness."));
add(P("Every fetch follows a fixed chain: **fresh cache → live source (2 s budget) → older cache → frozen snapshot**, with confidence 0.95, 1.00, 0.70 and 0.50 respectively. A per-host circuit breaker skips a server for a minute after it fails to connect, so a dead network costs one timeout rather than one per question. Whenever an answer uses older or stored data, the interface shows a banner saying which data and why. A fishing-zone advisory more than three days old is flagged in the same way."));

add(H3("Cyclone and Lightning Checks"));
add(P("Because the IMD API key could not be obtained, two free, keyless sources were tested and integrated. **GDACS** (the Global Disaster Alert and Coordination System of the UN and the European Commission) [12] publishes, for every advisory of every active storm, the forecast cone of uncertainty and the area of winds of 60 km/h or more at each forecast time. The system finds when, if at all, the harbour falls inside either, and grades the hours remaining against the cyclone thresholds. **SACHET**, NDMA's national alert portal [13], carries official lightning and thunderstorm warnings issued by IMD offices and state disaster authorities; the nearest warning in force during the window is graded by the lightning-warning rule. Neither check is ever answered from stored data: an old \"no cyclone\" is not evidence, so offline the answer states that the checks could not be made."));

add(H3("Indian Languages and Offline Operation"));
add(P("When the language model is reachable it plans non-English questions and writes the answers. When it is not — no network, or the free daily quota is exhausted — a deterministic path takes over: a Tamil, Hindi and Malayalam planner matches keywords and about 90 harbour names written in Tamil, Devanagari and Malayalam script by word stem (so *இராமேஸ்வரத்தில்*, \"in Rameswaram\", is found from its stem), and the answer is assembled from translated templates that carry every number across unchanged, so the verifier treats it exactly as it treats the English template."));
add(figure(path.join(FIG, "screen_tamil.png"),
  "A Tamil question about leaving Rameswaram on a heading of 90° at 8 knots. The verdict is CAUTION because the heading reaches the Sri Lanka boundary in 94.5 minutes; the agent trace shows the time taken by each stage.", 0.95));

// ---------------------------------------------------------------- 9 Results
add(H1("Results / Performance"));
add(sub("Accuracy of the safety verdict"));
add(P("The verdict was evaluated as a warning system. For each of 92 mornings (22 June to 21 September 2026, the south-west monsoon) at the five test harbours — Kochi, Veraval, Chennai, Paradip and Port Blair, 460 harbour-mornings in all — the verdict computed from the forecast issued one, two and three days ahead was compared with the verdict computed from the same model's final analysis of that morning. Results are reported with the standard warning-verification measures [10]: the **hit rate** (share of dangerous mornings that were warned), the **false-alarm ratio** (share of warnings that were not needed) and the **critical success index** (CSI), which counts misses and false alarms together."));
add(table(
  ["Forecast lead", "Dangerous mornings warned", "Hit rate", "False alarms", "False-alarm ratio", "CSI"],
  [
    ["1 day ahead", "31 of 33", "**93.9 %**", "1", "**3.1 %**", "**91.2 %**"],
    ["2 days ahead", "32 of 33", "97.0 %", "7", "17.9 %", "80.0 %"],
    ["3 days ahead", "30 of 33", "90.9 %", "13", "30.2 %", "65.2 %"],
  ],
  [18, 22, 14, 14, 16, 16],
  "Skill of the DO NOT SAIL verdict, all five harbours pooled (460 harbour-mornings per lead).",
));
add(figure(path.join(FIG, "fig_verification.png"), "Hit rate, false-alarm ratio and critical success index of the DO NOT SAIL verdict by forecast lead.", 0.9));
add(P("The day-ahead verdict warned 31 of the 33 dangerous mornings with a single false alarm, and **no dangerous morning was ever graded GO** — the two misses were graded CAUTION, which is the behaviour the worst-of rule is designed to produce. Skill falls with lead time mainly through false alarms, so the interface presents the day-ahead verdict as the decision and longer leads as an outlook."));
add(table(
  ["Actual morning", "Said GO", "Said CAUTION", "Said DO NOT SAIL"],
  [
    ["GO", "237", "7", "0"],
    ["CAUTION", "20", "162", "1"],
    ["DO NOT SAIL", "0", "2", "31"],
  ],
  [31, 23, 23, 23],
  "Confusion matrix, one day ahead (rows: what the morning brought; columns: what was said). Three-way agreement 93.5 %.",
));
add(sub("Cyclone check on past storms"));
add(P("The cyclone check was replayed over every advisory of the four tropical cyclones GDACS lists in the north Indian Ocean since mid-2025 (Murasu, Arnab, One and Ditwah) against ten coastal harbours — 40 harbour-storm pairs. At each advisory, the system was asked whether a fisherman could go out at that moment. **All nine harbours that the storms actually reached (inside the storm's area of 60 km/h winds in its final advisory) were told DO NOT SAIL, 24 to 82 hours before the storm's closest approach, and none was missed.** One harbour received an unnecessary DO NOT SAIL (Chennai, which Ditwah passed 94 km away) and four received CAUTION only; the remaining 26 pairs correctly received no warning."));
add(figure(path.join(FIG, "fig_cyclone_replay.png"), "Hours of warning before the storm's closest approach, for every harbour reached by the four storms.", 0.9));
add(sub("Question bank"));
add(P("A bank of 53 questions a fisherman might ask was written as a test set (it is never used for training): safety, sea conditions, fishing zones, the border, routes, chlorophyll, general marine knowledge, questions with missing information and off-topic questions, in English (30), Tamil (12), Hindi (10, including mixed Hindi-English) and Malayalam (1). Each question records the understanding expected — intent, place, day, time, boat, heading and speed — and each answer is checked for behaviour: an answer is given, every number is verified, it is in the asker's language, and a verdict is given exactly when one is needed."));
add(table(
  ["Measure", "With the language model", "Network disconnected"],
  [
    ["Questions understood correctly", "**53 of 53**", "44 of 44 answerable"],
    ["Answers with every number verified", "53 of 53", "44 of 44"],
    ["Reply in the asker's language", "53 of 53", "44 of 44"],
    ["Answers behaving correctly overall", "51 of 53", "44 of 44"],
    ["Median time per question", "about 5.8 s", "about 0.2 s"],
  ],
  [40, 30, 30],
  "Question-bank results (latest runs, 13–17 November 2026).",
));
add(P("Every question in every language was understood correctly. The two answers counted as not behaving correctly were route questions from Chennai and Rameswaram: the day's INCOIS advisory contained no fishing zone within 150 km of those harbours, so there was no destination to route to, and the system said so instead of inventing one. The same questions passed on days when the advisory covered those coasts. With the network disconnected, the nine general-knowledge and off-topic questions need the language model and are answered with a message saying so in the asker's language; the other 44 are answered correctly from stored data."));
add(sub("Speed"));
add(P("The safety decision itself takes about 0.1 ms and collecting the data typically under a second. Route search on a grid of about 1,600 cells takes well under a second. Most of the response time is spent in the two language-model stages, so English questions planned by deterministic rules answer fastest; offline, answers take about 0.2 s."));
add(sub("Screens"));
add(figure(path.join(FIG, "screen_border.png"),
  "Predictive border warning: heading 90° at 8 knots from Rameswaram reaches the Sri Lanka boundary in 94.5 minutes, so the verdict is CAUTION with the advice to change heading before then.", 0.95));
add(figure(path.join(FIG, "screen_route.png"),
  "Route from Kochi to the nearest fishing zone: 47.3 km in about 3 h 32 min at 7 knots, graded along its whole length, with the cyclone and lightning checks in the answer.", 0.95));
add(figure(path.join(FIG, "screen_bank.png"), "The question-bank panel inside the interface, with the result of the last run beside each question.", 0.95));
add(sub("Software quality"));
add(P("The project has 221 automated tests covering the risk rules, geometry, route search, data sources (using saved real responses), planner, synthesis, verifier, languages and the end-to-end graph. They run in about 15 seconds and are run after every change."));

// ---------------------------------------------------------------- 10 Discussion
add(H1same("Discussion"));
add(P("The project allowed us to reach the following inferences:"));
add(P("**Rule-Based Safety Engine :**", { after: 60 }));
add(bullets([
  "Keeping the decision in fixed rules made it fast (about 0.1 ms), transparent and fully testable, and the worst-of rule produced exactly the intended asymmetry: on the backtest no dangerous morning was ever graded GO.",
  "The engine is only as good as its thresholds. The traditional-craft values are the specification's starting values; INCOIS's Small Vessel Advisory Service [9] is the natural calibration target, but it does not publish its numeric criteria.",
]));
add(P("**A\\* Route Search :**", { after: 60 }));
add(bullets([
  "A\\* with an admissible time-based heuristic found legal, optimal routes in well under a second, including around the Dhanushkodi spit and the Palk Bay corner of the IMBL.",
  "Grading the whole route, not just the harbour, matters: conditions offshore can be worse than at the harbour.",
  "Routes depend on the day's INCOIS advisory for a destination, and the coastline is a 1:10 million map, so routes are advice rather than a navigation chart, and the answer says so.",
]));
add(P("**Language-Model Agents :**", { after: 60 }));
add(bullets([
  "The planner understood all 53 questions across four languages and mixed Hindi-English.",
  "The verifier proved its worth: it caught drafts that introduced unsupported numbers or a safety word where no verdict existed, and the retry or template guaranteed a correct answer every time.",
  "On the free tier the model has a daily request limit; the automatic fallback models and the deterministic path keep the system answering when it is reached.",
]));
add(P("**Cyclone and Lightning Checks :**", { after: 60 }));
add(bullets([
  "The GDACS-based cyclone check gave one to three days of warning to every affected harbour in the replay, from a free source with no key.",
  "Official lightning warnings are short-range nowcasts covering land districts, so they protect \"go now\" decisions at the harbour; for next-day decisions the weather model's thunderstorm signal is used.",
]));
add(P("**Offline and Indian-Language Operation :**", { after: 60 }));
add(bullets([
  "With the network disconnected the system answered 44 of 53 questions correctly in about 0.2 s, in the asker's language, and stated which data was stored.",
  "Designing every source to fail loudly rather than silently was essential: it exposed real upstream problems, such as a stale fishing-zone advisory, instead of hiding them.",
]));

// ---------------------------------------------------------------- 11 Conclusion
add(H1same("Conclusion and Future Work"));
add(P("Sagar Setu demonstrates that a conversational AI can serve a safety-critical user without being trusted with the safety decision. A fisherman can ask, in English, Tamil, Hindi or Malayalam, whether to go out, where the fish are, how to get there and where the border is, and receive one answer that combines safety, fishing and border information, with every number traceable to its source. Classical AI techniques — a rule-based system and A\\* search — make the decisions; the language model interprets and explains; and a verifier stands between the model and the user."));
add(P("The system was evaluated at the level the fisherman acts on. The day-ahead DO NOT SAIL verdict warned 93.9 % of dangerous mornings with a 3.1 % false-alarm ratio and never graded a dangerous morning GO; the cyclone check warned every affected harbour one to three days ahead in a replay of four storms; and all 53 questions in the question bank were understood correctly. The system keeps working, honestly labelled, with the network disconnected, and it was built entirely with free data and tools."));
add(P("**Future work :**", { after: 60 }));
add(bullets([
  "Review of the Tamil, Hindi and Malayalam answer wording by native speakers.",
  "Calibration of the thresholds against INCOIS's small-vessel criteria, and per-beam advisories, if the criteria are published.",
  "Official IMD cyclone tracks and lightning-strike data, if API access is granted.",
  "Evaluation against buoy observations, and over a full year covering both monsoons.",
  "Voice input, and alerts pushed to fishermen at sea.",
]));

// ---------------------------------------------------------------- 12 References
add(H1("References"));
const REFS = [
  "P. H. Kurup, S. Abhilash, S. Mavath, V. K. Mini, N. Alamirew and M. Martin, \"Validation of localised coastal wind forecasts for artisan fishers of southwestern India,\" *Weather*, vol. 79, no. 7, pp. 231–241, 2024, doi: 10.1002/wea.4554.",
  "R. K. Sarangi, M. Jishad, R. Sharma *et al.*, \"Multiple ocean parameter-based potential fishing zone (PFZ) location generation and validation in the Western Bay of Bengal,\" *Environmental Monitoring and Assessment*, vol. 196, no. 1, art. 98, 2024, doi: 10.1007/s10661-023-12259-6.",
  "S. K. Saka, A. E. Mathew, V. Ganesh *et al.*, \"A Web-GIS and mobile-based application for a safe ocean for fishers,\" *Marine Technology Society Journal*, vol. 55, no. 3, pp. 50–57, 2021, doi: 10.4031/MTSJ.55.3.10.",
  "N. J. Anabel, S. Velvizhi and D. Suvitha, \"Fisher Friend Mobile Application: a decision support system for small scale fishers in India,\" *CSI Transactions on ICT*, vol. 6, no. 3–4, pp. 257–267, 2018, doi: 10.1007/s40012-018-0212-1.",
  "S. Vincent, \"Palk Bay fishing problem requires Indo-Sri Lankan joint-governance,\" *Maritime Affairs: Journal of the National Maritime Foundation of India*, vol. 16, no. 2, pp. 71–88, 2020, doi: 10.1080/09733159.2020.1838717.",
  "P. Lewis, E. Perez, A. Piktus *et al.*, \"Retrieval-augmented generation for knowledge-intensive NLP tasks,\" in *Advances in Neural Information Processing Systems (NeurIPS)*, vol. 33, pp. 9459–9474, 2020.",
  "C. Niu, Y. Wu, J. Zhu, S. Xu, K. Shum, R. Zhong, J. Song and T. Zhang, \"RAGTruth: A hallucination corpus for developing trustworthy retrieval-augmented language models,\" in *Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics (ACL)*, vol. 1, pp. 10862–10878, 2024.",
  "J. Gala, P. A. Chitale, R. AK *et al.*, \"IndicTrans2: Towards high-quality and accessible machine translation models for all 22 scheduled Indian languages,\" *Transactions on Machine Learning Research (TMLR)*, 2023, arXiv:2305.16307.",
  "Indian National Centre for Ocean Information Services, \"Small Vessel Advisory and Forecast Services (SVAS).\" [Online]. Available: https://incois.gov.in/portal/osf/SVA_overview.jsp",
  "I. T. Jolliffe and D. B. Stephenson, *Forecast Verification: A Practitioner's Guide in Atmospheric Science*, 2nd ed. Chichester, UK: Wiley-Blackwell, 2012.",
  "P. E. Hart, N. J. Nilsson and B. Raphael, \"A formal basis for the heuristic determination of minimum cost paths,\" *IEEE Transactions on Systems Science and Cybernetics*, vol. 4, no. 2, pp. 100–107, 1968, doi: 10.1109/TSSC.1968.300136.",
  "Global Disaster Alert and Coordination System (GDACS), tropical cyclone events and forecast geometry API. [Online]. Available: https://www.gdacs.org (accessed November 2026).",
  "National Disaster Management Authority, SACHET Common Alerting Protocol alert portal. [Online]. Available: https://sachet.ndma.gov.in (accessed November 2026).",
  "Open-Meteo, Marine Weather and Weather Forecast APIs. [Online]. Available: https://open-meteo.com (accessed November 2026).",
  "Flanders Marine Institute, Maritime Boundaries Geodatabase (Marine Regions): exclusive economic zones and boundary lines. [Online]. Available: https://www.marineregions.org (accessed September–October 2026).",
  "Natural Earth, 1:10m physical vectors: land and minor islands. [Online]. Available: https://www.naturalearthdata.com (accessed October 2026).",
];
add(list(REFS, true, AlignmentType.LEFT));

// ================================================================ document
const doc = new Document({
  creator: "Harshvardhan Singh",
  title: "Sagar Setu — Project Report",
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 32, bold: true },
        paragraph: { alignment: AlignmentType.CENTER, spacing: { before: 240, after: 360 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 22, bold: true, underline: {} },
        paragraph: { alignment: AlignmentType.CENTER, spacing: { before: 360, after: 240 }, keepNext: true, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 22, bold: true },
        paragraph: { spacing: { before: 360, after: 200 }, keepNext: true, outlineLevel: 2 } },
    ],
  },
  numbering: { config: numberingConfigs },
  sections: [
    {
      properties: { page: { size: { width: PAGE_W, height: 16838 }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } }, titlePage: true },
      footers: {
        default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
          children: [new TextRun({ children: [PageNumber.CURRENT], size: 20 })] })] }),
        first: new Footer({ children: [new Paragraph({ children: [] })] }),
      },
      children: [...cover(), new Paragraph({ children: [new PageBreak()] }), ...tocPage(), ...content],
    },
  ],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUT, buf);
  console.log(`wrote ${OUT} (${(buf.length / 1024).toFixed(0)} KB), ${figNo} figures, ${tabNo} tables`);
});
