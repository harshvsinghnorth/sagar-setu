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
  "Have the synopsis open at Section 2.8, the comparison table — the page she is most likely to ask about.",
  "On the two literature slides, do not read the tables. Read the study name, one finding, then the red column. The red column is the point.",
  "Print this script. Read it twice, then speak from the bold lines.",
];

const LAND = [
  "The talk follows the marking scheme: problem → literature survey → research gap → objectives → methodology.",
  "Eight recent, verified studies. Every survey row ends in a red “limitation for our problem”, and those limitations become G1–G6.",
  "The AI never decides safety. RAGTruth (ACL 2024) is why: even with the right data retrieved, models still produce unsupported content.",
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
    bridge: "To see what already exists, I reviewed eight studies, chosen from a wider survey of twenty for relevance and recency.",
  },
  {
    n: 3, title: "Literature survey I — the fisherman's needs", time: "2:00",
    say: [
      "The first four cover what the fisherman needs and the systems already built for him. Each row reads left to right — the study, what it did, its method and data, the finding, and in red, **its limitation for my problem**.",
      "**Kurup et al., 2024, in Weather**, built localised wind forecasts for small-boat fishers in Kerala — the WRF model downscaled to a 5 km grid. They showed local forecasts complement the official ones, which cover large ocean areas. But it is a better forecast of wind; **the go / no-go decision is still left to the fisherman.**",
      "**Sarangi et al., 2024**, generated fishing zones for the Bay of Bengal from six satellite parameters and validated them against Fishery Survey of India catch data. Chlorophyll mattered most. It produces a zone map — not linked to safety or the border. And it shows how much work a validated fishing-zone product takes, which is why **I use INCOIS's advisory rather than building my own.**",
      "The next two are the **closest existing systems**. **Thoondil**, Saka et al. 2021, is a safety app run by the Tamil Nadu Fisheries department — offline maps, weather, fishing zones, incident reporting, fifteen thousand downloads. **Fisher Friend**, Anabel et al. 2018, from the Swaminathan Foundation with INCOIS, combines fishing zones, ocean forecasts and alerts in several Indian languages.",
      "Both prove the delivery works. But both are menu screens — **the fisherman still reads each screen and combines them himself.** Neither takes a question, neither gives a verdict.",
    ],
    point: "This slide carries the most marks. Do not read every cell: study name, one finding, then point at the red column. Slow down on Thoondil and Fisher Friend — she may know them.",
    bridge: "The second four cover the border and the AI techniques.",
  },
  {
    n: 4, title: "Literature survey II — the border and the AI", time: "1:45",
    say: [
      "**Vincent, 2020, in Maritime Affairs**, analyses the Palk Bay fishing conflict and argues it needs joint India–Sri Lanka governance. It establishes that the border problem is recurring and structural. I do not try to solve the politics — only the fisherman's need to know where the line is.",
      "**Lewis et al., 2020** — retrieval-augmented generation — is the principle my system rests on: tomorrow's wave height cannot come from a model's memory, it has to be fetched when the question is asked.",
      "**Niu et al., ACL 2024 — RAGTruth — is the key paper.** Eighteen thousand answers from many language models, annotated word by word. It shows that **even when the right evidence is retrieved, models still produce unsupported content.**",
      "That is why, in my design, **the model never makes the safety call, and every number it writes is checked mechanically.**",
      "And **Gala et al., 2023 — IndicTrans2** — covers all 22 scheduled languages. Translation is solved; nobody has attached it to a conversational system for fishermen.",
    ],
    point: "Pause on RAGTruth. It is the single strongest piece of external support for the whole architecture.",
    bridge: "Putting the eight side by side gives the research gap.",
  },
  {
    n: 5, title: "Research gap — comparative analysis", time: "1:45",
    say: [
      "Every row is a study from the survey. Across the top, what my problem needs.",
      "Each study covers one or two columns. **Thoondil and Fisher Friend come closest** — safety information, fishing zones, local language. But neither answers a question, neither issues a verdict from fixed rules, and neither verifies its numbers. **RAG systems** answer questions — but RAGTruth shows they cannot be trusted with the numbers.",
      "Nobody has the bottom row.",
      "So the gap: **we found no published system that lets a fisherman ask one question in his own language and receive a single operational decision — safety, fishing and border together — derived verifiably from official data rather than generated by a model.**",
    ],
    point: "Walk the table row by row with your hand. Pause after “Nobody has the bottom row.” Note the wording: “we found no system”, not “we are the first” — it is easier to defend.",
    bridge: "That breaks down into six specific gaps, and each one becomes an objective.",
  },
  {
    n: 6, title: "Research gaps and objectives", time: "1:15",
    say: [
      "On the left, each gap with its evidence from the survey. On the right, the objective that answers it.",
      "Fragmentation and menu-driven apps, **G1 and G2**, become **O1**: one conversational interface across all three needs. Language becomes **O4**.",
      "**G4 and G5 come straight from RAGTruth.** If retrieval cannot guarantee the numbers, then **O3**: an evidence ledger and a verifier that deletes any unsupported number. And **O2**: a deterministic, tested safety verdict that sits outside the model.",
      "**G6** — the studies validate forecasts and zones, never the decision — becomes **O6**: evaluate the verdict itself. And because connectivity at sea is unreliable — Thoondil ships offline maps for exactly this reason — **O5**: always answer, and say when the answer is degraded.",
      "**O2 and O3 are my research contribution.**",
    ],
    point: "Trace one or two rows across the table with your hand so the gap → evidence → objective link is visible.",
    bridge: "Here is how the methodology delivers them.",
  },
  {
    n: 7, title: "Methodology I — architecture and techniques", time: "1:15",
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
    n: 8, title: "Methodology II — dataset and tools", time: "1:30",
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
    n: 9, title: "Evaluation method and preliminary results", time: "1:15",
    say: [
      "Last review, you asked how often we are right. Prediction is the verdict from the evening-before forecast; truth is the verdict from the model's analysis of that morning; **460 harbour-mornings** through the monsoon.",
      "Day ahead, **93.9 %** of dangerous mornings were warned, and only **3.1 %** of warnings wasted a good day. **Both misses were graded caution — none were graded go.** It fails toward safety.",
      "In the table below, the hit rate looks like it rises at two days and falls at three. **It doesn't really move: there were only 33 dangerous mornings, so one morning is about three points.** The two-day forecast caught one extra morning because it warned more often — seven false alarms instead of one. **The real trend is CSI: 91, then 80, then 65 percent.**",
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
  ["3 – 4", "Literature survey (eight studies, two slides)", "3:45"],
  ["5 – 6", "Research gap and objectives", "3:00"],
  ["7 – 8", "Methodology: architecture, dataset, tools", "2:45"],
  ["9", "Evaluation and status", "1:15"],
  ["10", "References — leave on screen for questions", "—"],
];
const TOTAL = "≈ 12:30";
const CUT = "If you are told to cut to eight minutes: on slide 3 give one line per study plus the red column; on slide 6 cover only G4/G5 → O2/O3; on slide 8 cover only the two red rows. Never cut slides 3, 4 or 5 — they carry the 15 literature-and-gap marks.";

const QA = [
  { q: "How did you choose the literature?",
    a: "I surveyed about twenty papers and selected the eight most relevant and recent, one or two for each part of the system: small-boat weather (Kurup 2024), fishing zones (Sarangi 2024), the border (Vincent 2020), the two closest existing apps (Thoondil and Fisher Friend), and the AI foundations — retrieval (Lewis), its failure mode (RAGTruth, ACL 2024) and Indian-language translation (IndicTrans2). Half are from 2023 or later, and every citation was checked against its DOI record." },
  { q: "How is this different from Thoondil or Fisher Friend?",
    a: "They are the closest existing systems and I build on them, not against them. Both deliver weather and fishing zones to fishermen in local languages, and Thoondil is operational under the Tamil Nadu government. But both are menu screens: the fisherman reads each one and decides himself. Sagar Setu accepts a free-form question about his boat, place and time; gives one verdict from tested rules; combines safety, fishing zones and the border; and shows the source of every number. Thoondil could even be a delivery channel for it." },
  { q: "Why not just let the AI decide? The models are very good now.",
    a: "Because RAGTruth shows that even when the right data is retrieved, language models still produce unsupported content. A rule table can be unit-tested and audited by anyone; a model's judgement cannot. There is also no training data for it — no dataset of boats that did and did not come back. If someone drowns, “the model decided” is not an acceptable answer. The model is very good at language, so I use it for language." },
  { q: "Isn't this just a wrapper around some APIs? Where is the novelty?",
    a: "The fetching is ordinary engineering. The contribution is O2 and O3: an architecture where the safety verdict is structurally outside the model, not just prompted to be; and an evidence ledger with a verifier that mechanically deletes any number the model produced that is not in it. That combination answers exactly the failure RAGTruth documents." },
  { q: "How is your work different from INCOIS's Small Vessel Advisory?",
    a: "SVAS gives a boat safety index as a colour map, in English, with unpublished thresholds, separately from fishing zones and borders. I cite it as my calibration target — it independently uses wave steepness and vessel size, as I do — but my system answers a question in the user's language and combines all three needs for one boat, place and time." },
  { q: "Where does 93.9 % come from? Is that a real measurement?",
    a: "It is a backtest over 92 mornings at five harbours through this monsoon — 460 harbour-mornings. For each, I take the forecast available the evening before, run it through my safety engine, and compare that verdict with the verdict from the same model's final analysis. That is standard warning verification from Jolliffe and Stephenson. It regenerates with one command." },
  { q: "Why does the hit rate go up at two days and then down at three? Shouldn't it fall steadily?",
    a: "It looks odd, but it is the sample size. Only 33 of the 460 mornings were dangerous, so the hit rates are 31, 32 and 30 out of 33 — the 2-day “rise” is one morning. The 95 % confidence intervals are roughly 80–98, 85–99 and 76–97 percent, so they overlap almost completely; statistically the hit rate is flat. The 2-day forecast caught that one extra morning by warning more often: 39 warnings instead of 32, and false alarms went from 1 to 7. Hit rate on its own rewards over-warning — if we said “do not sail” every day we would score 100 %. That is why warning systems are scored with FAR and CSI as well. CSI, which counts both misses and false alarms, falls steadily: 91, 80, 65 percent — exactly what you expect as forecast error grows with lead time. A full-year backtest would give more dangerous mornings and narrower intervals; that is planned." },
  { q: "But you have no buoy data. So how do you know you are right?",
    a: "I do not, fully, and the synopsis says so. My truth is the model's analysis, not a physical measurement, so my figures are an upper bound. With buoy observations I change the truth source and rerun. That is one of my three asks." },
  { q: "This is an ISRO/INCOIS problem statement, but your primary source is Open-Meteo. Why?",
    a: "Because INCOIS's own open data archive is largely stale — their public sea-temperature series stops in 2011. I tested all of it before writing any code. I use INCOIS for what is live and excellent: fishing-zone advisories, sector and landing-centre layers, boundary lines. Open-Meteo is the reliability floor for waves and wind. With IMD and deeper INCOIS access, Indian sources move up the fallback chain — it is built for that substitution." },
  { q: "Did you train a model?",
    a: "No, deliberately. Sarangi et al. show what producing a validated fishing-zone product takes — six satellite parameters and years of catch validation. INCOIS already does that and publishes it free; the same is true of its forecasts. My contribution is reasoning over official products, not replacing them. And a model trained on question-answer pairs would memorise answers that go stale, because the sea changes every day." },
  { q: "What if the translation is wrong in Tamil?",
    a: "The verdict is computed before any translation, so translation cannot change it. And the verifier checks numbers in both Latin and Indic digits, so a fabricated figure is caught in Tamil too. The remaining risk is tone, which is why the target path is Bhashini, the government service, with IndicTrans2 as backup — Phase 5, waiting on keys." },
  { q: "Have you validated your safety thresholds?",
    a: "Not yet, and I say so in the report and in the code. They are sensible starting values. INCOIS's Boat Safety Index is the right calibration target, but its numeric criteria are not published. Getting them is one of my asks." },
  { q: "What happens when there is no internet at sea?",
    a: "Four-step fallback: fresh cache, live fetch with a two-second budget, stale cache, then a frozen snapshot committed in the repository. It always gives a complete answer, always says which source answered, and lowers its stated confidence. Thoondil's offline maps show the same constraint is real." },
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
  ["Studies reviewed", "8 (of ~20 surveyed), half from 2023 or later"],
  ["References", "10 (8 literature + 2 methodology), all DOI-checked"],
  ["Total external cost", "₹0"],
];

const SYNOPSIS_MAP = [
  ["Abstract", "The argument in three paragraphs, ending on the 93.9 % result."],
  ["§1  Introduction and Problem Definition", "Context, the boxed problem statement, six objectives. — 5 marks"],
  ["§2  Literature Review", "Eight studies in seven subsections, each ending in its limitation for this problem; comparison table in 2.8. — 10 marks"],
  ["§3  Research Gap", "One bold sentence, then gaps G1–G6 with evidence, mapped to objectives. — 5 marks"],
  ["§4  Proposed Methodology", "Architecture, Observation schema, threshold table, data sources, tools, evaluation method. — 5 marks"],
  ["§5  Progress and Results", "Four of six phases, 115 tests, the accuracy table, latency."],
  ["§6  Remaining Work", "Phases 5 and 6, plus three blockers with reasons."],
  ["References", "Eight reviewed studies plus two methodology references, each checked against its DOI record."],
];

// ===================================================================== MARKDOWN
function markdown() {
  const L = [];
  L.push("# Sagar Setu — mid-term presentation script\n");
  L.push("*13 October 2026 · 10 slides (9 + references) · about 12 minutes, plus questions.*\n");
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
  children: [new TextRun({ text: "Mid-term review  ·  13 October 2026  ·  10 slides  ·  ≈ 12 minutes", font: FONT, size: 23 })] }));
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
ch.push(p("Raise these at the end of slide 9, in this order. The first is the one that matters."));
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
