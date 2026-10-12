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
    fontSize: 12, bold: true, color: "FFFFFF", fill: { color: i === 4 ? H.accent3 : H.accent1 },
    valign: "middle" } }));
  const body = rows.map((r) => r.map((t, i) => {
    if (i === 0) {
      const [who, where] = t.split("|");
      return { text: [
        { text: who, options: { bold: true, color: H.dk1, fontSize: 12, breakLine: true } },
        { text: where, options: { color: H.accent6, fontSize: 10.5 } },
      ], options: { valign: "middle" } };
    }
    return { text: t, options: {
      fontSize: 11.5, color: i === 4 ? GAP_INK : "2E3E4C",
      fill: { color: i === 4 ? GAP_BG : "FFFFFF" }, valign: "middle" } };
  }));
  slide.addTable([hdr, ...body], { x: PAD, y: BODY_Y, w: CW, colW, rowH: 0.36,
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
  s.addText("Literature survey I — Indian marine information services", { placeholder: "title" });
  tag(s, "LITERATURE 1 / 3");
  survey(s, [
    ["Nair et al., 2013|Current Science [1]",
     "Validated INCOIS's operational Ocean State Forecast",
     "Forecast wave height vs wave-rider buoys, ship-borne wave meters, satellite altimeters",
     "Scatter index < 15 %; r = 0.98, RMSE 0.35 m at Gopalpur (Cyclone Phailin)",
     "Validates the forecast field, not any decision; reports RMSE, not verdict skill"],
    ["INCOIS SVAS|INCOIS portal [2], [3]",
     "Boat-specific overturning advisory, ten days ahead",
     "Boat Safety Index from wave height, steepness, directional spread, wind-sea growth; beam < 4 / 6 / 7 m",
     "Steepness and beam govern capsizing — not wave height alone",
     "Colour-coded map, English only; thresholds unpublished; separate from fishing zones and borders"],
    ["Pillai & Nair, 2010|Biological Forum [4]",
     "Validated PFZ advisories on the Kerala coast, 2006–2010",
     "Active fishers' catch data plus controlled experiments inside and outside notified zones",
     "CPUE higher inside zones: ~2–6× catch, ~2–7× monetary benefit",
     "Regional, institute-affiliated evidence; advisory is a bulletin, not interactive"],
    ["MSSRF Fisher Friend;|INCOIS dissemination [5]",
     "Getting advisories to fishermen",
     "Mobile app in 9 languages, multilingual SMS, 24×7 helpline, ~30 km offshore mobile pilot",
     "Language reach achieved; offshore connectivity remains the constraint",
     "Broadcast only — no channel accepts a question about a specific boat, place and time"],
  ]);
  takeaway(s, 6.18, "India's marine data is validated and excellent. What no product does is reason across all three and answer a question.", GAP_BG, GAP_INK);
  s.addNotes("Read the last column. Each row's limitation becomes a gap on slide 6. SVAS is the closest product to our safety half: it independently confirms wave steepness and vessel size matter — but it is a map, not a conversation.");
}

// ================================================================== 4 · lit II
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Literature survey" });
  s.addText("Literature survey II — forecasting and AI reasoning techniques", { placeholder: "title" });
  tag(s, "LITERATURE 2 / 3");
  survey(s, [
    ["Lam et al., 2023|Science [6]  ·  GraphCast",
     "Machine-learned global medium-range weather forecasting",
     "Graph neural network trained on decades of ERA5 reanalysis",
     "Outperforms operational numerical prediction on most headline scores",
     "Needs decades of reanalysis and heavy compute; produces fields, not decisions"],
    ["Bi et al., 2023|Nature [7]  ·  Pangu-Weather",
     "Machine-learned global medium-range weather forecasting",
     "3D Earth-specific transformer trained on ERA5 reanalysis",
     "Accuracy comparable to operational numerical prediction",
     "Would replace a forecast INCOIS already provides, validated and free"],
    ["Lewis et al., 2020|NeurIPS [10]  ·  RAG",
     "Retrieval-augmented generation",
     "Sequence-to-sequence generator combined with a dense retriever over Wikipedia",
     "Grounding in retrieved passages improves factual question answering",
     "Grounds in text; does not guarantee every generated claim is supported"],
    ["Yao et al., 2023|ICLR [8]  ·  ReAct",
     "Interleaving reasoning with tool actions",
     "Prompted LLM alternating thoughts and API / environment actions",
     "External tool access reduces hallucination compared with reasoning alone",
     "Tool use is prompted, not enforced; the model still writes the final answer"],
    ["Schick et al., 2023|NeurIPS [9]  ·  Toolformer",
     "Models that learn when to call APIs",
     "Self-supervised; calculator, QA, search, translation, calendar tools",
     "Learns useful tool calls with little human annotation",
     "The model decides when to call a tool and whether to trust it"],
  ]);
  takeaway(s, 6.18, "Training a forecaster is the road not taken. Tool-using agents make this approach possible — but none enforces that the answer comes from the tools.", GAP_BG, GAP_INK);
  s.addNotes("Two halves. GraphCast and Pangu are here as the road deliberately not taken: competing with INCOIS's validated forecast needs data and compute a student project does not have. RAG, ReAct and Toolformer are the techniques that make the system possible — and their shared limitation is that grounding is encouraged, not enforced.");
}

