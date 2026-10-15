/* Build docs/Sagar_Setu_Project_Brief.docx — a two-page, plain-language project brief.

   NODE_PATH=<dir containing node_modules/docx> node scripts/build_brief_doc.js
   BRIEF_OUT=<path> overrides the output location.
*/
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  WidthType, AlignmentType, LevelFormat, ShadingType, BorderStyle,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const FONT = "Calibri";
const BODY = 20;               // 10 pt
const NAVY = "1F3864", INK2 = "444444";

// ------------------------------------------------------------------ helpers
function rich(s, size = BODY, color) {
  const out = [];
  s.split(/(\*\*[^*]+\*\*)/).forEach((part) => {
    if (!part) return;
    const m = part.match(/^\*\*([^*]+)\*\*$/);
    out.push(new TextRun({ text: m ? m[1] : part, font: FONT, size, bold: !!m, color }));
  });
  return out;
}
const p = (s, o = {}) => new Paragraph({ spacing: { after: 80, line: 259 }, ...o, children: rich(s) });
const h = (t) => new Paragraph({ spacing: { before: 150, after: 60 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "B8C7DA", space: 2 } },
  children: [new TextRun({ text: t, font: FONT, size: 23, bold: true, color: NAVY })] });
const bullet = (s) => new Paragraph({ numbering: { reference: "bul", level: 0 },
  spacing: { after: 40, line: 252 }, children: rich(s) });

const cell = (content, w, head, fill) => new TableCell({
  width: { size: w, type: WidthType.DXA },
  shading: head ? { type: ShadingType.CLEAR, fill: "DCE6F1", color: "auto" }
    : fill ? { type: ShadingType.CLEAR, fill, color: "auto" } : undefined,
  margins: { top: 35, bottom: 35, left: 90, right: 90 },
  children: [new Paragraph({ spacing: { after: 0 }, children: rich(content, 18) })],
});
const table = (widths, rows, fills = {}) => new Table({
  width: { size: widths.reduce((a, c) => a + c, 0), type: WidthType.DXA },
  columnWidths: widths,
  rows: rows.map((r, ri) => new TableRow({ tableHeader: ri === 0,
    children: r.map((c, ci) => cell(ri === 0 ? `**${c}**` : c, widths[ci], ri === 0, fills[`${ri},${ci}`])) })),
});

// ------------------------------------------------------------------ content
const ch = [];

ch.push(new Paragraph({ spacing: { after: 20 }, children: [
  new TextRun({ text: "Sagar Setu", font: FONT, size: 36, bold: true, color: NAVY }),
  new TextRun({ text: "   — project brief", font: FONT, size: 26, color: INK2 }),
] }));
ch.push(new Paragraph({ spacing: { after: 100 }, children: rich(
  "A safety and fishing assistant for India's small-boat fishermen  ·  Harshvardhan Singh  ·  Supervisor: Ms. Anusha Chhabra  ·  Status as of 12 October 2026", 17, "666666") }));

ch.push(h("The idea"));
ch.push(p("A fisherman types a question on his phone, in his own language — **“Is it safe to go out from Kochi tomorrow morning?”** Sagar Setu (“bridge to the sea”) answers in that same language with a clear verdict — **GO, CAUTION or DO NOT SAIL** — plus where the fish are likely to be, how far the Sri Lankan border is, and a map. Underneath every answer it shows where each number came from and how fresh it is."));

ch.push(h("Why it matters"));
ch.push(p("Millions of Indians depend on sea fishing, most on small boats with no radar. Every morning, before dawn, they decide whether to go out. A wrong call costs a day's income — or lives. Fishermen are also arrested every year for drifting across the India–Sri Lanka sea border, which is invisible at sea. The government ocean agency, **INCOIS**, already publishes the information they need: wave forecasts, boat-safety advisories and fishing-zone maps. But it is spread across three separate websites, mostly in English and as maps. Nothing lets a fisherman simply **ask a question** and get **one answer**."));

ch.push(h("How it works — and the one rule that matters"));
ch.push(p("The system works in five steps: **(1)** AI understands the question — language, place, day, boat size; **(2)** the system collects live data from government and open sources, all at once; **(3)** a fixed rule book decides if it is safe; **(4)** AI writes the answer in the fisherman's language; **(5)** a checker confirms every number in that answer really came from the collected data, and deletes anything that didn't."));
ch.push(p("**The AI never decides whether it is safe to go to sea.** That decision comes from a fixed safety table — like one a harbour master would use — checking seven things such as wave height, wind and visibility for that size of boat. **The worst reading decides; nothing is averaged.** AI is good at language but can make things up, so it is only used to understand the question and explain the answer. Anyone can check the rules; nobody can fully check an AI's judgement."));

