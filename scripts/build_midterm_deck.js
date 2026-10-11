/* Build docs/Sagar_Setu_MidTerm.pptx — the mid-term review deck.
   Content mirrors docs/synopsis.md; edit both together.

   NODE_PATH=<dir containing node_modules> node scripts/build_midterm_deck.js
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
    accent1: "065A82", accent2: "1C7293", accent3: "C0392B",
    accent4: "1B8A5A", accent5: "D98324", accent6: "6B7C8C",
    hlink: "1C7293", folHlink: "6B7C8C",
  },
};
const H = THEME.colors;                 // hex, for fills and anything hex-only

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";            // 13.333 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.author = "Harshvardhan Singh";
pres.title = "Sagar Setu — Mid-Term Review";
const C = pres.SchemeColor;

const W = 13.333, PAD = 0.62, CW = W - 2 * PAD;   // content width 12.093
const BODY_Y = 1.42, BODY_H = 5.35;

// ------------------------------------------------------------------ layouts
pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: H.dk2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: PAD, y: 2.28, w: CW, h: 1.3,
        fontSize: 54, bold: true, color: C.background1, align: "left", valign: "bottom" }, text: " " } },
    { placeholder: { options: { name: "body", type: "body", x: PAD, y: 3.72, w: 9.6, h: 1.1,
        fontSize: 19, color: "BDD2E2", align: "left", valign: "top" }, text: " " } },
  ],
});

pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: C.background1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: PAD, y: 0.40, w: CW, h: 0.80,
        fontSize: 32, bold: true, color: C.text1, align: "left", valign: "middle" }, text: " " } },
    { text: { text: "Sagar Setu  ·  Mid-term review  ·  13 October 2026",
        options: { x: PAD, y: 6.96, w: 8, h: 0.3, fontSize: 9, color: C.accent6, isTextBox: true } } },
  ],
  slideNumber: { x: 12.55, y: 6.96, w: 0.5, h: 0.3, fontSize: 9, color: H.accent6, align: "right" },
});

pres.defineSlideMaster({
  title: "CLOSE_DARK",
  background: { color: H.dk2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: PAD, y: 0.40, w: CW, h: 0.80,
        fontSize: 32, bold: true, color: C.background1, align: "left", valign: "middle" }, text: " " } },
  ],
});

// ------------------------------------------------------------------ helpers
const tx = (slide, text, o) => slide.addText(text, Object.assign({ isTextBox: true }, o));

/** A content card: tinted panel, no edge stripes. */
function card(slide, x, y, w, h, fill) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.09, fill: { color: fill || H.lt2 }, line: { color: fill || H.lt2 },
  });
}

/** The repeated motif: a filled circle carrying a number or short label. */
function dot(slide, x, y, d, label, fill, size) {
  slide.addShape(pres.ShapeType.ellipse, {
    x, y, w: d, h: d, fill: { color: fill }, line: { color: fill },
  });
  tx(slide, label, {
    x, y, w: d, h: d, align: "center", valign: "middle",
    fontSize: size || 14, bold: true, color: "FFFFFF", margin: 0,
  });
}

const S = {
  h: { fontSize: 17, bold: true, color: H.dk1, isTextBox: true, margin: 0 },
  p: { fontSize: 13.5, color: "3A4A58", isTextBox: true, margin: 0, lineSpacingMultiple: 1.16 },
  cap: { fontSize: 10.5, color: H.accent6, isTextBox: true, margin: 0 },
};