// ================================================================== 5 · lit III
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Literature survey" });
  s.addText("Literature survey III — LLM decision support, reliability, evaluation", { placeholder: "title" });
  tag(s, "LITERATURE 3 / 3");
  survey(s, [
    ["Kuznetsov et al., 2025|npj Climate Action [11]  ·  ClimSight",
     "LLM climate-service platform",
     "Agent routing + retrieval over climate models and reports; XCLIM-AI adds deterministic indicator computation",
     "Largest gains when indicators are computed deterministically, not generated",
     "Analytical questions for planners; the model writes the conclusion; English"],
    ["Xie et al., 2025|arXiv [12]  ·  WildfireGPT",
     "Multi-agent hazard decision support",
     "Retrieval over hazard projections, observations and literature; ten expert case studies",
     "Outperforms existing LLM tools in expert-led evaluation",
     "Document-level grounding; no operational go / no-go; no per-number provenance"],
    ["Lin et al., 2025|arXiv [13]",
     "Survey of hallucination in LLM agents",
     "Taxonomy across five workflow stages; eighteen triggering causes",
     "Agent errors can be “physically consequential” and cascade",
     "Prompting cannot guarantee faithfulness — verification must be mechanical"],
    ["Gala et al., 2023|TMLR [14]  ·  IndicTrans2",
     "Open translation for all 22 scheduled languages",
     "BPCC corpus of 230 M bitext pairs; IN22 benchmark",
     "First model to cover all 22 languages",
     "Translation is solved; no conversational marine system uses it"],
    ["Jolliffe & Stephenson, 2012|Wiley [15]",
     "Forecast verification methodology",
     "2×2 contingency table: POD, FAR, CSI",
     "Misses and false alarms must be scored separately",
     "Applied to forecast fields — never to safety verdicts in this domain"],
  ]);
  takeaway(s, 6.18, "The closest systems still let the model conclude. ClimSight's own finding points the other way — we take it to its end.", GAP_BG, GAP_INK);
  s.addNotes("ClimSight is the single strongest support for the design: its own extension reports the biggest gains when indicators are computed deterministically. Lin et al. is why the verifier exists — prompting a model to be careful is not a guarantee.");
}

