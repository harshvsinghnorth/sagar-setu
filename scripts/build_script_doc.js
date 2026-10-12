/* Build the mid-term presentation script, in two formats from one source:
     docs/presentation-script.md
     docs/Sagar_Setu_Presentation_Script.docx

   Mirrors scripts/build_midterm_deck.js slide for slide; edit both together.

   NODE_PATH=<dir containing node_modules/docx> node scripts/build_script_doc.js
   SCRIPT_OUT=<path> overrides the .docx location.
*/
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
  WidthType, AlignmentType, LevelFormat, ShadingType, PageBreak, BorderStyle,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");

// ===================================================================== CONTENT
const PREP = [
  "Open the deck in Presenter View — every slide has speaker notes that condense this script.",
  "Have the web interface already running with a Tamil question already answered in a second tab, in case she asks to see it. Do not start it cold in the room.",
  "Have the synopsis open at Section 2.11, the comparison table — the page she is most likely to ask about.",
  "On the three literature slides, do not read the tables. Read the study name, one finding, then the red column. The red column is the point.",
  "Print this script. Read it twice tonight, then speak from the bold lines.",
];

const LAND = [
  "The talk follows the marking scheme: problem → literature survey → research gap → objectives → methodology.",
  "The gap comes out of the literature: every survey row ends in a red “limitation for our problem”, and those limitations become G1–G6.",
  "The AI never decides safety. ClimSight's own finding — deterministic computation beats generation — supports that design.",
  "93.9 % hit rate, 3.1 % false alarms, no dangerous morning ever graded “go”. Then the asks — lead with the IMD letter.",
];