// ------------------------------------------------------------------ 1 · title
pres.addSection({ title: "Opening" });
{
  const s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Opening" });
  s.addText("SAGAR SETU", { placeholder: "title", charSpacing: 3 });
  s.addText("An agentic, evidence-grounded marine advisory system\nfor Indian small-craft fishermen",
    { placeholder: "body" });

  // motif: the three verdicts this system exists to produce
  const verdicts = [["GO", H.accent4], ["CAUTION", H.accent5], ["DO NOT SAIL", H.accent3]];
  let vx = PAD;
  verdicts.forEach(([t, c]) => {
    const w = 0.22 + t.length * 0.105;
    s.addShape(pres.ShapeType.roundRect, { x: vx, y: 5.30, w, h: 0.40, rectRadius: 0.2,
      fill: { color: c }, line: { color: c } });
    tx(s, t, { x: vx, y: 5.30, w, h: 0.40, align: "center", valign: "middle",
      fontSize: 11, bold: true, color: "FFFFFF", margin: 0 });
    vx += w + 0.18;
  });

  tx(s, "Harshvardhan Singh   ·   Supervisor: Ms. Anusha Chhabra   ·   13 October 2026",
    { x: PAD, y: 6.42, w: CW, h: 0.3, fontSize: 13, color: "BDD2E2" });
  tx(s, "ISRO / INCOIS agentic marine intelligence problem statement  ·  Smart India Hackathon 2026",
    { x: PAD, y: 6.76, w: CW, h: 0.3, fontSize: 10.5, color: "7E9AB3" });
  s.addNotes("Sagar Setu means 'bridge to the sea'. One sentence: it lets a fisherman ask, in his own language, whether it is safe to go out — and it answers from official government data, with the safety decision made by fixed rules, not by the AI.");
}

// ------------------------------------------------------------------ 2 · problem
pres.addSection({ title: "Problem" });
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Problem" });
  s.addText("One decision, made in the dark", { placeholder: "title" });

  tx(s, "A small-craft fisherman makes one decision a day, before dawn, before the boat leaves: go, or stay. Wrong in one direction it costs a day's income. Wrong in the other it can cost the boat and the crew.",
    Object.assign({}, S.p, { x: PAD, y: BODY_Y, w: 6.55, h: 1.25, fontSize: 15 }));

  const qs = [
    ["Is it safe?", "Waves, wind, lightning, cyclone — against this boat's size", H.accent3],
    ["Where are the fish?", "A full hold, or a wasted tank of diesel", H.accent2],
    ["Where is the border?", "Detention by the Sri Lankan Navy is an annual event in the Palk Bay", H.accent5],
  ];
  let y = 2.92;
  qs.forEach(([q, sub, col]) => {
    dot(s, PAD, y + 0.03, 0.34, "?", col, 13);
    tx(s, q, Object.assign({}, S.h, { x: PAD + 0.52, y, w: 6.0, h: 0.3, fontSize: 15 }));
    tx(s, sub, Object.assign({}, S.p, { x: PAD + 0.52, y: y + 0.32, w: 6.0, h: 0.5, fontSize: 12 }));
    y += 1.06;
  });

  // stat cards
  const stats = [["4 million", "people depend on marine fishing in India"],
                 ["3", "separate government products hold the answers"],
                 ["0", "of them accept a question"]];
  let sy = BODY_Y;
  stats.forEach(([n, l], idx) => {
    card(s, 7.55, sy, 5.16, 1.60, idx === 2 ? "FBE9E7" : H.lt2);
    tx(s, n, { x: 7.85, y: sy + 0.16, w: 4.6, h: 0.78, fontSize: 40, bold: true,
      color: idx === 2 ? H.accent3 : H.accent1, isTextBox: true, margin: 0, fontFace: "Cambria" });
    tx(s, l, Object.assign({}, S.p, { x: 7.85, y: sy + 0.98, w: 4.6, h: 0.45, fontSize: 12.5 }));
    sy += 1.80;
  });
  s.addNotes("The data exists. The gap is the last two hundred metres — between a government web portal and a man on a beach at four in the morning with a cheap Android phone.");
}

