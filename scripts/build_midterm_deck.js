/* Build docs/Sagar_Setu_MidTerm.pptx — the mid-term review deck.

   Structured around the marking scheme, not around a story:
     Literature review (10) · Research gap (5) · Objective / problem (5) · Methodology (5).
   Content mirrors docs/synopsis.md; edit both together.

   NODE_PATH=<dir containing node_modules> APPLY_THEME=<skill>/scripts/apply_theme.js \
     node scripts/build_midterm_deck.js
   DECK_OUT=<path> overrides the output location.
*/
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require(process.env.APPLY_THEME ||
  path.join(__dirname, "apply_theme.js"));

const ROOT = path.resolve(__dirname, "..");
const FIG = (f) => path.join(ROOT, "docs", "architecture", f);
const OUT = process.env.DECK_OUT || path.join(ROOT, "docs", "Sagar_Setu_MidTerm.pptx");

// ------------------------------------------------------------------ theme
const THEME = {
  name: "Sagar Setu",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "0F1E2E", lt1: "FFFFFF",
    dk2: "16304A", lt2: "EDF2F6",
    accent1: "065A82", accent2: "1C7293", accent3: "B03A2E",
    accent4: "1B8A5A", accent5: "D98324", accent6: "6B7C8C",
    hlink: "1C7293", folHlink: "6B7C8C",
  },
};
const H = THEME.colors;
const GAP_BG = "FBEDEB";     // tint for "limitation / gap" cells
const GAP_INK = "8E2B21";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";            // 13.333 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.author = "Harshvardhan Singh";
pres.title = "Sagar Setu — Mid-Term Review";
const C = pres.SchemeColor;

const W = 13.333, PAD = 0.55, CW = W - 2 * PAD;   // content width 12.233
const BODY_Y = 1.30;

// ------------------------------------------------------------------ layouts
pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: H.dk2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: PAD, y: 2.10, w: CW, h: 1.3,
        fontSize: 54, bold: true, color: C.background1, align: "left", valign: "bottom" }, text: " " } },
    { placeholder: { options: { name: "body", type: "body", x: PAD, y: 3.55, w: 10.5, h: 1.1,
        fontSize: 20, color: "BDD2E2", align: "left", valign: "top" }, text: " " } },
  ],
});

pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: C.background1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: PAD, y: 0.32, w: CW, h: 0.74,
        fontSize: 30, bold: true, color: C.text1, align: "left", valign: "middle" }, text: " " } },
    { text: { text: "Sagar Setu  ·  Mid-term review  ·  13 October 2026",
        options: { x: PAD, y: 7.06, w: 8, h: 0.28, fontSize: 9, color: C.accent6, isTextBox: true } } },
  ],
  slideNumber: { x: 12.45, y: 7.06, w: 0.5, h: 0.28, fontSize: 9, color: H.accent6, align: "right" },
});

// ------------------------------------------------------------------ helpers
const tx = (slide, text, o) => slide.addText(text, Object.assign({ isTextBox: true }, o));

function card(slide, x, y, w, h, fill) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.08, fill: { color: fill || H.lt2 }, line: { color: fill || H.lt2 },
  });
}

/** Small section tag above a slide title — which marking criterion this slide serves. */
function tag(slide, text, fill) {
  const w = 0.30 + text.length * 0.075;
  slide.addShape(pres.ShapeType.roundRect, { x: W - PAD - w, y: 0.47, w, h: 0.32, rectRadius: 0.16,
    fill: { color: fill || H.accent1 }, line: { color: fill || H.accent1 } });
  tx(slide, text, { x: W - PAD - w, y: 0.47, w, h: 0.32, align: "center", valign: "middle",
    fontSize: 10, bold: true, color: "FFFFFF", margin: 0 });
}

function takeaway(slide, y, text, fill, ink) {
  card(slide, PAD, y, CW, 0.62, fill || H.lt2);
  tx(slide, text, { x: PAD + 0.28, y, w: CW - 0.56, h: 0.62, valign: "middle", fontSize: 13.5,
    bold: true, color: ink || H.dk1, margin: 0 });
}

const BORDER = { type: "solid", pt: 0.6, color: "D5DDE3" };