ch.push(h("What has been done"));
ch.push(p("**Four of six planned stages are complete, and the system works end to end today.** A question in Tamil gets a full answer in about eight seconds."));
[
  "**Stage 1 — data proven.** Every data source was tested live before any code was written, and a week of real data was saved so the system **works even with no internet**.",
  "**Stage 2 — safety rule book.** Seven safety checks for three boat sizes, protected by **115 automatic tests**.",
  "**Stage 3 — the AI layer.** Understands questions, gathers data in parallel, writes answers and checks every number.",
  "**Stage 4 — the website.** Chat, live map with fishing zones and sea borders, and the evidence table under each answer.",
  "**Accuracy measured.** Over 92 days at five harbours (460 mornings) in the 2026 monsoon, the day-ahead verdict **warned 93.9 % of dangerous mornings**, with only **3.1 % false alarms**, and **never said GO on a dangerous morning**.",
  "**Research and documents.** A literature review of 8 recent, verified studies, a synopsis report, an architecture document and a presentation.",
  "**Cost so far: ₹0.** Every data source is free, the AI runs on a free tier, and it runs on a laptop.",
].forEach((t) => ch.push(bullet(t)));

ch.push(h("The data used"));
ch.push(table([2600, 4900, 2240], [
  ["Source", "What it tells us", "Status"],
  ["Open-Meteo (marine + weather)", "Waves, swell, currents, wind, gusts, visibility, storms", "Working — main source"],
  ["INCOIS fishing-zone advisories", "Where fish are likely to be today, by coastal sector", "Working"],
  ["INCOIS map layers", "14 coastal sectors and 1,223 named fishing harbours", "Working, saved locally"],
  ["Marine Regions", "India's sea area and the India–Sri Lanka border line", "Working, saved locally"],
  ["NOAA and Copernicus", "Plankton levels (a clue to where fish gather)", "Working"],
  ["IMD (weather department)", "Cyclones and lightning", "Blocked — needs an access key"],
], { "6,2": "FBEDEB", "1,2": "EAF5EE", "2,2": "EAF5EE", "3,2": "EAF5EE", "4,2": "EAF5EE", "5,2": "EAF5EE" }));

ch.push(h("Tech stack"));
ch.push(table([2600, 7140], [
  ["Part", "Tools used"],
  ["Core language", "Python 3.11 (back end), TypeScript (website)"],
  ["AI", "Google Gemini (free tier) — swappable for a local model or none at all; LangGraph to coordinate the AI steps"],
  ["Data handling", "Pydantic (checks every data shape), httpx (fast parallel downloads), xarray / netCDF4 (ocean data), Shapely (border and map geometry)"],
  ["Server", "FastAPI, streaming answers word by word as they are written"],
  ["Website and map", "React + Vite, MapLibre GL with free OpenStreetMap maps — no paid map service"],
  ["Quality", "pytest (115 tests), ruff (code checking), uv (package management), Git + GitHub"],
]));

ch.push(h("Future objectives"));
ch.push(p("**Next stages (5 and 6):**"));
[
  "**Official Indian-language translation** through the government's Bhashini service (IndicTrans2 as backup) — Tamil already works through Gemini.",
  "**Safest-route suggestion** drawn on the map, avoiding rough water and the border.",
  "**Follow-up questions** such as “what about tomorrow instead?” without repeating everything.",
  "**Explaining changes**, e.g. why catches have fallen in an area.",
  "**Hardening and rehearsal** — offline mode, clear error messages, testing at all five harbours, and practising the demo with Wi-Fi off.",
].forEach((t) => ch.push(bullet(t)));
ch.push(p("**Improvements that need outside help:**", { spacing: { before: 60, after: 40 } }));
[
  "**IMD access key** — needs a letter on college letterhead. Switches on cyclone and lightning checks (2 of the 7 are currently inactive).",
  "**INCOIS's official boat-safety limits** — to replace the current starting values with sourced numbers, and add the two factors INCOIS uses that we don't yet: wave **spread** and boat **width**.",
  "**Buoy measurements** from INCOIS or NIOT — so accuracy is tested against the real sea, not just against a weather model.",
].forEach((t) => ch.push(bullet(t)));

ch.push(h("Honest limitations"));
ch.push(p("The safety limits are sensible starting values, not yet official ones. The 93.9 % figure compares forecasts against a weather model's own record of what happened, not physical buoys, so it is a best case. And the main wave data comes from Open-Meteo, a European service, because INCOIS's public data archive is out of date. Each of these is fixable with the help listed above."));

// ------------------------------------------------------------------ build
const doc = new Document({
  styles: { default: { document: { run: { font: FONT, size: BODY } } } },
  numbering: { config: [{ reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
    alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 340, hanging: 200 } } } }] }] },
  sections: [{ properties: { page: { margin: { top: 760, bottom: 720, left: 900, right: 900 } } }, children: ch }],
});

Packer.toBuffer(doc).then((buf) => {
  const out = process.env.BRIEF_OUT || path.join(ROOT, "docs", "Sagar_Setu_Project_Brief.docx");
  fs.writeFileSync(out, buf);
  console.log("wrote", out, (buf.length / 1e3).toFixed(0), "KB");
});