// ------------------------------------------------------------------ 3 · literature A
pres.addSection({ title: "Literature" });
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Literature" });
  s.addText("What India already publishes", { placeholder: "title" });

  const items = [
    ["1", "INCOIS Ocean State Forecast", "Waves, wind, currents, SST for the Indian Ocean.",
     "Validated against buoys, ship-borne wave meters and altimeters — scatter index below 15 %.", "Nair et al., 2013 [1]", H.accent1],
    ["2", "INCOIS Small Vessel Advisory", "Boat-specific capsizing risk, ten days ahead.",
     "Boat Safety Index from wave height, steepness, directional spread; beam classes < 4 / 6 / 7 m.", "INCOIS SVAS [2]", H.accent2],
    ["3", "INCOIS Potential Fishing Zone", "Satellite-derived fishing advisories, 12 sectors.",
     "Catch per unit effort and profit measurably higher inside notified zones.", "Pillai & Nair, 2010 [4]", H.accent4],
  ];
  const cw = 3.84, gap = 0.30;
  items.forEach(([n, title, lead, detail, cite, col], idx) => {
    const x = PAD + idx * (cw + gap);
    card(s, x, BODY_Y, cw, 4.02);
    dot(s, x + 0.30, BODY_Y + 0.28, 0.42, n, col);
    tx(s, title, Object.assign({}, S.h, { x: x + 0.30, y: BODY_Y + 0.86, w: cw - 0.6, h: 0.72, fontSize: 15.5 }));
    tx(s, lead, Object.assign({}, S.p, { x: x + 0.30, y: BODY_Y + 1.62, w: cw - 0.6, h: 0.55, fontSize: 13, bold: true, color: H.dk1 }));
    tx(s, detail, Object.assign({}, S.p, { x: x + 0.30, y: BODY_Y + 2.22, w: cw - 0.6, h: 1.15, fontSize: 12.5 }));
    tx(s, cite, Object.assign({}, S.cap, { x: x + 0.30, y: BODY_Y + 3.52, w: cw - 0.6, h: 0.3 }));
  });

  card(s, PAD, 5.72, CW, 0.78, "FBE9E7");
  tx(s, [{ text: "All three are maps and bulletins. ", options: { bold: false } },
         { text: "None of them answers a question", options: { bold: true } },
         { text: " — and none of them knows about the other two.", options: { bold: false } }],
    { x: PAD + 0.32, y: 5.72, w: CW - 0.64, h: 0.78, valign: "middle", fontSize: 15,
      color: H.accent3, isTextBox: true, margin: 0 });
  s.addNotes("This is the point to stress: India's data is excellent. We are not fixing the data. We are fixing the interface to it.");
}