/** Literature survey table. The last column is the limitation — the gap, for our problem. */
function survey(slide, rows) {
  const head = ["Study", "Contribution", "Method / data", "Key finding", "Limitation for our problem"];
  const colW = [2.05, 2.25, 2.85, 2.45, 2.633];
  const hdr = head.map((t, i) => ({ text: t, options: {
    fontSize: 13.5, bold: true, color: "FFFFFF", fill: { color: i === 4 ? H.accent3 : H.accent1 },
    valign: "middle" } }));
  const body = rows.map((r) => r.map((t, i) => {
    if (i === 0) {
      const [who, where] = t.split("|");
      return { text: [
        { text: who, options: { bold: true, color: H.dk1, fontSize: 14.5, breakLine: true } },
        { text: where, options: { color: H.accent6, fontSize: 12 } },
      ], options: { valign: "middle" } };
    }
    return { text: t, options: {
      fontSize: 14, color: i === 4 ? GAP_INK : "2E3E4C",
      fill: { color: i === 4 ? GAP_BG : "FFFFFF" }, valign: "middle" } };
  }));
  // Four studies per slide: rows sized to fill the space above the takeaway bar.
  const rowH = [0.5, ...rows.map(() => (5.95 - BODY_Y - 0.5) / rows.length)];
  slide.addTable([hdr, ...body], { x: PAD, y: BODY_Y, w: CW, colW, rowH,
    border: BORDER, margin: [3, 5, 3, 5], fontFace: "Calibri" });
}

// ================================================================== 1 · title
pres.addSection({ title: "Opening" });
{
  const s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Opening" });
  s.addText("SAGAR SETU", { placeholder: "title", charSpacing: 3 });
  s.addText("An agentic, evidence-grounded marine advisory system\nfor Indian small-craft fishermen",
    { placeholder: "body" });
  const verdicts = [["GO", H.accent4], ["CAUTION", H.accent5], ["DO NOT SAIL", H.accent3]];
  let vx = PAD;
  verdicts.forEach(([t, c]) => {
    const w = 0.24 + t.length * 0.105;
    s.addShape(pres.ShapeType.roundRect, { x: vx, y: 5.08, w, h: 0.40, rectRadius: 0.2,
      fill: { color: c }, line: { color: c } });
    tx(s, t, { x: vx, y: 5.08, w, h: 0.40, align: "center", valign: "middle",
      fontSize: 11, bold: true, color: "FFFFFF", margin: 0 });
    vx += w + 0.18;
  });
  tx(s, "Harshvardhan Singh   ·   Supervisor: Ms. Anusha Chhabra   ·   Mid-term review, 13 October 2026",
    { x: PAD, y: 6.36, w: CW, h: 0.32, fontSize: 13.5, color: "BDD2E2" });
  tx(s, "ISRO / INCOIS agentic marine intelligence problem statement  ·  Smart India Hackathon 2026",
    { x: PAD, y: 6.72, w: CW, h: 0.3, fontSize: 11, color: "7E9AB3" });
  s.addNotes("Sagar Setu: 'bridge to the sea'. One sentence — a fisherman asks in his own language and gets a safety decision built from official data, where the AI explains the decision but never makes it. Today's structure follows the review criteria: problem, literature survey, research gap, objectives, methodology.");
}

// ================================================================== 2 · problem
pres.addSection({ title: "Problem definition" });
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Problem definition" });
  s.addText("Introduction and problem definition", { placeholder: "title" });
  tag(s, "PROBLEM DEFINITION");

  tx(s, "Context", { x: PAD, y: BODY_Y + 0.05, w: 5.9, h: 0.36, fontSize: 17, bold: true, color: H.accent1, margin: 0 });
  s.addText([
    { text: "About 4 million people depend on marine fishing in India; most work boats under 12 m — no radar, little offshore signal.", options: { bullet: true, breakLine: true } },
    { text: "One decision a day, made before dawn: go, or stay. Wrong one way costs a day's income; wrong the other way can cost the boat and crew.", options: { bullet: true, breakLine: true } },
    { text: "Three questions arrive together: Is it safe? Where are the fish? Where is the maritime border?", options: { bullet: true, breakLine: true } },
    { text: "India already publishes the answer to each — in three separate products, as maps and bulletins.", options: { bullet: true } },
  ], { x: PAD, y: BODY_Y + 0.52, w: 5.95, h: 4.0, fontSize: 14, color: "2E3E4C", isTextBox: true,
       paraSpaceAfter: 12, lineSpacingMultiple: 1.12, valign: "top" });

  const bx = 6.85, bw = W - PAD - bx;
  card(s, bx, BODY_Y, bw, 4.38, H.lt2);
  tx(s, "Problem statement", { x: bx + 0.32, y: BODY_Y + 0.22, w: bw - 0.64, h: 0.36, fontSize: 17,
    bold: true, color: H.accent1, margin: 0 });
  tx(s, "Given a free-form question in any of India's scheduled languages, produce a single, trustworthy operational answer — safety verdict, fishing guidance and boundary warning together — derived verifiably from official marine data, fast enough to use before a boat leaves, and degrading honestly when sources fail.",
    { x: bx + 0.32, y: BODY_Y + 0.70, w: bw - 0.64, h: 2.35, fontSize: 14.5, color: H.dk1, margin: 0,
      lineSpacingMultiple: 1.15, valign: "top" });
  card(s, bx + 0.32, BODY_Y + 3.24, bw - 0.64, 0.92, GAP_BG);
  tx(s, "Constraint: the language model must never be the component that decides whether it is safe to go to sea.",
    { x: bx + 0.52, y: BODY_Y + 3.24, w: bw - 1.04, h: 0.92, valign: "middle", fontSize: 13.5,
      bold: true, color: GAP_INK, margin: 0 });

  takeaway(s, 5.95, "The gap is not data. It is the last step between a government portal and a fisherman on a beach at 4 a.m.");
  s.addNotes("Context on the left, the formal problem statement on the right. Read the constraint aloud — it shapes every design decision that follows.");
}