const SLIDES = [
  {
    n: 1, title: "Title", time: "0:30",
    say: [
      "Good afternoon. My project is **Sagar Setu** — “bridge to the sea” — a decision-support system for India's small-craft fishermen.",
      "In one sentence: **a fisherman asks a question in his own language and gets back a safety decision built from official government data — where the AI explains the decision but never makes it.**",
      "I will follow the review structure: the problem, the literature survey, the research gap and objectives, and the proposed methodology.",
    ],
    point: "Do not read the subtitle. Let the three coloured pills sit on screen while you say the one-sentence version.",
    bridge: "Let me start with the problem.",
  },
  {
    n: 2, title: "Introduction and problem definition", time: "1:15",
    say: [
      "Context on the left. About **four million people** depend on marine fishing in India, most on boats under twelve metres — no radar, little signal offshore.",
      "Every morning, before dawn, they make one decision: **go, or stay**. And three questions arrive together — is it safe, where are the fish, where is the border.",
      "India already publishes the answer to each. But in three separate products, as maps and bulletins.",
      "So my problem statement, on the right: **given a free-form question in an Indian language, produce one trustworthy operational answer — safety, fishing and border together — derived verifiably from official data, fast enough to use before the boat leaves, and honest when sources fail.**",
      "And one constraint that shapes everything: **the language model must never be the component that decides whether it is safe to go to sea.**",
    ],
    point: "Read the red constraint box slowly. Every design decision in the methodology traces back to it.",
    bridge: "To see what already exists, I surveyed the literature in three groups.",
  },
  {
    n: 3, title: "Literature survey I — Indian marine information services", time: "1:45",
    say: [
      "The first group is India's own marine information services. Each row reads left to right — the study, what it did, its method and data, the finding, and in red, **its limitation for my problem**.",
      "**Nair et al., 2013, in Current Science**, validated INCOIS's Ocean State Forecast against wave-rider buoys, ship-borne meters and satellite altimeters — scatter index under fifteen percent. An excellent forecast. But it validates the forecast field, not any decision.",
      "**INCOIS's Small Vessel Advisory** is the closest product to my safety work. It computes a Boat Safety Index from wave height, steepness, directional spread and wind-sea growth, per boat width. It independently confirms that steepness and vessel size matter. But it is a colour map, in English, its thresholds are not published, and it knows nothing about fishing zones or borders.",
      "**Pillai and Nair, 2010**, validated the fishing-zone advisories on the Kerala coast from 2006 to 2010 — roughly two to six times the catch inside the zones. A real benefit. But it is a bulletin.",
      "And dissemination — the **Fisher Friend app**, INCOIS's SMS and helplines — reaches nine languages, but it is broadcast. None of it accepts a question.",
      "**So India's marine data is validated and excellent. What no product does is reason across all three and answer a question.**",
    ],
    point: "Do not read every cell. For each row: bold study name, one finding, then point at the red column. The Small Vessel Advisory row deserves the most time — it is the strongest item in the review.",
    bridge: "The second group is the techniques I could build with.",
  },
  {
    n: 4, title: "Literature survey II — forecasting and AI reasoning techniques", time: "1:15",
    say: [
      "Two halves. **GraphCast and Pangu-Weather** — Science and Nature, 2023 — are machine-learned forecasting models that now rival operational prediction. They are in my review as **the road not taken**: they need decades of reanalysis and heavy compute, and they would replace a forecast INCOIS already provides, validated and free.",
      "The other three make my system possible. **Retrieval-augmented generation** grounds answers in retrieved evidence. **ReAct** interleaves reasoning with tool calls. **Toolformer** shows models learning when to call an API.",
      "Their shared limitation, in red: **grounding is encouraged, not enforced. The model still writes the answer and decides what to trust.**",
    ],
    point: "Move briskly. The one idea to land is the red column of the last three rows.",
    bridge: "The third group is the closest systems to mine — and why that limitation matters.",
  },
  {
    n: 5, title: "Literature survey III — LLM decision support, reliability, evaluation", time: "1:30",
    say: [
      "**ClimSight**, in npj Climate Action 2025, and **WildfireGPT**, 2025, are the closest relatives: multi-agent LLM systems for climate and wildfire decision support, grounded by retrieval. But they answer analytical questions for planners, ground in documents, and still let the model write the conclusion.",
      "One finding matters a lot to me. ClimSight's extension, XCLIM-AI, reports its **largest gains when indicators are computed deterministically rather than generated.** That is independent support for my design.",
      "**Lin et al., 2025**, surveyed hallucination in AI agents — five workflow stages, eighteen causes — and warn that errors can be physically consequential. That is why my verification is mechanical, not a prompt instruction.",
      "**IndicTrans2** covers all 22 scheduled languages — translation is solved, but nobody has attached it to a marine system. And **Jolliffe and Stephenson** give the standard way to score warnings, POD and FAR — which nobody in this domain has applied to the verdict itself.",
    ],
    point: "Pause on the ClimSight finding. It is the single strongest piece of external support for the whole architecture.",
    bridge: "Putting the three groups side by side gives the research gap.",
  },
  {
    n: 6, title: "Research gap — comparative analysis", time: "1:45",
    say: [
      "Every row here is a study from the survey. Across the top, the properties my problem needs.",
      "The **Small Vessel Advisory** is the only one with a deterministic safety verdict — and it fails every other column. The fishing-zone advisories and Fisher Friend reach many languages, but they are broadcast. **ClimSight and WildfireGPT** are conversational, but they ground in documents and let the model conclude.",
      "Nobody has the bottom row.",
      "So the gap: **no published system lets a fisherman ask one question in his own language and receive a single operational decision — safety, fishing and border together — that is provably derived from official products rather than generated by a model.**",
    ],
    point: "Walk the table row by row with your hand. Pause after “Nobody has the bottom row.” This is the 5-mark research-gap slide.",
    bridge: "That breaks down into six specific gaps, and each one becomes an objective.",
  },
  {
    n: 7, title: "Research gaps and objectives", time: "1:15",
    say: [
      "On the left, each gap with its evidence from the survey. On the right, the objective that answers it.",
      "Fragmentation and broadcast-only, **G1 and G2**, become **O1**: one conversational interface across all three products. Language depth becomes **O4**.",
      "**G4 and G5 are the important ones.** Grounding is only at document level and hallucination is unsolved — so **O3**, an evidence ledger and a verifier that deletes any unsupported number. And no architecture keeps safety out of the model — so **O2**, a deterministic, tested safety verdict that sits structurally outside it.",
      "**G6**, evaluation that stops at RMSE, becomes **O6**: evaluate the verdict. And because connectivity at sea is unreliable, **O5**: always answer, and say when the answer is degraded.",
      "**O2 and O3 are my research contribution.**",
    ],
    point: "Trace one or two rows across the table with your hand so the gap → evidence → objective link is visible.",
    bridge: "Here is how the methodology delivers them.",
  },
  {
    n: 8, title: "Proposed methodology I — architecture and techniques", time: "1:15",
    say: [
      "Five steps. The diagram on the right is the same pipeline — **blue is AI, red is no AI.**",
      "Step one, an LLM planner turns the question into a typed task graph, validated against a schema. Step two, three specialists fetch data in parallel through LangGraph, with a cache, live, stale, snapshot fallback chain.",
      "**Below the red line there is no model.** Step three is the decision: seven parameters, three vessel classes, the worst parameter wins — never an average. Under fifty milliseconds, 115 unit tests.",
      "Step four, the model explains the verdict in the user's language. Step five, every number in that answer, in Latin or Indic digits, is matched against the **evidence ledger**; anything unsupported is stripped and the answer regenerated.",
      "The ledger is what makes that possible: **no tool returns a bare number** — every value carries its source, time, distance and confidence.",
    ],
    point: "Tap the red dashed line in the diagram when you say “below the red line there is no model.”",
    bridge: "And the dataset behind it.",
  },
  {
    n: 9, title: "Proposed methodology II — dataset and tools", time: "1:30",
    say: [
      "**Every source here was tested live before I wrote any code against it.**",
      "**Open-Meteo** marine and weather is the primary source for waves, wind and visibility — hourly, free, no key. **INCOIS** provides the daily fishing-zone advisories, plus 14 sectors and 1,223 named landing centres. **Marine Regions** provides India's EEZ and the IMBL. Chlorophyll comes from **NOAA** and **Copernicus**, where I have an account.",
      "Two red rows, honestly. **IMD** — cyclone and lightning — needs an API key; without it, two of the seven safety checks have no data. And **INCOIS's open ERDDAP archive is stale** — its sea temperature series stops in 2011 — so it is not used.",
      "Two derived datasets: a frozen seven-day snapshot for five harbours and the Gulf of Mannar, so it runs offline; and a 92-day evaluation set. Tools are along the bottom. **Total data cost: zero.**",
    ],
    point: "She cares most about datasets — slow down here. Raise the two red rows yourself before she asks.",
    bridge: "Finally, how well it works so far.",
  },
  {
    n: 10, title: "Evaluation method and preliminary results", time: "1:15",
    say: [
      "Last review, you asked how often we are right. Prediction is the verdict from the evening-before forecast; truth is the verdict from the model's analysis of that morning; **460 harbour-mornings** through the monsoon.",
      "Day ahead, **93.9 %** of dangerous mornings were warned, and only **3.1 %** of warnings wasted a good day. **Both misses were graded caution — none were graded go.** It fails toward safety.",
      "The limitation: truth here is model analysis, not a buoy, so this is an **upper bound**.",
      "Four of six phases are complete. Three things would materially improve it: **an IMD API key, which needs a letter on college letterhead**; INCOIS's small-craft criteria; and buoy data from INCOIS or NIOT.",
      "Thank you. I am happy to take questions.",
    ],
    point: "Say each of the three needs, then stop talking. Advance to the references slide and leave it on screen during questions.",
    bridge: null,
  },
];