// ------------------------------------------------------------------ 4 · literature B
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Literature" });
  s.addText("What the AI literature says", { placeholder: "title" });

  const colW = 5.88;
  card(s, PAD, BODY_Y, colW, 3.85);
  dot(s, PAD + 0.32, BODY_Y + 0.26, 0.38, "✓", H.accent4, 15);
  tx(s, "Grounding a model in tools works", Object.assign({}, S.h, { x: PAD + 0.84, y: BODY_Y + 0.30, w: colW - 1.2, h: 0.35 }));
  s.addText([
    { text: "ReAct [8] and Toolformer [9] — the model plans and calls tools instead of recalling facts.", options: { bullet: true, breakLine: true } },
    { text: "Retrieval-augmented generation [10] — ground the answer in retrieved evidence.", options: { bullet: true, breakLine: true } },
    { text: "ClimSight [11] and WildfireGPT [12] — multi-agent advisory systems for climate and wildfire.", options: { bullet: true, breakLine: true } },
    { text: "ClimSight's XCLIM-AI extension reports its largest gains when indicators are computed deterministically rather than generated.", options: { bullet: true } },
  ], { x: PAD + 0.32, y: BODY_Y + 0.82, w: colW - 0.64, h: 2.85, fontSize: 13, color: "3A4A58",
       isTextBox: true, paraSpaceAfter: 9, lineSpacingMultiple: 1.1 });

  const x2 = PAD + colW + 0.32;
  card(s, x2, BODY_Y, colW, 3.85, "FBE9E7");
  dot(s, x2 + 0.32, BODY_Y + 0.26, 0.38, "!", H.accent3, 15);
  tx(s, "But grounding is not proof", Object.assign({}, S.h, { x: x2 + 0.84, y: BODY_Y + 0.30, w: colW - 1.2, h: 0.35 }));
  s.addText([
    { text: "Lin et al. [13] survey hallucination in LLM agents: five failure types, eighteen causes.", options: { bullet: true, breakLine: true } },
    { text: "They warn that agent errors can be “physically consequential” and cascade down a chain.", options: { bullet: true, breakLine: true } },
    { text: "Tool bypass — the model simulates a tool's output instead of calling it — defeats auditing exactly when auditing matters.", options: { bullet: true, breakLine: true } },
    { text: "Both systems above ground in documents, answer analytical questions, and still let the model write the conclusion.", options: { bullet: true } },
  ], { x: x2 + 0.32, y: BODY_Y + 0.82, w: colW - 0.64, h: 2.85, fontSize: 13, color: "3A4A58",
       isTextBox: true, paraSpaceAfter: 9, lineSpacingMultiple: 1.1 });

  tx(s, "Which is why “only use the data provided” is treated in this work as insufficient. An unsupported number must be removed mechanically, not discouraged.",
    { x: PAD, y: 5.56, w: CW, h: 0.9, fontSize: 15, italics: true, color: H.accent1, isTextBox: true, margin: 0 });
  s.addNotes("If she asks why not just prompt the model to be careful: because the literature says prompting is not a guarantee, and we are making a safety claim.");
}

// ------------------------------------------------------------------ 5 · the gap
pres.addSection({ title: "Gap" });
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Gap" });
  s.addText("The gap", { placeholder: "title" });

  const head = ["System", "Conver-\nsational", "Indian\nlanguages", "Deterministic\nsafety verdict", "Per-number\nprovenance", "All three\ndomains"];
  const body = [
    ["INCOIS Ocean State Forecast [1]", "✗", "partial", "n/a", "✗", "✗"],
    ["INCOIS Small Vessel Advisory [2]", "✗", "✗", "✓", "✗", "✗"],
    ["INCOIS Potential Fishing Zone [4]", "✗", "✓  (10)", "n/a", "✗", "✗"],
    ["Fisher Friend app [5]", "✗", "✓  (9)", "✗", "✗", "partial"],
    ["ClimSight [11]", "✓", "✗", "✗", "document", "✗"],
    ["WildfireGPT [12]", "✓", "✗", "✗", "document", "✗"],
  ];
  const cellBase = { fontSize: 12, color: "2E3E4C", align: "center", valign: "middle" };
  const rows = [
    head.map((t, i) => ({ text: t, options: { fontSize: 11.5, bold: true, color: "FFFFFF",
      fill: { color: H.accent1 }, align: i ? "center" : "left", valign: "middle" } })),
    ...body.map((r) => r.map((t, i) => ({ text: t,
      options: Object.assign({}, cellBase, i ? {} : { align: "left", color: H.dk1 },
        t === "✓" ? { color: H.accent4, bold: true } : {},
        t === "✗" ? { color: "B9C4CC" } : {}) }))),
    ["Sagar Setu (proposed)", "✓", "✓", "✓", "✓", "✓"].map((t, i) => ({ text: t,
      options: { fontSize: 12.5, bold: true, color: i ? H.accent4 : "FFFFFF",
        fill: { color: i ? "E4F3EA" : H.dk2 }, align: i ? "center" : "left", valign: "middle" } })),
  ];
  s.addTable(rows, {
    x: PAD, y: BODY_Y, w: CW, colW: [3.30, 1.62, 1.72, 2.10, 1.88, 1.473],
    rowH: 0.385, border: { type: "solid", pt: 0.6, color: "D8E0E6" },
    margin: 5, fontFace: "Calibri",
  });

  card(s, PAD, 5.02, CW, 1.08, H.lt2);
  tx(s, "No published system lets a fisherman ask one question in his own language and receive a single operational decision — safety, fishing and boundary together — that is provably derived from official products rather than generated by a model.",
    { x: PAD + 0.34, y: 5.02, w: CW - 0.68, h: 1.08, valign: "middle", fontSize: 14.5,
      bold: true, color: H.dk1, isTextBox: true, margin: 0 });
  s.addNotes("This table is the research gap. Read down the last row. Six specific gaps are enumerated in the synopsis: fragmentation, interaction mode, language depth, verifiability, structural safety separation, and evaluation at the level of action.");
}