// ================================================================== 3 · lit I
pres.addSection({ title: "Literature survey" });
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Literature survey" });
  s.addText("Literature survey I — the fisherman's needs", { placeholder: "title" });
  tag(s, "LITERATURE 1 / 2");
  survey(s, [
    ["Kurup et al., 2024|Weather 79(7) [1]",
     "Localised coastal wind forecasts for artisan fishers, Kerala",
     "WRF model downscaled to a 5 km grid; forecasts issued per 25 × 25 km zone",
     "Localised forecasts complement official ones issued for large ocean areas",
     "Forecasts wind only; turning it into a go / no-go call is left to the fisher"],
    ["Sarangi et al., 2024|Environ. Monit. Assess. 196 [2]",
     "Multi-parameter fishing-zone generation, western Bay of Bengal",
     "Chlorophyll, SST fronts, winds, currents, Ekman transport, eddies; FSI catch data 2016–18",
     "Chlorophyll correlates most with catch, then fronts and eddies",
     "A zone map only — not linked to safety, the boat or the border"],
    ["Saka et al., 2021|MTS Journal 55(3) [3]  ·  Thoondil",
     "Fisher safety app run by Tamil Nadu Fisheries",
     "Android app: offline maps to nearest port, weather, PFZ, incident reports; web-GIS boat tracking",
     "Operational, local language, 15,000+ downloads in months",
     "Menu screens; no free-form questions; no go / no-go verdict described"],
    ["Anabel et al., 2018|CSI Trans. ICT 6(3–4) [4]  ·  Fisher Friend",
     "Decision-support app for small-scale fishers (MSSRF, INCOIS)",
     "PFZ with GPS, ocean-state forecasts, danger-zone and disaster alerts, market prices",
     "Multilingual one-stop delivery works in practice",
     "The fisher reads and combines each screen himself; no source shown per number"],
  ]);
  takeaway(s, 6.18, "The data and the delivery channels exist. Every system still leaves the fisherman to combine the pieces and make the call himself.", GAP_BG, GAP_INK);
  s.addNotes("Four studies on what the fisherman needs. Kurup: better local wind forecasts, but the decision is still his. Sarangi: fishing zones done properly need six satellite parameters and catch validation — which is why we consume INCOIS's PFZ product. Thoondil and Fisher Friend are the closest existing systems: real, operational, local-language — but menu screens, no question answering, no verdict. Read the red column.");
}

// ================================================================== 4 · lit II
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Literature survey" });
  s.addText("Literature survey II — the border and the AI", { placeholder: "title" });
  tag(s, "LITERATURE 2 / 2");
  survey(s, [
    ["Vincent, 2020|Maritime Affairs 16(2) [5]",
     "Analysis of the Palk Bay fishing conflict",
     "Governance analysis of fishing across the India–Sri Lanka IMBL",
     "The problem is recurring; argues for joint Indo–Sri Lankan governance",
     "No aid to the fisherman — the boundary stays invisible at sea"],
    ["Lewis et al., 2020|NeurIPS 33 [6]  ·  RAG",
     "Retrieval-augmented generation",
     "Language model combined with a dense retriever over Wikipedia",
     "Retrieved evidence improves factual answers and provenance",
     "Grounds in text, not live numbers; no guarantee every claim is supported"],
    ["Niu et al., 2024|ACL 2024 [7]  ·  RAGTruth",
     "Hallucination corpus for retrieval-augmented models",
     "~18,000 responses from many LLMs, annotated word by word",
     "Unsupported content persists even with the right evidence retrieved",
     "Retrieval is not enough — the safety call must stay out of the model"],
    ["Gala et al., 2023|TMLR [8]  ·  IndicTrans2",
     "Open translation for all 22 scheduled languages",
     "BPCC corpus of 230 M sentence pairs; IN22 benchmark",
     "First model to cover all 22 languages",
     "Translation is solved; no fisher system offers conversation in it"],
  ]);
  takeaway(s, 6.18, "Retrieval makes a trustworthy assistant possible; RAGTruth shows it is not sufficient. So our model never makes the safety call.", GAP_BG, GAP_INK);
  s.addNotes("Vincent establishes the border problem is structural — we do not solve the politics, only the fisherman's need to see the line. RAG is the principle: tomorrow's waves must be fetched, not remembered. RAGTruth is the key paper: even with the right data retrieved, models still produce unsupported content. That single finding justifies both research choices — fixed rules for the verdict, and a mechanical number checker.");
}