// ================================================================== 6 · gap matrix
pres.addSection({ title: "Research gap" });
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Research gap" });
  s.addText("Research gap — comparative analysis", { placeholder: "title" });
  tag(s, "RESEARCH GAP", H.accent3);

  const head = ["System", "Conver-\nsational", "Indian\nlanguages", "Live numeric\ndata", "Deterministic\nsafety verdict", "Per-number\nprovenance", "Safety + fish\n+ border", "Verdict-level\nevaluation"];
  const Y = "✓", N = "✗";
  const body = [
    ["INCOIS Ocean State Forecast [1]", N, "partial", Y, "n/a", N, N, "RMSE only"],
    ["INCOIS Small Vessel Advisory [2]", N, N, Y, Y, N, N, N],
    ["INCOIS Potential Fishing Zone [4]", N, Y + " (10)", Y, "n/a", N, N, "catch-based"],
    ["Fisher Friend app [5]", N, Y + " (9)", Y, N, N, "partial", N],
    ["ClimSight [11]", Y, N, "partial", N, "document", N, N],
    ["WildfireGPT [12]", Y, N, "partial", N, "document", N, "case studies"],
  ];
  const base = { fontSize: 12, color: "2E3E4C", align: "center", valign: "middle" };
  const rows = [
    head.map((t, i) => ({ text: t, options: { fontSize: 11, bold: true, color: "FFFFFF",
      fill: { color: H.accent1 }, align: i ? "center" : "left", valign: "middle" } })),
    ...body.map((r) => r.map((t, i) => ({ text: t, options: Object.assign({}, base,
      i ? {} : { align: "left", color: H.dk1 },
      t === Y ? { color: H.accent4, bold: true } : {},
      t === N ? { color: "B4C0C8" } : {}) }))),
    ["Sagar Setu (proposed)", Y, Y, Y, Y, Y, Y, "POD / FAR / CSI"].map((t, i) => ({ text: t,
      options: { fontSize: 12, bold: true, color: i ? H.accent4 : "FFFFFF",
        fill: { color: i ? "E4F3EA" : H.dk2 }, align: i ? "center" : "left", valign: "middle" } })),
  ];
  s.addTable(rows, { x: PAD, y: BODY_Y, w: CW, colW: [2.95, 1.17, 1.32, 1.36, 1.5, 1.36, 1.27, 1.303],
    rowH: 0.42, border: BORDER, margin: 4, fontFace: "Calibri" });

  card(s, PAD, 5.22, CW, 1.12, GAP_BG);
  tx(s, "No published system lets a fisherman ask one question in his own language and receive a single operational decision — safety, fishing and border together — that is provably derived from official products rather than generated by a model.",
    { x: PAD + 0.32, y: 5.22, w: CW - 0.64, h: 1.12, valign: "middle", fontSize: 14.5,
      bold: true, color: GAP_INK, margin: 0 });
  s.addNotes("Every row of this table is a study from the three survey slides. Walk it row by row. The SVAS row is the only one with a deterministic verdict — but it fails every other column. ClimSight and WildfireGPT are conversational, but they ground in documents and let the model conclude. Nobody has the bottom row.");
}

// ================================================================== 7 · gaps → objectives
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
    [gap("G1", "Fragmentation — safety, fish and borders are three separate products"), ev("[2] [4] [5]"),
      obj("O1", "Integrate all three behind one conversational interface that accepts a question", { rowspan: 2 })],
    [gap("G2", "Broadcast only — no channel accepts a question"), ev("[5]")],
    [gap("G3", "Language reach is translated output, not dialogue"), ev("[5] [14]"),
      obj("O4", "End-to-end question answering in Indian languages, Tamil and Hindi first")],
    [gap("G4", "Grounding is document-level; hallucination remains unsolved"), ev("[11] [12] [13]"),
      obj("O3", "Evidence ledger per observation; a verifier that deletes any unsupported number")],
    [gap("G5", "No architecture keeps the safety decision out of the model"), ev("[11] [8] [9]"),
      obj("O2", "Deterministic, unit-tested safety verdict, structurally outside the model")],
    [gap("G6", "Evaluation stops at forecast RMSE, never the verdict"), ev("[1] [15]"),
      obj("O6", "Evaluate the verdict itself with POD, FAR and CSI")],
    [gap("C", "Offshore connectivity is unreliable (operational constraint)"), ev("[5]"),
      obj("O5", "Cache → live → stale cache → snapshot, always declaring degradation")],
  ];
  s.addTable(rows, { x: PAD, y: BODY_Y, w: CW, colW: [5.1, 1.5, 5.633], rowH: 0.56,
    border: BORDER, margin: [3, 7, 3, 7], fontFace: "Calibri" });

  takeaway(s, 6.18, "O2 and O3 are the research contribution. The rest is engineering that makes them usable.");
  s.addNotes("Each gap traces to evidence on the survey slides, and each maps to one objective. O2 and O3 are the novel part — keep the safety decision out of the model, and make unsupported numbers impossible rather than unlikely.");
}