// ------------------------------------------------------------------ 6 · objectives
pres.addSection({ title: "Objectives" });
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Objectives" });
  s.addText("Objectives", { placeholder: "title" });

  const objs = [
    ["O1", "Integrate", "Safety, fishing zones and boundaries behind one conversational interface."],
    ["O2", "Separate", "The safety verdict produced by deterministic, unit-tested rules — structurally outside the model's reach."],
    ["O3", "Prove", "An evidence ledger per observation, and a verifier that deletes any number absent from it."],
    ["O4", "Translate", "End-to-end question answering in Indian languages, starting with Tamil and Hindi."],
    ["O5", "Degrade honestly", "Cache → live → stale cache → snapshot, always declaring which one answered."],
    ["O6", "Evaluate", "At the level the user acts on — the verdict — with POD, FAR and CSI."],
  ];
  const cw = 5.88, chh = 1.54;
  objs.forEach(([n, title, text], idx) => {
    const x = PAD + (idx % 2) * (cw + 0.32);
    const y = BODY_Y + Math.floor(idx / 2) * (chh + 0.22);
    card(s, x, y, cw, chh);
    dot(s, x + 0.30, y + 0.30, 0.46, n, idx % 2 ? H.accent2 : H.accent1, 13);
    tx(s, title, Object.assign({}, S.h, { x: x + 0.92, y: y + 0.28, w: cw - 1.24, h: 0.34, fontSize: 16 }));
    tx(s, text, Object.assign({}, S.p, { x: x + 0.92, y: y + 0.66, w: cw - 1.24, h: 0.82, fontSize: 12.5 }));
  });
  s.addNotes("O2 and O3 are the research contribution. The rest is good engineering.");
}

// ------------------------------------------------------------------ 7 · architecture
pres.addSection({ title: "Method" });
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Method" });
  s.addText("Architecture", { placeholder: "title" });

  const pts = [
    ["AI", "Understand and explain", "The model reads the question and writes the answer. Those are language tasks, and it is good at them.", H.accent1],
    ["NO AI", "Decide", "Seven checks against a threshold table for that vessel class. Pure Python, 115 unit tests, under 50 ms.", H.accent3],
    ["NO AI", "Check", "Every number in the drafted answer is traced back to the ledger. Anything unsupported is removed and the answer rewritten.", H.accent3],
  ];
  let y = BODY_Y + 0.05;
  pts.forEach(([badge, title, text, col]) => {
    s.addShape(pres.ShapeType.roundRect, { x: PAD, y, w: 0.92, h: 0.34, rectRadius: 0.17,
      fill: { color: col }, line: { color: col } });
    tx(s, badge, { x: PAD, y, w: 0.92, h: 0.34, align: "center", valign: "middle",
      fontSize: 10, bold: true, color: "FFFFFF", margin: 0 });
    tx(s, title, Object.assign({}, S.h, { x: PAD + 1.10, y: y - 0.02, w: 5.3, h: 0.36, fontSize: 17 }));
    tx(s, text, Object.assign({}, S.p, { x: PAD, y: y + 0.44, w: 6.3, h: 0.95, fontSize: 13 }));
    y += 1.62;
  });

  card(s, PAD, 6.00, 6.3, 0.72, "FBE9E7");
  tx(s, "The model never computes, adjusts or softens the verdict.",
    { x: PAD + 0.28, y: 6.00, w: 5.74, h: 0.72, valign: "middle", fontSize: 13.5, bold: true,
      color: H.accent3, isTextBox: true, margin: 0 });

  s.addImage({ path: FIG("architecture.png"), x: 7.70, y: 1.16, w: 4.62, h: 5.55 });
  s.addNotes("Walk down the figure. Blue is AI, red is no AI. The red dashed line is the design constraint: below it there is no model at all.");
}