// ================================================================== 5 · gap matrix
pres.addSection({ title: "Research gap" });
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Research gap" });
  s.addText("Research gap — comparative analysis", { placeholder: "title" });
  tag(s, "RESEARCH GAP", H.accent3);

  const head = ["Work", "Small-boat\nsafety info", "Fishing\nzones", "Border\nawareness", "Indian\nlanguages", "Answers a\nquestion", "Go / no-go by\nfixed rules", "Every number\nverified"];
  const Y = "✓", N = "✗", D = "—";
  const body = [
    ["Kurup et al. [1]", Y + " (wind)", N, N, D, N, N, N],
    ["Sarangi et al. [2]", N, Y, N, N, N, N, N],
    ["Thoondil — Saka et al. [3]", Y, Y, D, Y, N, N, N],
    ["Fisher Friend — Anabel et al. [4]", Y, Y, "partial", Y, N, N, N],
    ["RAG systems [6] [7]", N, N, N, "partial", Y, N, N],
    ["IndicTrans2 [8]", N, N, N, Y, N, N, N],
  ];
  const base = { fontSize: 12.5, color: "2E3E4C", align: "center", valign: "middle" };
  const rows = [
    head.map((t, i) => ({ text: t, options: { fontSize: 11.5, bold: true, color: "FFFFFF",
      fill: { color: H.accent1 }, align: i ? "center" : "left", valign: "middle" } })),
    ...body.map((r) => r.map((t, i) => ({ text: t, options: Object.assign({}, base,
      i ? {} : { align: "left", color: H.dk1, bold: true },
      t.startsWith(Y) ? { color: H.accent4, bold: true } : {},
      t === N ? { color: "B4C0C8" } : {}) }))),
    ["Sagar Setu (proposed)", Y, Y, Y, Y, Y, Y, Y].map((t, i) => ({ text: t,
      options: { fontSize: 13, bold: true, color: i ? H.accent4 : "FFFFFF",
        fill: { color: i ? "E4F3EA" : H.dk2 }, align: i ? "center" : "left", valign: "middle" } })),
  ];
  s.addTable(rows, { x: PAD, y: BODY_Y, w: CW, colW: [2.75, 1.25, 1.2, 1.25, 1.25, 1.25, 1.55, 1.733],
    rowH: 0.42, border: BORDER, margin: 4, fontFace: "Calibri" });

  tx(s, "✓ addressed  ·  ✗ not addressed  ·  — not described in the source.   Vincent [5] analyses the boundary problem but proposes no tool.",
    { x: PAD, y: 4.98, w: CW, h: 0.28, fontSize: 10.5, color: H.accent6, margin: 0 });

  card(s, PAD, 5.40, CW, 1.12, GAP_BG);
  tx(s, "We found no published system that lets a fisherman ask one question in his own language and receive a single operational decision — safety, fishing and border together — derived verifiably from official data rather than generated by a model.",
    { x: PAD + 0.32, y: 5.40, w: CW - 0.64, h: 1.12, valign: "middle", fontSize: 14.5,
      bold: true, color: GAP_INK, margin: 0 });
  s.addNotes("Every row is a study from the two survey slides. Each covers one or two columns. Thoondil and Fisher Friend come closest — safety information, fishing zones, local language — but neither answers a question, issues a verdict from fixed rules, or verifies its numbers. RAG systems answer questions, but RAGTruth shows they cannot be trusted with the numbers. Nobody has the bottom row.");
}