// ================================================================== 8 · method I
pres.addSection({ title: "Methodology" });
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Methodology" });
  s.addText("Proposed methodology I — architecture and techniques", { placeholder: "title" });
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

// ================================================================== 9 · method II — dataset
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Methodology" });
  s.addText("Proposed methodology II — dataset and tools", { placeholder: "title" });
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

// ================================================================== 10 · evaluation
pres.addSection({ title: "Evaluation" });
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Evaluation" });
  s.addText("Evaluation method and preliminary results", { placeholder: "title" });
  tag(s, "PROGRESS");

  card(s, PAD, BODY_Y, 5.6, 3.55);
  tx(s, "Method", { x: PAD + 0.28, y: BODY_Y + 0.18, w: 5.0, h: 0.34, fontSize: 16, bold: true, color: H.accent1, margin: 0 });
  s.addText([
    { text: "Prediction: ", options: { bold: true } }, { text: "verdict from the forecast available the evening before.", options: { breakLine: true } },
    { text: "Truth: ", options: { bold: true } }, { text: "verdict from the same model's analysis of that morning.", options: { breakLine: true } },
    { text: "Sample: ", options: { bold: true } }, { text: "92 mornings × 5 harbours = 460, 2026 south-west monsoon.", options: { breakLine: true } },
    { text: "Metrics: ", options: { bold: true } }, { text: "POD, FAR, CSI from the 2×2 contingency table [15].", options: {} },
  ], { x: PAD + 0.28, y: BODY_Y + 0.62, w: 5.05, h: 2.75, fontSize: 13, color: "2E3E4C", isTextBox: true,
       paraSpaceAfter: 9, lineSpacingMultiple: 1.1, valign: "top", margin: 0 });

  const stats = [["93.9 %", "hit rate (POD)", "dangerous mornings that were warned", H.accent4],
                 ["3.1 %", "false-alarm ratio", "warnings that wasted a good day", H.accent5],
                 ["0", "misses graded GO", "both misses were graded CAUTION", H.accent1]];
  const sx = PAD + 5.85, sw = (CW - 5.85 - 0.4) / 3;
  stats.forEach(([n, l, d, col], i) => {
    const x = sx + i * (sw + 0.2);
    card(s, x, BODY_Y, sw, 3.55);
    tx(s, n, { x: x + 0.22, y: BODY_Y + 0.35, w: sw - 0.44, h: 0.95, fontSize: 40, bold: true, color: col, margin: 0, fontFace: "Cambria" });
    tx(s, l, { x: x + 0.22, y: BODY_Y + 1.42, w: sw - 0.44, h: 0.36, fontSize: 13.5, bold: true, color: H.dk1, margin: 0 });
    tx(s, d, { x: x + 0.22, y: BODY_Y + 1.84, w: sw - 0.44, h: 0.9, fontSize: 12.5, color: "3A4A58", margin: 0, valign: "top" });
  });
  tx(s, "Day-ahead “do not sail” verdict. Skill falls with lead time, mainly through false alarms (3-day FAR 30.2 %).",
    { x: sx, y: BODY_Y + 3.62, w: CW - 5.85, h: 0.36, fontSize: 11, color: H.accent6, margin: 0 });

  card(s, PAD, 5.38, CW, 0.62, GAP_BG);
  tx(s, "Limitation: truth is model analysis, not a buoy measurement — these figures are an upper bound on real skill.",
    { x: PAD + 0.28, y: 5.38, w: CW - 0.56, h: 0.62, valign: "middle", fontSize: 13, bold: true, color: GAP_INK, margin: 0 });
  tx(s, [
    { text: "Status: ", options: { bold: true, color: H.dk1 } },
    { text: "phases 1–4 of 6 complete · 115 unit tests · ₹0 cost.   ", options: { color: "2E3E4C" } },
    { text: "Needed: ", options: { bold: true, color: H.dk1 } },
    { text: "IMD API key (college letter) · INCOIS small-craft criteria · INCOIS/NIOT buoy data.", options: { color: "2E3E4C" } },
  ], { x: PAD, y: 6.20, w: CW, h: 0.55, fontSize: 13, margin: 0, valign: "middle" });
  s.addNotes("The professor asked last time how often we are right — this is the answer. Stress the asymmetry: the misses fell to caution, never to go. State the limitation before it is asked. Close on the three needs, leading with the IMD letter.");
}

