/* Build the mid-term presentation script, in two formats from one source:
     docs/presentation-script.md
     docs/Sagar_Setu_Presentation_Script.docx

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
  "Open the deck in Presenter View — the speaker notes on every slide are a condensed version of this script.",
  "Have the web interface already running and a Tamil question already answered in a second tab, in case she asks to see it live. Do not start it cold in the room.",
  "Have the synopsis open at the comparison table (Section 2.11) — that is the page she is most likely to want to look at.",
  "If the wifi is unreliable, say so at the start and demo from the frozen snapshot. The system is built to do that. Degrading loudly is part of the design, not an excuse.",
  "Print this script. Do not read it word for word — read it twice tonight, then speak from the bold lines.",
];

const LAND = [
  "Four of six phases are done. It works today — a Tamil question answers in about eight seconds.",
  "93.9 % hit rate, 3.1 % false alarms. It never said “go” on a dangerous morning.",
  "The AI never decides safety. That is the research contribution, and the literature supports it.",
  "Three specific asks. Lead with the IMD letter.",
];

const SLIDES = [
  {
    n: 1, title: "Title — Sagar Setu", time: "0:30",
    say: [
      "Good afternoon. My project is called **Sagar Setu** — it means “bridge to the sea”.",
      "It is a decision-support system for India's small-craft fishermen.",
      "The one-sentence version: **a fisherman asks a question in his own language, and gets back a safety decision built from official government data — where the AI explains the decision but never makes it.**",
      "That last part is the research contribution, and I will keep coming back to it.",
    ],
    point: "Do not read the subtitle aloud. Let the three coloured pills — GO, CAUTION, DO NOT SAIL — sit on screen while you say the one-sentence version.",
    bridge: "Let me start with the person this is for.",
  },
  {
    n: 2, title: "One decision, made in the dark", time: "1:15",
    say: [
      "About **four million people** depend on marine fishing in India. Most work boats under twelve metres — open boats, no radar, no weather fax, often no signal once they are out.",
      "They make one decision a day, and they make it in the dark, before the boat leaves. **Go, or stay.**",
      "Wrong in one direction costs a day's income. Wrong in the other can cost the boat, and the crew.",
      "Two more questions ride along with it. *Where should I fish* — the difference between a full hold and a wasted tank of diesel. And in the Palk Bay, *where is the border* — because Indian fishermen are detained by the Sri Lankan Navy every year, and a maritime boundary is invisible from a boat.",
      "Here is the thing. **India already publishes the answers to all three.** Three separate government products.",
    ],
    point: "Point at the three stat cards on the right as you land the last line — four million, three products, zero that accept a question.",
    bridge: "So let me show you what already exists, because that is where my literature review starts.",
  },
  {
    n: 3, title: "What India already publishes", time: "1:30",
    say: [
      "INCOIS — the Indian National Centre for Ocean Information Services — runs the **Ocean State Forecast**. Waves, wind, currents, sea temperature. Nair and colleagues published its validation in *Current Science* in 2013, checked against buoys, ship-mounted wave meters and satellite altimeters. Scatter index under fifteen percent. It is good.",
      "Second — and I only found this while writing the literature review — INCOIS also publishes a **Small Vessel Advisory**. It gives a *Boat Safety Index*: where small boats risk overturning, ten days ahead. Built from wave height, wave **steepness**, directional spread, and how fast the wind sea is building. Issued per boat width.",
      "Third, the **Potential Fishing Zone** advisories. Pillai and Nair validated these along the Kerala coast in 2010 — catch and profit both measurably higher inside the notified zones.",
      "So the data is excellent. **I want to be clear that I am not trying to improve on any of this.**",
      "But all three are maps and bulletins. **None of them answers a question, and none of them knows the other two exist.**",
    ],
    point: "Point at the red bar along the bottom for the last line. If she looks interested in the Small Vessel Advisory, that is a good sign — it is the strongest thing in your literature review and it comes back on slide 8.",
    bridge: "The other half of the literature is the AI side.",
  },
  {
    n: 4, title: "What the AI literature says", time: "1:30",
    say: [
      "On the left: **grounding a model in tools works.** ReAct and Toolformer showed models can plan and call external tools instead of recalling facts. Retrieval-augmented generation established grounding an answer in retrieved evidence. And two systems are close relatives of mine — ClimSight for climate advice, WildfireGPT for wildfire decisions. Both multi-agent, both grounded.",
      "One finding I want to flag, because it supports my design independently: **ClimSight's extension reports its biggest gains when the indicators are computed deterministically rather than generated by the model.** They arrived at that separately from me.",
      "On the right is the problem. **Lin and colleagues surveyed hallucination in AI agents** — five failure types, eighteen causes. They warn that agent errors can be, their phrase, “physically consequential”. And there is a failure mode called **tool bypass**, where the model simulates a tool's output instead of actually calling it — which defeats auditing exactly when auditing matters most.",
      "So telling a model “only use the data provided” is **not a guarantee**. If I am making a safety claim, an unsupported number has to be removed mechanically. Not discouraged.",
    ],
    point: "This slide is doing the heavy lifting for the 10-mark literature criterion. Do not rush it. The left card is why the approach is possible; the right card is why the approach has to be careful.",
    bridge: "Which brings me to the gap.",
  },
  {
    n: 5, title: "The gap", time: "2:00",
    say: [
      "**This table is my research gap.** Down the left, the systems I reviewed. Across the top, five properties.",
      "The Ocean State Forecast — not conversational, produces no verdict. The **Small Vessel Advisory does** produce a deterministic safety verdict, the only one here that does — but it is a colour-coded map, in English, and it knows nothing about fishing zones or borders.",
      "The fishing zone advisories reach ten languages, but they are bulletins. The Fisher Friend app reaches nine languages — but it is broadcast. It pushes. It does not listen.",
      "Then the AI systems. ClimSight and WildfireGPT are conversational — but they ground in **documents**, not live numbers, they are English-only, and crucially **they still let the model write the conclusion**.",
      "Nobody has the bottom row.",
      "So the gap in one sentence: **no published system lets a fisherman ask one question in his own language and receive a single operational decision — safety, fishing and border together — that is provably derived from official products rather than generated by a model.**",
      "In the synopsis I break that into six specific gaps, G1 to G6, and each one maps to an objective.",
    ],
    point: "Slow down. This is the 5-mark research-gap criterion and the single most important slide in the deck. Walk the table row by row with your hand. Pause after “Nobody has the bottom row.”",
    bridge: "So those gaps turn into six objectives.",
  },
  {
    n: 6, title: "Objectives", time: "1:00",
    say: [
      "**O1** — integrate the three products behind one conversation.",
      "**O2**, and this is a research objective — make the safety verdict come from deterministic, tested rules that sit structurally outside the model's reach.",
      "**O3**, the other research one — record every number with its source before it is used, and mechanically delete any number in the answer that is not in that record.",
      "**O4**, work end to end in Indian languages. **O5**, always answer honestly when sources fail, and say when the answer is degraded. **O6**, evaluate at the level the user acts on — the verdict.",
      "**O2 and O3 are the contribution. The rest is good engineering.**",
    ],
    point: "Go fast here. Six items, one line each. The last line is the one that matters — it tells her where to look for novelty.",
    bridge: "Here is how it is built.",
  },
  {
    n: 7, title: "Architecture", time: "1:30",
    say: [
      "Five steps, top to bottom. **Blue means AI. Red means no AI.**",
      "Step one, the model reads the question — language, place, day, boat size. Step two, three collectors fetch data **at the same time**: sea conditions, maps and borders, fish data. Running them in parallel is what keeps it fast.",
      "This red line is the design. **Below it there is no AI at all.**",
      "Step three is the safety decision — seven checks against a threshold table for that size of boat. Pure Python. A hundred and fifteen unit tests. Under fifty milliseconds.",
      "Step four, the model writes the answer in the user's language. Step five, **every number in that answer is traced back to the ledger** — anything unsupported is removed and the answer rewritten.",
      "On the right is the **evidence ledger** — every number the system finds, with where it came from and how fresh it is. A typical question records about a hundred and thirty numbers, and the user sees them under every answer.",
      "**The model never computes the verdict, never adjusts it, never softens it.**",
    ],
    point: "Trace the figure with your finger as you go down it. Stop and tap the red dashed line when you say “below it there is no AI at all.”",
    bridge: "One rule shapes that whole safety engine.",
  },
  {
    n: 8, title: "The rule that shapes everything", time: "1:00",
    say: [
      "**The worst parameter decides. Never an average.**",
      "Seven checks — wave height, wind, steepness, lightning, cyclone, visibility. If any one of them says do not sail, the verdict is do not sail, however calm the rest look.",
      "**Averaging six parameters is how you build a system that sends a boat out under a thunderstorm because the waves happened to be flat.**",
      "And missing data can never produce a “go”. If I do not have wind, I do not say go.",
      "One honest caveat. **These numbers are provisional.** They are sensible starting values, not INCOIS's published criteria. I know the calibration target now — the Boat Safety Index I mentioned earlier — but INCOIS does not publish the numbers behind it. That is one of my three asks at the end.",
    ],
    point: "Raising the caveat yourself is worth more than being caught by it. Say it plainly and move on — do not apologise for it.",
    bridge: "Last review, the question was: how often are you right. Here is the answer.",
  },
  {
    n: 9, title: "How often is it right?", time: "1:30",
    say: [
      "I ran the system over **92 mornings across five harbours** — 460 harbour-mornings — through this year's south-west monsoon.",
      "When it said “do not sail” the day before, it was right **93.9 %** of the time. And only **3.1 %** of its warnings wasted a good day. That second number matters as much as the first — you cannot keep telling a man not to work.",
      "And this is the part I am most pleased with. There were **two misses. Both were graded caution.** Not one dangerous morning was ever graded “go”. That is exactly the asymmetry the worst-of rule is designed to produce — **it fails toward safety.**",
      "Skill drops as you forecast further out, mostly through false alarms — which is why the interface presents the day-ahead verdict as the decision and longer leads as outlook.",
      "Now the honest limit, before you ask it. My “truth” here is the same weather model's **final analysis — not a buoy measurement.** There is no public INCOIS or NIOT buoy feed I can reach. So this is an **upper bound** on real skill. The harness runs unchanged the moment I get buoy data — and that is my third ask.",
    ],
    point: "This is the slide she asked for last time. Deliver the two big numbers slowly. Then point at the green card on the right — that is the safety argument, not just an accuracy figure.",
    bridge: "So where am I.",
  },
  {
    n: 10, title: "Where we are, and what we need", time: "1:30",
    say: [
      "**Four of six phases complete** — data sources verified and frozen for offline use; the tool belt and safety engine with 115 tests; the agent system; and the web interface with the map and the ledger visible.",
      "Phases five and six remain: the official Bhashini translation path, route optimisation, and offline hardening with rehearsals.",
      "**Total external cost of this project so far: zero rupees.** Every data source is free, the AI runs on a free tier, and it is hosted on this laptop.",
      "Three things would materially improve it, and I would appreciate help with them.",
      "**One, an IMD API key.** It needs a request letter on college letterhead. Without it I have no lightning and no cyclone data — two of my seven safety checks are coded and tested but inactive.",
      "**Two, INCOIS's published small-craft criteria** — the numbers behind the Boat Safety Index — so I can replace my provisional table with a sourced one.",
      "**Three, buoy observations** from INCOIS or NIOT. That turns my evaluation from model-against-model into model-against-the-sea.",
      "Thank you. I am happy to take questions.",
    ],
    point: "Do not rush the three asks — they are the point of ending here. Say each one, then stop. The IMD letter is the one you actually want; ask for it first and most clearly.",
    bridge: null,
  },
];

const QA = [
  { q: "Why not just let the AI decide? The models are very good now.",
    a: "Three reasons. First, I cannot test it — a rule table can be unit-tested and audited by anyone; a model's judgement cannot. Second, there is no training data for it: there is no dataset of boats that did and did not come back. Third, the literature says agent errors can be physically consequential and that models sometimes fake tool calls. If someone drowns, “the model decided” is not an acceptable answer. The model is very good at language, so I use it for language." },
  { q: "Isn't this just a wrapper around some APIs? Where is the novelty?",
    a: "The fetching is ordinary engineering, yes. The contribution is two things. One, an architecture where the safety verdict is structurally outside the model — not prompted to be, but unable to be. Two, the evidence ledger plus a verifier that mechanically deletes any number the model produced that is not in it. ClimSight and WildfireGPT ground in documents and still let the model write the conclusion. Nobody in this domain has done per-number provenance with a mechanical check." },
  { q: "Where does 93.9 % come from? Is that a real measurement?",
    a: "It is a backtest over 92 mornings at five harbours through this monsoon — 460 harbour-mornings. For each one I take the forecast that was available the evening before, run it through my safety engine, and compare that verdict with the verdict computed from the same model's final analysis of what actually happened. It is standard warning verification — hit rate and false-alarm ratio, from Jolliffe and Stephenson. The numbers regenerate with one command." },
  { q: "But you said you have no buoy data. So how do you know you are right?",
    a: "I do not, fully, and I say so in the synopsis. My truth is the weather model's own final analysis, not a physical measurement. That means my numbers are an upper bound — against real buoys they would be lower. The harness is written so that if I obtain buoy observations I change the truth source and rerun. That is my third ask." },
  { q: "This is an ISRO/INCOIS problem statement, but your main data source is Open-Meteo, which is European. Why?",
    a: "Honest answer: because INCOIS's own open data archive is largely stale — their public sea-temperature series stops in 2011, chlorophyll in 2006. I tested all of it before writing any code. I use INCOIS for what is live and excellent: the fishing zone advisories, the sector and landing-centre layers, and the boundary lines. Open-Meteo is the reliability floor for waves and wind because it answers in about 300 ms on a bad connection. If I get IMD and deeper INCOIS access, the Indian sources move up the chain — the fallback chain is built for exactly that substitution." },
  { q: "What datasets are you actually using?",
    a: "Live: Open-Meteo marine and weather; INCOIS Potential Fishing Zone advisories over their GeoServer; NOAA chlorophyll; Copernicus Marine, for which I have an account. Static and committed: India's EEZ polygon and boundary lines from Marine Regions, INCOIS's 14 sector polygons and 1,223 named landing centres. Plus a frozen week of real data for five harbours so the whole thing runs offline. Every endpoint was tested live before any code was written against it — that is documented in docs/data-sources.md." },
  { q: "Did you train a model?",
    a: "No, deliberately. Training a competitive forecast model needs decades of reanalysis and compute I do not have, and the product it would compete with — INCOIS's — is already validated and free. GraphCast and Pangu-Weather are in my literature review precisely as the road not taken. My contribution is reasoning over official forecasts, not replacing them." },
  { q: "What if the translation is wrong in Tamil?",
    a: "Two safeguards. The verdict is computed before any translation happens, so a translation error cannot change it. And the verifier checks numbers in both Latin and Indic digits, so a fabricated figure is caught in Tamil as well as English. The remaining risk is tone or nuance, which is why the proper path is Bhashini, the government translation service, rather than a general model — that is Phase 5, blocked on keys." },
  { q: "Have you validated your safety thresholds?",
    a: "No, and I say so in the report and in the code. They are sensible starting values. I now know the right calibration target — INCOIS's Boat Safety Index, which independently selects wave steepness just as I did — but INCOIS does not publish the numeric criteria behind it. Getting those is one of my three asks." },
  { q: "What happens when there is no internet, out at sea?",
    a: "The system falls back in four steps: fresh cache, then live fetch with a two-second budget, then stale cache, then a frozen snapshot committed in the repository. It always produces a complete answer, and it always says which one answered and lowers its stated confidence. I can demonstrate it with the wifi switched off." },
  { q: "Why four agents? The problem statement lists nine roles.",
    a: "Those nine are capabilities, not processes. A naive nine-agent chain costs about forty seconds, and a tool a fisherman uses at four in the morning cannot take forty seconds. I use a planner and four specialists, with every other capability implemented as ordinary typed Python in the tool belt. My measured end-to-end time for a Tamil question is about eight seconds." },
  { q: "Will you finish it?",
    a: "Four of six phases are done and the system works end to end today. What remains is the official translation path, two optional features, and hardening. The honest risk is not the code — it is the three access blockers, which is why I am raising them now rather than at the end." },
];

const ASKS = [
  ["IMD API key", "Needs a request letter on college letterhead. Unlocks lightning and cyclone — two of the seven safety checks are coded and tested but have no data. This is the one to push for.", "Highest value"],
  ["INCOIS small-craft criteria", "The numeric thresholds behind the Boat Safety Index. Ask whether the department has an INCOIS contact, or write as a student project.", "Replaces “provisional”"],
  ["INCOIS / NIOT buoy data", "Turns the evaluation from model-against-model into model-against-the-sea.", "Strengthens results"],
];

const FACTS = [
  ["Phases complete", "4 of 6"],
  ["Unit tests passing", "115"],
  ["Code size", "~4,700 lines Python, ~630 TypeScript"],
  ["Day-ahead hit rate (POD)", "93.9 %"],
  ["Day-ahead false-alarm ratio (FAR)", "3.1 %"],
  ["Backtest sample", "92 mornings × 5 harbours = 460 harbour-mornings"],
  ["Misses graded GO", "Zero"],
  ["Tamil question, end to end", "~8 seconds"],
  ["Safety decision time", "under 50 ms"],
  ["Numbers recorded per briefing", "~130"],
  ["Named landing centres resolvable", "1,223"],
  ["References in the synopsis", "15, all verified"],
  ["Total external cost", "₹0"],
];

const SYNOPSIS_MAP = [
  ["Abstract", "The whole argument in three paragraphs, ending on the 93.9 % result."],
  ["§1  Introduction and Problem Definition", "Who the user is, the boxed problem statement, and six numbered objectives. — 5 marks"],
  ["§2  Literature Review", "Eleven subsections: what India publishes (2.1–2.3), the last-mile problem (2.4), ML weather models as the road not taken (2.5), tool-using agents and the two closest systems (2.6–2.7), hallucination (2.8), Indian-language NLP (2.9), verification method (2.10), and the comparison table (2.11). — 10 marks"],
  ["§3  Research Gap", "One bold sentence, then six enumerated gaps G1–G6, each mapping to an objective. — 5 marks"],
  ["§4  Proposed Methodology", "Architecture figure, the Observation schema, the threshold table, the data-source table, the tech stack, and the evaluation method. — 5 marks"],
  ["§5  Progress and Preliminary Results", "Four of six phases, 115 tests, the accuracy table, and the measured latency figure."],
  ["§6  Remaining Work", "Phases 5 and 6 plus the three blockers, each marked Blocked with its reason."],
  ["References", "Fifteen, every one checked against the publisher or repository record."],
];

// ===================================================================== MARKDOWN
const strip = (s) => s.replace(/\*\*(.+?)\*\*/g, "$1");