// ================================================================== 6 · gaps → objectives
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Research gap" });
  s.addText("Research gaps and objectives", { placeholder: "title" });
  tag(s, "GAP  →  OBJECTIVES", H.accent3);

  const hdr = ["Gap identified in the literature", "Evidence", "Objective"].map((t, i) => ({ text: t,
    options: { fontSize: 12.5, bold: true, color: "FFFFFF", fill: { color: i === 2 ? H.accent4 : H.accent3 }, valign: "middle" } }));
  const gap = (code, text) => ({ text: [
    { text: code + "  ", options: { bold: true, color: GAP_INK } },
    { text, options: { color: "2E3E4C" } }], options: { fontSize: 12.5, valign: "middle", fill: { color: GAP_BG } } });
  const ev = (t) => ({ text: t, options: { fontSize: 12, color: H.accent6, align: "center", valign: "middle" } });
  const obj = (code, text, extra) => ({ text: [
    { text: code + "  ", options: { bold: true, color: H.accent4 } },
    { text, options: { color: H.dk1 } }], options: Object.assign({ fontSize: 12.5, valign: "middle", fill: { color: "F0F8F3" } }, extra || {}) });

  const rows = [
    hdr,
    [gap("G1", "Fragmentation — weather, fishing zones and the border are separate studies and separate screens"), ev("[1]–[5]"),
      obj("O1", "Integrate all three behind one conversational interface that accepts a question", { rowspan: 2 })],
    [gap("G2", "Menu-driven apps — no system accepts a free-form question"), ev("[3] [4]")],
    [gap("G3", "Local-language content exists, but not conversation"), ev("[3] [4] [8]"),
      obj("O4", "End-to-end question answering in Indian languages, Tamil and Hindi first")],
    [gap("G4", "Retrieval grounds answers, yet hallucination persists"), ev("[6] [7]"),
      obj("O3", "Evidence ledger per observation; a verifier that deletes any unsupported number")],
    [gap("G5", "No system keeps the safety call out of the model"), ev("[6] [7]"),
      obj("O2", "Deterministic, unit-tested safety verdict, structurally outside the model")],
    [gap("G6", "Validation stops at the forecast or the zone, never the decision"), ev("[1] [2]"),
      obj("O6", "Evaluate the verdict itself with POD, FAR and CSI [10]")],
    [gap("C", "Connectivity at sea is unreliable — Thoondil ships offline maps for this reason"), ev("[3]"),
      obj("O5", "Cache → live → stale cache → snapshot, always declaring degradation")],
  ];
  s.addTable(rows, { x: PAD, y: BODY_Y, w: CW, colW: [5.1, 1.5, 5.633], rowH: 0.56,
    border: BORDER, margin: [3, 7, 3, 7], fontFace: "Calibri" });

  takeaway(s, 6.18, "O2 and O3 are the research contribution. The rest is engineering that makes them usable.");
  s.addNotes("Each gap traces to evidence on the survey slides, and each maps to one objective. G4 and G5 come straight from RAGTruth: if retrieval cannot guarantee the numbers, the model must not make the safety call, and every number must be checked mechanically.");
}

// ================================================================== 7 · method I
pres.addSection({ title: "Methodology" });
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Methodology" });
  s.addText("Methodology I — architecture and techniques", { placeholder: "title" });
  tag(s, "METHODOLOGY", H.accent4);

  const hdr = ["Step", "Technique", "Model?"].map((t, i) => ({ text: t, options: {
    fontSize: 12, bold: true, color: "FFFFFF", fill: { color: H.accent1 }, align: i === 2 ? "center" : "left", valign: "middle" } }));
  const ai = (t) => ({ text: t, options: { fontSize: 11, bold: true, color: "FFFFFF", align: "center", valign: "middle",
    fill: { color: t === "AI" ? H.accent1 : H.accent3 } } });
  const step = (n, t) => ({ text: [{ text: n + "  ", options: { bold: true, color: H.accent1 } },
    { text: t, options: { bold: true, color: H.dk1 } }], options: { fontSize: 12.5, valign: "middle" } });
  const tech = (t) => ({ text: t, options: { fontSize: 11.5, color: "2E3E4C", valign: "middle" } });
  s.addTable([
    hdr,
    [step("1", "Understand"), tech("LLM planner emits a typed task DAG (Pydantic schema, validated, one retry)"), ai("AI")],
    [step("2", "Collect"), tech("LangGraph parallel superstep: ocean & weather, geospatial & boundary, analytics. Async fetch; cache → live (2 s) → stale → snapshot"), ai("NO AI")],
    [step("3", "Decide"), tech("Deterministic rule engine: 7 parameters × 3 vessel classes; worst parameter wins, never an average; < 50 ms"), ai("NO AI")],
    [step("4", "Explain"), tech("LLM writes the answer in the user's language from a structured brief"), ai("AI")],
    [step("5", "Verify"), tech("Every number extracted (Latin and Indic digits) and matched to the ledger; unsupported → stripped and regenerated"), ai("NO AI")],
  ], { x: PAD, y: BODY_Y, w: 7.55, colW: [1.55, 5.0, 1.0], rowH: 0.62, border: BORDER, margin: [3, 6, 3, 6], fontFace: "Calibri" });

  card(s, PAD, 5.25, 7.55, 1.38);
  tx(s, [
    { text: "Evidence ledger.  ", options: { bold: true, color: H.accent1 } },
    { text: "No tool returns a bare number. Every value is an Observation — value, unit, source, valid time, fetch time, distance to the query point, confidence, note. About 130 per question, shown to the user beneath every answer.", options: { color: "2E3E4C" } },
  ], { x: PAD + 0.26, y: 5.25, w: 7.03, h: 1.38, valign: "middle", fontSize: 12.5, margin: 0, lineSpacingMultiple: 1.1 });

  s.addImage({ path: FIG("architecture.png"), x: 8.55, y: 1.14, w: 4.48, h: 5.38 });
  s.addNotes("Left: the five steps and the technique used at each. Right: the same pipeline as a diagram — blue is AI, red is no AI. The red dashed line is the design: below it there is no model at all. The ledger is what makes step 5 possible.");
}