// ================================================================== 11 · references
pres.addSection({ title: "References" });
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "References" });
  s.addText("References", { placeholder: "title" });
  const refs = [
    "B. T. M. Nair et al., “Performance of the ocean state forecast system at INCOIS,” Current Science, 105(2), 175–181, 2013.",
    "INCOIS, “Small Vessel Advisory and Forecast Services (SVAS),” incois.gov.in/portal/osf/SVA_overview.jsp",
    "A. N. Deshmukh, “Small Craft Advisory,” ITCOocean training material, INCOIS, Hyderabad.",
    "V. N. Pillai and P. G. Nair, “Potential fishing zone (PFZ) advisories — are they beneficial to the coastal fisherfolk? A case study along Kerala coast,” Biological Forum, 2(2), 46–55, 2010.",
    "M. S. Swaminathan Research Foundation, “Fisher Friend Mobile Application”; INCOIS multilingual dissemination services.",
    "R. Lam et al., “Learning skillful medium-range global weather forecasting,” Science, 382(6677), 1416–1421, 2023.",
    "K. Bi et al., “Accurate medium-range global weather forecasting with 3D neural networks,” Nature, 619, 533–538, 2023.",
    "S. Yao et al., “ReAct: Synergizing reasoning and acting in language models,” ICLR, 2023.",
    "T. Schick et al., “Toolformer: Language models can teach themselves to use tools,” NeurIPS 36, 2023.",
    "P. Lewis et al., “Retrieval-augmented generation for knowledge-intensive NLP tasks,” NeurIPS 33, 9459–9474, 2020.",
    "I. Kuznetsov et al., “Transforming climate services with LLMs and multi-source data integration,” npj Climate Action, 4, 97, 2025.",
    "Y. Xie et al., “A RAG-based multi-agent LLM system for natural hazard resilience and adaptation,” arXiv:2504.17200, 2025.",
    "X. Lin et al., “LLM-based agents suffer from hallucinations: a survey of taxonomy, methods, and directions,” arXiv:2509.18970, 2025.",
    "J. Gala et al., “IndicTrans2: Towards high-quality and accessible machine translation models for all 22 scheduled Indian languages,” TMLR, 2023.",
    "I. T. Jolliffe and D. B. Stephenson, Forecast Verification: A Practitioner's Guide in Atmospheric Science, 2nd ed., Wiley-Blackwell, 2012.",
  ];
  const col = (list, start, x) => s.addText(list.map((r, i) => ({ text: [`[${start + i}]  `, r].join(""),
    options: { breakLine: i < list.length - 1 } })), {
    x, y: BODY_Y + 0.02, w: (CW - 0.35) / 2, h: 5.55, fontSize: 11, color: "2E3E4C", isTextBox: true,
    valign: "top", paraSpaceAfter: 7, lineSpacingMultiple: 1.05, margin: 0 });
  col(refs.slice(0, 8), 1, PAD);
  col(refs.slice(8), 9, PAD + (CW - 0.35) / 2 + 0.35);
  s.addNotes("Every reference was checked against its publisher or repository record.");
}

// ------------------------------------------------------------------ build
pres.writeFile({ fileName: OUT }).then(async () => {
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT, (fs.statSync(OUT).size / 1e6).toFixed(2), "MB");
});