const TIMING = [
  ["1 – 2", "Opening and problem definition", "1:45"],
  ["3 – 5", "Literature survey (three slides)", "4:30"],
  ["6 – 7", "Research gap and objectives", "3:00"],
  ["8 – 9", "Methodology: architecture, dataset, tools", "2:45"],
  ["10", "Evaluation and status", "1:15"],
  ["11", "References — leave on screen for questions", "—"],
];
const TOTAL = "≈ 13:15";
const CUT = "If you are told to cut to eight minutes: on slide 4 say only the red-column line; on slide 7 cover only G4/G5 → O2/O3; on slide 9 cover only the two red rows. Never cut slides 3, 5 or 6 — they carry the 15 literature-and-gap marks.";

const QA = [
  { q: "How did you choose the literature?",
    a: "Three groups, matching the three parts of the problem. First, the domain: India's own marine information services, because that is what a fisherman uses today. Second, the techniques I could build with: machine-learned forecasting as the alternative I rejected, and tool-using language models as the approach I took. Third, the closest systems to mine, plus reliability and evaluation. Every reference was checked against its publisher or repository record." },
  { q: "Why not just let the AI decide? The models are very good now.",
    a: "Three reasons. I cannot test it — a rule table can be unit-tested and audited by anyone; a model's judgement cannot. There is no training data for it — no dataset of boats that did and did not come back. And Lin et al. show agent errors can be physically consequential. If someone drowns, “the model decided” is not an acceptable answer. The model is very good at language, so I use it for language." },
  { q: "Isn't this just a wrapper around some APIs? Where is the novelty?",
    a: "The fetching is ordinary engineering. The contribution is O2 and O3: an architecture where the safety verdict is structurally outside the model, not just prompted to be; and an evidence ledger with a verifier that mechanically deletes any number the model produced that is not in it. ClimSight and WildfireGPT ground in documents and still let the model write the conclusion." },
  { q: "How is your work different from INCOIS's Small Vessel Advisory?",
    a: "SVAS is the closest existing product and I build on it rather than compete with it. It gives a boat safety index as a colour map, in English, with unpublished thresholds, and separately from fishing zones and borders. My system takes a question in the user's language, combines safety, fishing zones and boundary warnings for one boat, place and time, and shows the source of every number. SVAS is also my calibration target — it independently uses steepness and vessel size, as I do." },
  { q: "Where does 93.9 % come from? Is that a real measurement?",
    a: "It is a backtest over 92 mornings at five harbours through this monsoon — 460 harbour-mornings. For each, I take the forecast available the evening before, run it through my safety engine, and compare that verdict with the verdict from the same model's final analysis. That is standard warning verification from Jolliffe and Stephenson. It regenerates with one command." },
  { q: "But you have no buoy data. So how do you know you are right?",
    a: "I do not, fully, and the synopsis says so. My truth is the model's analysis, not a physical measurement, so my figures are an upper bound. The harness is written so that with buoy observations I change the truth source and rerun. That is one of my three asks." },
  { q: "This is an ISRO/INCOIS problem statement, but your primary source is Open-Meteo. Why?",
    a: "Because INCOIS's own open data archive is largely stale — their public sea-temperature series stops in 2011 and chlorophyll in 2006. I tested all of it before writing any code. I use INCOIS for what is live and excellent: fishing-zone advisories, sector and landing-centre layers, boundary lines. Open-Meteo is the reliability floor for waves and wind. With IMD and deeper INCOIS access, Indian sources move up the fallback chain — it is built for that substitution." },
  { q: "Did you train a model?",
    a: "No, deliberately. GraphCast and Pangu-Weather are in my survey as the road not taken: training a competitive forecaster needs decades of reanalysis and compute, and would replace a product INCOIS already provides, validated and free. My contribution is reasoning over official forecasts, not replacing them." },
  { q: "What if the translation is wrong in Tamil?",
    a: "The verdict is computed before any translation, so translation cannot change it. And the verifier checks numbers in both Latin and Indic digits, so a fabricated figure is caught in Tamil too. The remaining risk is tone, which is why the target path is Bhashini, the government service — Phase 5, waiting on keys." },
  { q: "Have you validated your safety thresholds?",
    a: "Not yet, and I say so in the report and in the code. They are sensible starting values. INCOIS's Boat Safety Index is the right calibration target, but its numeric criteria are not published. Getting them is one of my asks." },
  { q: "What happens when there is no internet at sea?",
    a: "Four-step fallback: fresh cache, live fetch with a two-second budget, stale cache, then a frozen snapshot committed in the repository. It always gives a complete answer, always says which source answered, and lowers its stated confidence." },
  { q: "Will you finish it?",
    a: "Four of six phases are done and it works end to end today. What remains is the official translation path, optional features and hardening. The real risk is the three access blockers, which is why I am raising them now." },
];