// ================================================================== 8 · method II — dataset
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Methodology" });
  s.addText("Methodology II — dataset and tools", { placeholder: "title" });
  tag(s, "METHODOLOGY · DATASET", H.accent4);

  const OK = "✓", NO = "✗";
  const hdr = ["Source", "Variables used", "Format", "Access", "Status"].map((t) => ({ text: t, options: {
    fontSize: 12, bold: true, color: "FFFFFF", fill: { color: H.accent1 }, valign: "middle" } }));
  const st = (t) => ({ text: t, options: { fontSize: 11.5, bold: true, valign: "middle",
    color: t.startsWith(OK) ? H.accent4 : H.accent3, fill: { color: t.startsWith(OK) ? "F0F8F3" : GAP_BG } } });
  const c = (t, bold) => ({ text: t, options: { fontSize: 11.5, color: bold ? H.dk1 : "2E3E4C", bold: !!bold, valign: "middle" } });
  const data = [
    ["Open-Meteo Marine", "Wave height, period, direction; swell; currents; SST", "JSON, hourly, 7 d past + 8 d ahead", "Free, no key", OK + " Live — primary"],
    ["Open-Meteo Weather", "Wind, gusts, visibility, thunderstorm code, CAPE", "JSON, hourly", "Free, no key", OK + " Live"],
    ["INCOIS PFZ (GeoServer WFS)", "Daily Potential Fishing Zone advisory lines, by sector", "GeoJSON, daily", "Open", OK + " Live"],
    ["INCOIS static layers", "14 PFZ sectors; 1,223 named landing centres", "GeoJSON", "Open", OK + " Committed"],
    ["Marine Regions (VLIZ)", "India EEZ polygon; boundary lines incl. IMBL", "GeoJSON", "Open", OK + " Committed"],
    ["NOAA CoastWatch (VIIRS)", "Chlorophyll-a", "ERDDAP grid", "Open", OK + " Live"],
    ["Copernicus Marine", "Chlorophyll-a (BGC_001_028); physics (PHY_001_024)", "NetCDF", "Free account", OK + " Account active"],
    ["IMD API", "Cyclone track, lightning, district warnings", "—", "API key", NO + " Blocked (401)"],
    ["INCOIS ERDDAP", "SST and chlorophyll archive", "NetCDF", "Open", NO + " Stale (SST ends 2011)"],
  ];
  s.addTable([hdr, ...data.map((r) => [c(r[0], true), c(r[1]), c(r[2]), c(r[3]), st(r[4])])],
    { x: PAD, y: BODY_Y, w: CW, colW: [2.65, 3.95, 2.35, 1.35, 1.933], rowH: 0.37,
      border: BORDER, margin: [2, 6, 2, 6], fontFace: "Calibri" });

  const half = (CW - 0.25) / 2;
  card(s, PAD, 5.38, half, 1.30);
  tx(s, [
    { text: "Derived datasets", options: { bold: true, color: H.accent1, breakLine: true } },
    { text: "Frozen 7-day snapshot × 5 harbours + Gulf of Mannar (offline fallback). Evaluation set: 92 days × 5 harbours of archived forecasts.", options: { color: "2E3E4C" } },
  ], { x: PAD + 0.24, y: 5.38, w: half - 0.48, h: 1.30, valign: "middle", fontSize: 12, margin: 0, lineSpacingMultiple: 1.1 });
  card(s, PAD + half + 0.25, 5.38, half, 1.30);
  tx(s, [
    { text: "Tools", options: { bold: true, color: H.accent1, breakLine: true } },
    { text: "Python 3.11 · Pydantic · LangGraph · FastAPI + SSE · httpx (async) · xarray / netCDF4 · Shapely · pytest · React + Vite + MapLibre GL · Gemini (free tier)", options: { color: "2E3E4C" } },
  ], { x: PAD + half + 0.49, y: 5.38, w: half - 0.48, h: 1.30, valign: "middle", fontSize: 12, margin: 0, lineSpacingMultiple: 1.1 });
  s.addNotes("Every source was tested live from this laptop before any code was written against it — documented in docs/data-sources.md. Be upfront about the two red rows: IMD needs an API key (a letter on college letterhead), and INCOIS's open ERDDAP archive is stale. Total cost of every source: zero.");
}

