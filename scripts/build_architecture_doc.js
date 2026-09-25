/* Build docs/Sagar_Setu_Architecture.docx — the architecture submission.
   Kept deliberately short and plain. Run scripts/plot_architecture_simple.py first.

   NODE_PATH=<dir containing node_modules/docx> node scripts/build_architecture_doc.js
*/
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
  WidthType, AlignmentType, LevelFormat, ShadingType, ImageRun, PageBreak,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const FONT = "Calibri";
const PAGE_W = 605; // px at 96 dpi ≈ 6.3" of usable width

const p = (runs, opts = {}) =>
  new Paragraph({
    spacing: { after: 140, line: 288 },
    ...opts,
    children: (Array.isArray(runs) ? runs : [runs]).map((t) =>
      typeof t === "string" ? new TextRun({ text: t, font: FONT, size: 22 }) : t),
  });
const b = (t) => new TextRun({ text: t, font: FONT, size: 22, bold: true });
const mono = (t) => new TextRun({ text: t, font: "Consolas", size: 19 });
const h1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 320, after: 150 }, children: [new TextRun({ text: t, font: FONT })] });
const bullet = (runs) => new Paragraph({
  numbering: { reference: "bullets", level: 0 }, spacing: { after: 110, line: 288 },
  children: (Array.isArray(runs) ? runs : [runs]).map((t) =>
    typeof t === "string" ? new TextRun({ text: t, font: FONT, size: 22 }) : t),
});

const cell = (content, w, head) =>
  new TableCell({
    width: { size: w, type: WidthType.DXA },
    shading: head ? { type: ShadingType.CLEAR, fill: "DCE6F1", color: "auto" } : undefined,
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({
      spacing: { after: 0 },
      children: (Array.isArray(content) ? content : [content]).map((r) =>
        typeof r === "string" ? new TextRun({ text: r, font: FONT, size: 20, bold: !!head }) : r),
    })],
  });

const table = (widths, rows) =>
  new Table({
    width: { size: widths.reduce((a, c) => a + c, 0), type: WidthType.DXA },
    columnWidths: widths,
    rows: rows.map((r, ri) => new TableRow({ tableHeader: ri === 0, children: r.map((c, ci) => cell(c, widths[ci], ri === 0)) })),
  });

function image(file, widthPx) {
  const data = fs.readFileSync(path.join(ROOT, "docs", "architecture", file));
  const w = data.readUInt32BE(16), hgt = data.readUInt32BE(20);
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 140, after: 100 },
    children: [new ImageRun({ type: "png", data, transformation: { width: widthPx, height: Math.round((widthPx * hgt) / w) } })],
  });
}
const caption = (t) => new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { after: 240 },
  children: [new TextRun({ text: t, font: FONT, size: 18, italics: true, color: "555555" })],
});

const children = [];

// ---------------------------------------------------------------- title
children.push(
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 70 }, children: [new TextRun({ text: "Sagar Setu — Proposed System Architecture", font: FONT, size: 34, bold: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 }, children: [new TextRun({ text: "Marine decision support for Indian small-craft fishermen", font: FONT, size: 24 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 }, children: [new TextRun({ text: "ISRO / INCOIS problem statement · Smart India Hackathon 2026", font: FONT, size: 21, color: "555555" })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 280 }, children: [new TextRun({ text: "Harshvardhan Singh · September 2026", font: FONT, size: 21, color: "555555" })] }),
);

// ---------------------------------------------------------------- 1
children.push(h1("1.  What the system does"));
children.push(p("A fisherman types a question in his own language — “Is it safe to go out from Kochi tomorrow morning?”, “Where are the fish today?”, “How far is the Sri Lanka border on this heading?” — and gets an answer in that same language, with a map, and with the source of every number shown underneath."));
children.push(p([b("The system does not predict the weather itself."), " It collects official forecasts and fishing-zone advisories, applies a fixed safety table to them, and uses AI only to understand the question and to explain the result in plain words."]));

// ---------------------------------------------------------------- 2
children.push(h1("2.  The main idea"));
children.push(p("Three rules shape the whole design:"));
children.push(bullet([b("AI never decides whether it is safe to go to sea. "), "The decision comes from a fixed safety table — the kind of table a harbour master would use. AI sits outside that decision, before it and after it."]));
children.push(bullet([b("No number is shown unless it was recorded first. "), "Every value the system collects goes into an evidence ledger, along with where it came from and how old it is. A checking step removes any number in the answer that is not in the ledger."]));
children.push(bullet([b("The system always answers, and always says how good its data is. "), "If a source is slow or down, it falls back to a stored copy — and tells the fisherman that is what it did."]));

// ---------------------------------------------------------------- diagram
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h1("3.  The architecture"));
children.push(image("architecture.png", PAGE_W));
children.push(caption("Figure 1 — the main components and how they connect."));