const ASKS = [
  ["IMD API key", "A request letter on college letterhead. Unlocks lightning and cyclone — two of the seven safety checks are coded and tested but have no data.", "Highest value"],
  ["INCOIS small-craft criteria", "The numeric thresholds behind the Boat Safety Index. Ask whether the department has an INCOIS contact.", "Replaces “provisional”"],
  ["INCOIS / NIOT buoy data", "Turns the evaluation from model-against-model into model-against-the-sea.", "Strengthens results"],
];

const FACTS = [
  ["Phases complete", "4 of 6"],
  ["Unit tests passing", "115"],
  ["Day-ahead hit rate (POD)", "93.9 %"],
  ["Day-ahead false-alarm ratio (FAR)", "3.1 %"],
  ["Backtest sample", "92 mornings × 5 harbours = 460"],
  ["Misses graded GO", "Zero (both graded CAUTION)"],
  ["Tamil question, end to end", "~8 seconds"],
  ["Safety decision time", "under 50 ms"],
  ["Numbers recorded per question", "~130"],
  ["Named landing centres", "1,223"],
  ["PFZ sectors", "14"],
  ["References", "15, all verified"],
  ["Total external cost", "₹0"],
];

const SYNOPSIS_MAP = [
  ["Abstract", "The argument in three paragraphs, ending on the 93.9 % result."],
  ["§1  Introduction and Problem Definition", "Context, the boxed problem statement, six objectives. — 5 marks"],
  ["§2  Literature Review", "Eleven subsections plus the comparison table (2.11). — 10 marks"],
  ["§3  Research Gap", "One bold sentence, then gaps G1–G6, each mapped to an objective. — 5 marks"],
  ["§4  Proposed Methodology", "Architecture, Observation schema, threshold table, data sources, tools, evaluation method. — 5 marks"],
  ["§5  Progress and Results", "Four of six phases, 115 tests, the accuracy table, latency."],
  ["§6  Remaining Work", "Phases 5 and 6, plus three blockers with reasons."],
  ["References", "Fifteen, each checked against the publisher record."],
];