// ------------------------------------------------------------------ 8 · the rule
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Method" });
  s.addText("The rule that shapes everything", { placeholder: "title" });

  tx(s, "The worst parameter decides. Never an average.",
    { x: PAD, y: BODY_Y - 0.08, w: CW, h: 0.52, fontSize: 26, bold: true, color: H.accent3,
      isTextBox: true, margin: 0, fontFace: "Cambria" });
  tx(s, "Averaging across six parameters is how a system sends a boat out under a thunderhead because the waves happened to be calm.",
    Object.assign({}, S.p, { x: PAD, y: BODY_Y + 0.50, w: 8.6, h: 0.44, fontSize: 14 }));

  const hdr = ["Parameter", "GO", "CAUTION", "DO NOT SAIL"];
  const data = [
    ["Significant wave height", "< 1.5 m", "1.5 – 2.5 m", "> 2.5 m"],
    ["Sustained wind", "< 19 kt", "19 – 27 kt", "> 27 kt"],
    ["Sea steepness (Hs/T²)", "low", "short-period swell", "breaking-sea regime"],
    ["Lightning proximity", "none < 50 km", "50 – 100 km closing", "any strike < 50 km"],
    ["Cyclone cone of uncertainty", "no intersect", "intersect 72 – 120 h", "intersect < 48 h"],
    ["Visibility", "> 5 km", "2 – 5 km", "< 2 km"],
  ];
  const hcol = [H.accent1, H.accent4, H.accent5, H.accent3];
  s.addTable([
    hdr.map((t, i) => ({ text: t, options: { fontSize: 12, bold: true, color: "FFFFFF",
      fill: { color: hcol[i] }, align: i ? "center" : "left", valign: "middle" } })),
    ...data.map((r) => r.map((t, i) => ({ text: t, options: { fontSize: 12.5,
      color: i ? "2E3E4C" : H.dk1, bold: !i, align: i ? "center" : "left", valign: "middle" } }))),
  ], { x: PAD, y: BODY_Y + 1.12, w: 8.6, colW: [3.05, 1.70, 1.95, 1.90], rowH: 0.40,
       border: { type: "solid", pt: 0.6, color: "D8E0E6" }, margin: 5, fontFace: "Calibri" });

  card(s, 9.52, BODY_Y + 1.12, 3.21, 1.42, "FBE9E7");
  tx(s, "Missing wave or wind data can never produce a GO.",
    { x: 9.80, y: BODY_Y + 1.12, w: 2.65, h: 1.42, valign: "middle", fontSize: 14, bold: true,
      color: H.accent3, isTextBox: true, margin: 0 });

  card(s, 9.52, BODY_Y + 2.72, 3.21, 1.22);
  tx(s, "Three vessel classes, separate tables: traditional < 12 m, motorised 12–20 m, mechanised > 20 m.",
    Object.assign({}, S.p, { x: 9.80, y: BODY_Y + 2.72, w: 2.65, h: 1.22, valign: "middle", fontSize: 12.5 }));

  tx(s, "Provisional values. INCOIS's Boat Safety Index independently selects steepness, directional spread and beam width — calibrating against its published criteria is identified, outstanding work.",
    Object.assign({}, S.cap, { x: PAD, y: 5.72, w: CW, h: 0.4, fontSize: 11 }));
  s.addNotes("Honest caveat she may probe: these thresholds are starting values, not yet calibrated to an official published document. We say so rather than implying authority we do not have.");
}