function markdown() {
  const L = [];
  L.push("# Sagar Setu — mid-term presentation script\n");
  L.push("*13 October 2026 · 10 slides · about 13 minutes of speech, plus questions.*\n");
  L.push("Bold text is what to stress. Italic blocks are stage directions, not words to say.\n");
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
  L.push("| 1–2 | Opening and the problem | 1:45 |");
  L.push("| 3–4 | Literature review | 3:00 |");
  L.push("| 5 | The research gap | 2:00 |");
  L.push("| 6–8 | Objectives, architecture, the rule | 3:30 |");
  L.push("| 9–10 | Results and status | 3:00 |");
  L.push("| | **Total** | **≈ 13:15** |");
  L.push("\n**If you are told to cut to eight minutes:** compress slide 4 to the two bold lines, "
    + "drop the per-objective detail on slide 6, and cut the lead-time paragraph on slide 9. "
    + "Never cut slide 5 or the asks on slide 10.\n");
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
  L.push("| | |");
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
const h2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: t, font: FONT })] });
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
  children: [new TextRun({ text: "Mid-term review  ·  13 October 2026  ·  10 slides  ·  ≈ 13 minutes", font: FONT, size: 23 })] }));
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
      new TextRun({ text: `  SLIDE ${s.n}  —  ${s.title}`, font: FONT, size: 24, bold: true, color: "FFFFFF" }),
      new TextRun({ text: `          ${s.time}  `, font: FONT, size: 22, bold: true, color: "BDD2E2" }),
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
ch.push(table([2100, 5400, 1526], [
  ["Slides", "Content", "Time"],
  ["1 – 2", "Opening and the problem", "1:45"],
  ["3 – 4", "Literature review", "3:00"],
  ["5", "The research gap", "2:00"],
  ["6 – 8", "Objectives, architecture, the rule", "3:30"],
  ["9 – 10", "Results and status", "3:00"],
  [[b("")], [b("Total")], [b("≈ 13:15")]],
]));
ch.push(p([b("If you are told to cut to eight minutes: "),
  "compress slide 4 to the two bold lines, drop the per-objective detail on slide 6, and cut the lead-time paragraph on slide 9. ",
  b("Never cut slide 5, or the asks on slide 10.")], { spacing: { before: 180, after: 140 } }));

ch.push(h1("Questions she is likely to ask"));
QA.forEach(({ q, a }) => {
  ch.push(new Paragraph({ spacing: { before: 200, after: 70 },
    children: [new TextRun({ text: `Q.  ${q}`, font: FONT, size: 23, bold: true, color: "1F3864" })] }));
  ch.push(new Paragraph({ spacing: { after: 110, line: 288 }, indent: { left: 290 }, children: rich(a, 22) }));
});

ch.push(new Paragraph({ children: [new PageBreak()] }));
ch.push(h1("The three asks"));
ch.push(p("Raise these at the end of slide 10, in this order. The first is the one that matters."));
ch.push(table([2500, 5200, 1326], [
  ["Ask", "What it needs", "Why"],
  ...ASKS.map(([a, c, d]) => [[b(a)], c, d]),
]));

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
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, color: "2E5A96", font: FONT },
        paragraph: { spacing: { before: 240, after: 110 }, outlineLevel: 1 } },
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