// ================================================================== 9 · evaluation
pres.addSection({ title: "Evaluation" });
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Evaluation" });
  s.addText("Evaluation method and preliminary results", { placeholder: "title" });
  tag(s, "PROGRESS");

  const MW = 4.95, CH = 2.75;              // method card width, card height
  card(s, PAD, BODY_Y, MW, CH);
  tx(s, "Method", { x: PAD + 0.26, y: BODY_Y + 0.16, w: MW - 0.5, h: 0.34, fontSize: 16, bold: true, color: H.accent1, margin: 0 });
  s.addText([
    { text: "Prediction: ", options: { bold: true } }, { text: "verdict from the forecast available the evening before.", options: { breakLine: true } },
    { text: "Truth: ", options: { bold: true } }, { text: "verdict from the same model's analysis of that morning.", options: { breakLine: true } },
    { text: "Sample: ", options: { bold: true } }, { text: "92 mornings × 5 harbours = 460, 2026 monsoon.", options: { breakLine: true } },
    { text: "Metrics: ", options: { bold: true } }, { text: "POD, FAR, CSI from the 2×2 contingency table [10].", options: {} },
  ], { x: PAD + 0.26, y: BODY_Y + 0.58, w: MW - 0.5, h: CH - 0.7, fontSize: 12.5, color: "2E3E4C", isTextBox: true,
       paraSpaceAfter: 6, lineSpacingMultiple: 1.05, valign: "top", margin: 0 });

  // Non-breaking space keeps each number on one line with its unit.
  const stats = [["93.9 %", "hit rate (POD)", "dangerous mornings that were warned, one day ahead", H.accent4],
                 ["3.1 %", "false-alarm ratio", "warnings that wasted a good day", H.accent5],
                 ["0", "misses graded GO", "both misses were graded CAUTION", H.accent1]];
  const sx = PAD + MW + 0.25, sw = (CW - MW - 0.25 - 0.4) / 3;
  stats.forEach(([n, l, d, col], i) => {
    const x = sx + i * (sw + 0.2);
    card(s, x, BODY_Y, sw, CH);
    tx(s, n, { x: x + 0.22, y: BODY_Y + 0.2, w: sw - 0.44, h: 0.8, fontSize: 36, bold: true, color: col, margin: 0, fontFace: "Cambria" });
    tx(s, l, { x: x + 0.22, y: BODY_Y + 1.08, w: sw - 0.44, h: 0.34, fontSize: 13.5, bold: true, color: H.dk1, margin: 0 });
    tx(s, d, { x: x + 0.22, y: BODY_Y + 1.46, w: sw - 0.44, h: 1.1, fontSize: 12.5, color: "3A4A58", margin: 0, valign: "top" });
  });

  const hd = (t, i) => ({ text: t, options: { fontSize: 12, bold: true, color: "FFFFFF", fill: { color: H.accent1 },
    align: i ? "center" : "left", valign: "middle" } });
  const rowOf = (r, ri) => r.map((t, i) => ({ text: t, options: { fontSize: 12.5, bold: ri === 0,
    color: ri === 0 ? H.dk1 : "2E3E4C", fill: { color: ri === 0 ? "E4F3EA" : "FFFFFF" },
    align: i ? "center" : "left", valign: "middle" } }));
  s.addTable([
    ["Forecast lead", "n", "Hit rate (POD)", "False-alarm ratio", "CSI", "3-way agreement"].map(hd),
    ...[["1 day ahead", "460", "93.9 %", "3.1 %", "91.2 %", "93.5 %"],
        ["2 days ahead", "460", "97.0 %", "17.9 %", "80.0 %", "90.2 %"],
        ["3 days ahead", "460", "90.9 %", "30.2 %", "65.2 %", "85.0 %"]].map(rowOf),
  ], { x: PAD, y: BODY_Y + CH + 0.2, w: CW, colW: [2.6, 1.2, 2.2, 2.4, 1.6, 2.233], rowH: 0.34,
       border: BORDER, margin: [2, 6, 2, 6], fontFace: "Calibri" });

  card(s, PAD, 5.78, CW, 0.5, GAP_BG);
  tx(s, "Limitation: truth is model analysis, not a buoy measurement — these figures are an upper bound on real skill.",
    { x: PAD + 0.28, y: 5.78, w: CW - 0.56, h: 0.5, valign: "middle", fontSize: 13, bold: true, color: GAP_INK, margin: 0 });
  tx(s, [
    { text: "Status: ", options: { bold: true, color: H.dk1 } },
    { text: "phases 1–4 of 6 complete · 115 unit tests · ₹0 cost.   ", options: { color: "2E3E4C" } },
    { text: "Needed: ", options: { bold: true, color: H.dk1 } },
    { text: "IMD API key (college letter) · INCOIS small-craft criteria · INCOIS/NIOT buoy data.", options: { color: "2E3E4C" } },
  ], { x: PAD, y: 6.38, w: CW, h: 0.5, fontSize: 13, margin: 0, valign: "middle" });
  s.addNotes("The professor asked last time how often we are right — this is the answer. Stress the asymmetry: the misses fell to caution, never to go. The table shows skill falling with lead time, mainly through false alarms, which is why the day-ahead verdict is the decision. State the limitation before it is asked. Close on the three needs, leading with the IMD letter.");
}