// ------------------------------------------------------------------ 9 · results
pres.addSection({ title: "Results" });
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  s.addText("How often is it right?", { placeholder: "title" });

  tx(s, "Day-ahead “do not sail” verdict, 92 mornings × 5 harbours = 460 harbour-mornings, 2026 south-west monsoon",
    Object.assign({}, S.p, { x: PAD, y: BODY_Y - 0.10, w: CW, h: 0.34, fontSize: 13.5 }));

  const big = [["93.9 %", "of dangerous mornings were warned", "hit rate (POD)", H.accent4],
               ["3.1 %", "of warnings wasted a good day", "false-alarm ratio (FAR)", H.accent5]];
  big.forEach(([n, l, sub, col], idx) => {
    const x = PAD + idx * 3.30;
    card(s, x, BODY_Y + 0.34, 3.06, 1.96);
    tx(s, n, { x: x + 0.26, y: BODY_Y + 0.50, w: 2.6, h: 0.82, fontSize: 42, bold: true,
      color: col, isTextBox: true, margin: 0, fontFace: "Cambria" });
    tx(s, l, Object.assign({}, S.p, { x: x + 0.26, y: BODY_Y + 1.34, w: 2.6, h: 0.56, fontSize: 12.5 }));
    tx(s, sub, Object.assign({}, S.cap, { x: x + 0.26, y: BODY_Y + 1.92, w: 2.6, h: 0.28 }));
  });

  card(s, PAD + 6.60, BODY_Y + 0.34, 5.49, 1.96, "E4F3EA");
  tx(s, "Both misses were graded CAUTION.\nNo dangerous morning was ever graded GO.",
    { x: PAD + 6.90, y: BODY_Y + 0.34, w: 4.9, h: 1.96, valign: "middle", fontSize: 16,
      bold: true, color: "14633F", isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });

  s.addTable([
    ["Forecast lead", "n", "Hit rate (POD)", "False-alarm ratio", "CSI", "3-way agreement"].map((t, i) =>
      ({ text: t, options: { fontSize: 12, bold: true, color: "FFFFFF", fill: { color: H.accent1 },
        align: i ? "center" : "left", valign: "middle" } })),
    ...[["1 day ahead", "460", "93.9 %", "3.1 %", "91.2 %", "93.5 %"],
        ["2 days ahead", "460", "97.0 %", "17.9 %", "80.0 %", "90.2 %"],
        ["3 days ahead", "460", "90.9 %", "30.2 %", "65.2 %", "85.0 %"]].map((r, ri) =>
      r.map((t, i) => ({ text: t, options: { fontSize: 12.5, bold: ri === 0,
        color: ri === 0 ? H.dk1 : "2E3E4C", fill: { color: ri === 0 ? "E4F3EA" : "FFFFFF" },
        align: i ? "center" : "left", valign: "middle" } }))),
  ], { x: PAD, y: BODY_Y + 2.56, w: CW, colW: [2.60, 1.30, 2.30, 2.40, 1.70, 1.793], rowH: 0.40,
       border: { type: "solid", pt: 0.6, color: "D8E0E6" }, margin: 5, fontFace: "Calibri" });

  tx(s, "Honest limit: truth here is the same wave model's final analysis, not a buoy measurement — no public INCOIS or NIOT buoy feed is available to us. These are therefore an upper bound on skill. The harness runs unchanged against buoy data the moment access is obtained.",
    Object.assign({}, S.cap, { x: PAD, y: 6.26, w: CW, h: 0.58, fontSize: 11.5 }));
  s.addNotes("This is the slide the professor asked for after the last review: a number for how often we are right. Note the asymmetry — misses fall to CAUTION, never GO, which is what the worst-of rule is designed to produce. And state the limitation before she finds it.");
}