// ---------------------------------------------------------------- 4
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h1("4.  The parts of the system"));
children.push(table([2900, 6126], [
  ["Component", "What it does"],
  ["Web page", "Where the fisherman types the question and sees the answer, the map and the evidence table"],
  ["Server", "Connects the web page to everything else, and sends the answer back a few words at a time so it appears as it is written"],
  [[b("1. Understanding "), "(AI)"], "Works out the language, the place, the day and time, and the size of the boat — then decides what needs to be looked up"],
  [[b("2. Collectors "), "(three, at the same time)"], "One fetches sea conditions, one checks maps and borders, one looks at fish and plankton data. They run together, not one after another"],
  [[b("Evidence ledger")], "The record of every number collected: its value, where it came from, what time it is for, how fresh it is, and how much it can be trusted"],
  [[b("3. Safety rules "), "(no AI)"], "Checks seven things — wave height, wind, visibility and so on — against a published safety table for that size of boat. The worst one decides the answer"],
  [[b("4. Answer writer "), "(AI)"], "Turns the decision into a few plain sentences in the fisherman's own language"],
  [[b("5. Checker "), "(no AI)"], "Reads the answer and throws out any number that is not in the ledger. If it finds one, the answer is written again"],
  ["Data sources", "INCOIS (fishing zones), Open-Meteo (waves and wind), Copernicus and NOAA (plankton), Marine Regions (sea borders). IMD's cyclone and lightning data is pending an access key"],
]));

// ---------------------------------------------------------------- 5
children.push(h1("5.  How the parts work together"));
children.push(p("The question travels down through the parts in order; the answer comes back up. The collectors run at the same time as each other rather than one after another, which is what keeps the system fast. Below is a real question, measured."));
children.push(image("flow.png", PAGE_W));
children.push(caption("Figure 2 — one Tamil question, measured end to end on 22 September 2026."));
children.push(p([b("Eight seconds in all."), " The two AI steps take almost all of it. The safety decision itself takes a ten-thousandth of a second, because it is only a table lookup. An English question is faster, about four seconds, because step 1 does not need AI. With AI switched off completely, the system still answers in English in under half a second."]));

// ---------------------------------------------------------------- 6
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h1("6.  Why it is built this way"));
children.push(table([3400, 5626], [
  ["Choice", "Reason"],
  ["The safety decision uses fixed rules, not AI", "Anyone can read the table and check the answer. A wrong answer here could cost a life, and there is no dataset of “boats that did and did not come back” to train such a model on anyway"],
  ["The worst reading decides, never an average", "Averaging is how a system tells someone to go out under a thunderstorm because the waves happened to be calm"],
  ["Every number is recorded before it is used", "This makes it impossible for the AI to invent a number, rather than merely unlikely — the checker removes anything that is not in the ledger"],
  ["We use INCOIS's fishing zones rather than predicting our own", "INCOIS has twenty years of validation against real catch data. Our contribution is reasoning over their advisory, not replacing it"],
  ["A stored copy of the data is kept in the system", "The system must still give a complete, honest answer when the network is down — and say that is what it is doing"],
]));

// ---------------------------------------------------------------- 7
children.push(h1("7.  What runs where"));
children.push(p("Two programs on one computer:"));
children.push(new Paragraph({ spacing: { after: 0 }, children: [mono("uv run uvicorn marine.api:app --reload       # the server and all the logic")] }));
children.push(new Paragraph({ spacing: { after: 160 }, children: [mono("cd web && npm run dev                        # the web page")] }));
children.push(p("Everything is free: every data source, the AI service (free tier), and the hosting, which is a laptop. The sea borders and a week of stored data are kept inside the project, so a fresh copy works without an internet connection."));
children.push(p([b("Built so far: "), "all five parts above are working, with 115 automatic tests. Code and a more detailed technical diagram are at github.com/harshvsinghnorth/sagar-setu."], { spacing: { before: 200 } }));

// ---------------------------------------------------------------- build
const doc = new Document({
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 28, bold: true, color: "1F3864", font: FONT }, paragraph: { spacing: { before: 320, after: 150 }, outlineLevel: 0 } },
    ],
  },
  numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [{ properties: { page: { margin: { top: 1160, bottom: 1160, left: 1160, right: 1160 } } }, children }],
});

Packer.toBuffer(doc).then((buf) => {
  const out = process.env.ARCH_DOC_OUT || path.join(ROOT, "docs", "Sagar_Setu_Architecture.docx");
  fs.writeFileSync(out, buf);
  console.log("wrote", out, (buf.length / 1e6).toFixed(2), "MB");
});