// ===================================================================== MARKDOWN
function markdown() {
  const L = [];
  L.push("# Sagar Setu — mid-term presentation script\n");
  L.push("*13 October 2026 · 11 slides (10 + references) · about 13 minutes, plus questions.*\n");
  L.push("Bold text is what to stress. Quoted blocks are stage directions, not words to say.\n");
  L.push("---\n");
  L.push("## Before you start\n");
  PREP.forEach((p) => L.push(`- ${p}`));
  L.push("\n## If you remember four things\n");
  LAND.forEach((p, i) => L.push(`${i + 1}. ${p}`));
  L.push("\n---\n");
  SLIDES.forEach((s) => {
    L.push(`## Slide ${s.n} — ${s.title}\n`);
    L.push(`**${s.time}**\n`);
    s.say.forEach((p) => L.push(`${p}\n`));
    L.push(`> *${s.point}*\n`);
    if (s.bridge) L.push(`**Bridge to slide ${s.n + 1}:** “${s.bridge}”\n`);
    L.push("---\n");
  });
  L.push("## Timing\n");
  L.push("| Slides | Content | Time |");
  L.push("|---|---|---|");
  TIMING.forEach(([a, b, c]) => L.push(`| ${a} | ${b} | ${c} |`));
  L.push(`| | **Total** | **${TOTAL}** |`);
  L.push(`\n**${CUT}**\n`);
  L.push("---\n");
  L.push("## Questions she is likely to ask\n");
  QA.forEach(({ q, a }) => { L.push(`**Q. ${q}**\n`); L.push(`${a}\n`); });
  L.push("---\n");
  L.push("## The three asks\n");
  L.push("| Ask | What it needs | Why |");
  L.push("|---|---|---|");
  ASKS.forEach(([a, b, c]) => L.push(`| ${a} | ${b} | ${c} |`));
  L.push("\n---\n");
  L.push("## If she asks about the synopsis\n");
  L.push("| Section | What is in it |");
  L.push("|---|---|");
  SYNOPSIS_MAP.forEach(([a, b]) => L.push(`| ${a} | ${b} |`));
  L.push("\n---\n");
  L.push("## Numbers worth knowing cold\n");
  L.push("| Figure | Value |");
  L.push("|---|---|");
  FACTS.forEach(([a, b]) => L.push(`| ${a} | ${b} |`));
  L.push("");
  return L.join("\n");
}