// ------------------------------------------------------------------ 10 · status
pres.addSection({ title: "Status" });
{
  const s = pres.addSlide({ masterName: "CLOSE_DARK", sectionTitle: "Status" });
  s.addText("Where we are, and what we need", { placeholder: "title" });

  const done = [["Phase 1", "Data sources verified, a week of real data frozen for offline demo"],
                ["Phase 2", "Typed tool belt and deterministic risk engine — 115 unit tests"],
                ["Phase 3", "LangGraph agent system: planner, parallel specialists, verifier"],
                ["Phase 4", "FastAPI + SSE backend, React + MapLibre interface with the ledger visible"]];
  tx(s, "Complete", { x: PAD, y: BODY_Y, w: 6.0, h: 0.34, fontSize: 17, bold: true, color: "FFFFFF", isTextBox: true, margin: 0 });
  let y = BODY_Y + 0.46;
  done.forEach(([ph, text]) => {
    dot(s, PAD, y, 0.27, "✓", H.accent4, 12);
    tx(s, ph, { x: PAD + 0.44, y, w: 1.3, h: 0.30, fontSize: 12.5, bold: true, color: "9FD8BC",
      isTextBox: true, margin: 0, valign: "top" });
    tx(s, text, { x: PAD + 1.62, y, w: 4.5, h: 0.62, fontSize: 12.5, color: "D3E0EB",
      isTextBox: true, margin: 0, valign: "top", lineSpacingMultiple: 1.1 });
    y += 0.86;
  });
  tx(s, "Phases 5 and 6 — Bhashini translation, route optimisation, offline hardening — remain.",
    { x: PAD, y: y + 0.08, w: 6.1, h: 0.5, fontSize: 12.5, italics: true, color: "9FB3C4", isTextBox: true, margin: 0 });

  const asks = [["IMD API key", "Needs a letter on college letterhead. Unlocks lightning and cyclone parameters — two of the seven checks are inactive without it."],
                ["INCOIS threshold criteria", "The published small-craft numbers behind the Boat Safety Index, to replace our provisional table."],
                ["Buoy observations", "INCOIS or NIOT data would turn the evaluation from model-against-model into model-against-the-sea."]];
  const x2 = 7.10;
  tx(s, "What would make this materially better", { x: x2, y: BODY_Y, w: 5.6, h: 0.34, fontSize: 17, bold: true, color: "FFFFFF", isTextBox: true, margin: 0 });
  let y2 = BODY_Y + 0.46;
  asks.forEach(([t, d], idx) => {
    s.addShape(pres.ShapeType.roundRect, { x: x2, y: y2, w: 5.62, h: 1.26, rectRadius: 0.09,
      fill: { color: "1E3E5C" }, line: { color: "1E3E5C" } });
    dot(s, x2 + 0.26, y2 + 0.24, 0.32, String(idx + 1), H.accent5, 12);
    tx(s, t, { x: x2 + 0.70, y: y2 + 0.20, w: 4.7, h: 0.32, fontSize: 14, bold: true, color: "FFD9A8", isTextBox: true, margin: 0 });
    tx(s, d, { x: x2 + 0.70, y: y2 + 0.56, w: 4.7, h: 0.62, fontSize: 11.5, color: "C8D8E6", isTextBox: true, margin: 0, lineSpacingMultiple: 1.1 });
    y2 += 1.40;
  });

  tx(s, "Total external cost of the project to date: ₹0.", { x: PAD, y: 6.72, w: 6.0, h: 0.3,
    fontSize: 12, italics: true, color: "7E9AB3", isTextBox: true, margin: 0 });
  s.addNotes("Close on the three asks. These are not excuses — each one is a specific thing the department can help with that measurably improves the project.");
}

// ------------------------------------------------------------------ build
pres.writeFile({ fileName: OUT }).then(async () => {
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT, (fs.statSync(OUT).size / 1e6).toFixed(2), "MB");
});