// ================================================================== 10 · references
pres.addSection({ title: "References" });
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "References" });
  s.addText("References", { placeholder: "title" });
  const LIT = [
    "P. H. Kurup, S. Abhilash, S. Mavath, V. K. Mini, N. Alamirew and M. Martin, “Validation of localised coastal wind forecasts for artisan fishers of southwestern India,” Weather, 79(7), 231–241, 2024.",
    "R. K. Sarangi, M. Jishad, R. Sharma et al., “Multiple ocean parameter-based potential fishing zone (PFZ) location generation and validation in the Western Bay of Bengal,” Environ. Monit. Assess., 196, 98, 2024.",
    "S. K. Saka, A. E. Mathew, V. Ganesh et al., “A Web-GIS and mobile-based application for a safe ocean for fishers,” Marine Technology Society Journal, 55(3), 50–57, 2021.",
    "N. J. Anabel, S. Velvizhi and D. Suvitha, “Fisher Friend Mobile Application: a decision support system for small scale fishers in India,” CSI Transactions on ICT, 6(3–4), 257–267, 2018.",
    "S. Vincent, “Palk Bay fishing problem requires Indo-Sri Lankan joint-governance,” Maritime Affairs, 16(2), 71–88, 2020.",
    "P. Lewis, E. Perez, A. Piktus et al., “Retrieval-augmented generation for knowledge-intensive NLP tasks,” NeurIPS 33, 9459–9474, 2020.",
    "C. Niu, Y. Wu, J. Zhu et al., “RAGTruth: A hallucination corpus for developing trustworthy retrieval-augmented language models,” ACL 2024, 10862–10878.",
    "J. Gala, P. A. Chitale, R. AK et al., “IndicTrans2: Towards high-quality and accessible machine translation models for all 22 scheduled Indian languages,” TMLR, 2023.",
  ];
  const METH = [
    "INCOIS, “Small Vessel Advisory and Forecast Services (SVAS),” incois.gov.in/portal/osf/SVA_overview.jsp",
    "I. T. Jolliffe and D. B. Stephenson, Forecast Verification: A Practitioner's Guide in Atmospheric Science, 2nd ed., Wiley-Blackwell, 2012.",
  ];
  const colW = (CW - 0.35) / 2;
  const item = (n, t, last) => ({ text: `[${n}]  ${t}`, options: { breakLine: !last } });
  const head = (t) => ({ text: t, options: { bold: true, color: H.accent1, fontSize: 12.5, breakLine: true } });

  s.addText([head("Literature reviewed"), ...LIT.slice(0, 5).map((t, i) => item(i + 1, t, i === 4))], {
    x: PAD, y: BODY_Y + 0.02, w: colW, h: 5.55, fontSize: 11.5, color: "2E3E4C", isTextBox: true,
    valign: "top", paraSpaceAfter: 8, lineSpacingMultiple: 1.05, margin: 0 });
  s.addText([
    ...LIT.slice(5).map((t, i) => item(i + 6, t, false)),
    { text: " ", options: { breakLine: true } },
    head("Methodology references"),
    ...METH.map((t, i) => item(i + 9, t, i === METH.length - 1)),
  ], { x: PAD + colW + 0.35, y: BODY_Y + 0.02 + 0.33, w: colW, h: 5.2, fontSize: 11.5, color: "2E3E4C",
       isTextBox: true, valign: "top", paraSpaceAfter: 8, lineSpacingMultiple: 1.05, margin: 0 });
  s.addNotes("Every reference was checked against its publisher or DOI record. Leave this slide on screen during questions.");
}

// ------------------------------------------------------------------ build
pres.writeFile({ fileName: OUT }).then(async () => {
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT, (fs.statSync(OUT).size / 1e6).toFixed(2), "MB");
});