// ========================================================================= DOCX
const FONT = "Calibri";
const runs = (xs, size = 22) =>
  (Array.isArray(xs) ? xs : [xs]).map((t) =>
    typeof t === "string" ? new TextRun({ text: t, font: FONT, size }) : t);

/** Render **bold** spans inside a plain string. */
function rich(s, size = 23) {
  const out = [];
  s.split(/(\*\*[^*]+\*\*)/).forEach((part) => {
    if (!part) return;
    const m = part.match(/^\*\*([^*]+)\*\*$/);
    out.push(new TextRun({ text: m ? m[1] : part, font: FONT, size, bold: !!m }));
  });
  return out;
}

const p = (c, o = {}) => new Paragraph({ spacing: { after: 130, line: 288 }, ...o, children: runs(c) });
const b = (t) => new TextRun({ text: t, font: FONT, size: 22, bold: true });
const h1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: t, font: FONT })] });
const bullet = (c) => new Paragraph({
  numbering: { reference: "bul", level: 0 }, spacing: { after: 110, line: 288 }, children: runs(c),
});
const num = (c) => new Paragraph({
  numbering: { reference: "num", level: 0 }, spacing: { after: 110, line: 288 }, children: runs(c),
});

const direction = (t) => new Paragraph({
  spacing: { before: 140, after: 170, line: 276 },
  indent: { left: 340, right: 240 },
  border: { left: { style: BorderStyle.SINGLE, size: 16, color: "C0A000", space: 12 } },
  children: [new TextRun({ text: t, font: FONT, size: 20, italics: true, color: "6B5A00" })],
});

const cell = (content, w, head, size) => new TableCell({
  width: { size: w, type: WidthType.DXA },
  shading: head ? { type: ShadingType.CLEAR, fill: "DCE6F1", color: "auto" } : undefined,
  margins: { top: 75, bottom: 75, left: 115, right: 115 },
  children: [new Paragraph({ spacing: { after: 0 },
    children: (Array.isArray(content) ? content : [content]).map((r) =>
      typeof r === "string" ? new TextRun({ text: r, font: FONT, size, bold: !!head }) : r) })],
});
const table = (widths, rows, size = 19) => new Table({
  width: { size: widths.reduce((a, c) => a + c, 0), type: WidthType.DXA },
  columnWidths: widths,
  rows: rows.map((r, ri) => new TableRow({ tableHeader: ri === 0,
    children: r.map((c, ci) => cell(c, widths[ci], ri === 0, size)) })),
});

const ch = [];
ch.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
  children: [new TextRun({ text: "Sagar Setu — Presentation Script", font: FONT, size: 40, bold: true, color: "1F3864" })] }));
ch.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 },
  children: [new TextRun({ text: "Mid-term review  ·  13 October 2026  ·  11 slides  ·  ≈ 13 minutes", font: FONT, size: 23 })] }));
ch.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 300 },
  children: [new TextRun({ text: "Bold = stress it.   Yellow blocks = stage directions, not words to say.", font: FONT, size: 19, italics: true, color: "666666" })] }));

ch.push(h1("Before you start"));
PREP.forEach((t) => ch.push(bullet(rich(t, 22))));
ch.push(h1("If you remember four things"));
LAND.forEach((t) => ch.push(num(rich(t, 22))));

ch.push(new Paragraph({ children: [new PageBreak()] }));
ch.push(h1("The script"));
SLIDES.forEach((s) => {
  ch.push(new Paragraph({
    spacing: { before: 300, after: 60 },
    shading: { type: ShadingType.CLEAR, fill: "1F3864", color: "auto" },
    children: [
      new TextRun({ text: `  SLIDE ${s.n}  —  ${s.title}`, font: FONT, size: 23, bold: true, color: "FFFFFF" }),
      new TextRun({ text: `        ${s.time}  `, font: FONT, size: 22, bold: true, color: "BDD2E2" }),
    ],
  }));
  s.say.forEach((t) => ch.push(new Paragraph({ spacing: { after: 140, line: 300 }, children: rich(t, 23) })));
  ch.push(direction(s.point));
  if (s.bridge) {
    ch.push(new Paragraph({ spacing: { after: 160 }, children: [
      new TextRun({ text: `Bridge to slide ${s.n + 1}:  `, font: FONT, size: 20, bold: true, color: "2E5A96" }),
      new TextRun({ text: `“${s.bridge}”`, font: FONT, size: 21, italics: true, color: "2E5A96" }),
    ] }));
  }
});

ch.push(new Paragraph({ children: [new PageBreak()] }));
ch.push(h1("Timing"));
ch.push(table([1600, 5900, 1526], [
  ["Slides", "Content", "Time"],
  ...TIMING,
  [[b("")], [b("Total")], [b(TOTAL)]],
]));
ch.push(p([b(CUT)], { spacing: { before: 180, after: 140 } }));

ch.push(h1("Questions she is likely to ask"));
QA.forEach(({ q, a }) => {
  ch.push(new Paragraph({ spacing: { before: 200, after: 70 },
    children: [new TextRun({ text: `Q.  ${q}`, font: FONT, size: 23, bold: true, color: "1F3864" })] }));
  ch.push(new Paragraph({ spacing: { after: 110, line: 288 }, indent: { left: 290 }, children: rich(a, 22) }));
});

ch.push(new Paragraph({ children: [new PageBreak()] }));
ch.push(h1("The three asks"));
ch.push(p("Raise these at the end of slide 10, in this order. The first is the one that matters."));
ch.push(table([2500, 5200, 1326], [["Ask", "What it needs", "Why"], ...ASKS.map(([a, c, d]) => [[b(a)], c, d])]));

ch.push(h1("If she asks about the synopsis"));
ch.push(table([3000, 6026], [["Section", "What is in it"], ...SYNOPSIS_MAP.map(([a, c]) => [[b(a)], c])]));

ch.push(h1("Numbers worth knowing cold"));
ch.push(table([4600, 4426], [["Figure", "Value"], ...FACTS.map(([a, c]) => [a, [b(c)]])], 21));

const doc = new Document({
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, color: "1F3864", font: FONT },
        paragraph: { spacing: { before: 340, after: 160 }, outlineLevel: 0 } },
    ],
  },
  numbering: { config: [
    { reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
      alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 460, hanging: 250 } } } }] },
    { reference: "num", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.",
      alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 460, hanging: 250 } } } }] },
  ] },
  sections: [{ properties: { page: { margin: { top: 1080, bottom: 1080, left: 1120, right: 1120 } } }, children: ch }],
});

fs.writeFileSync(path.join(ROOT, "docs", "presentation-script.md"), markdown(), "utf8");
Packer.toBuffer(doc).then((buf) => {
  const out = process.env.SCRIPT_OUT || path.join(ROOT, "docs", "Sagar_Setu_Presentation_Script.docx");
  fs.writeFileSync(out, buf);
  console.log("wrote docs/presentation-script.md");
  console.log("wrote", out, (buf.length / 1e6).toFixed(2), "MB");
});
