/* Build the live-demo script as a Word document from docs/demo-script.md (the one source).

   NODE_PATH=<dir containing node_modules/docx> node scripts/build_demo_doc.js
   DEMO_OUT=<path> overrides the .docx location (docs/Sagar_Setu_Demo_Script.docx).

   Renders only the markdown this file uses: headings, paragraphs, bullet and numbered lists
   (one level of nesting), block quotes, fenced code, tables, rules, **bold**, *italic*, `code`.
*/
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
  WidthType, LevelFormat, ShadingType, BorderStyle,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const SRC = path.join(ROOT, "docs", "demo-script.md");
const OUT = process.env.DEMO_OUT || path.join(ROOT, "docs", "Sagar_Setu_Demo_Script.docx");
const FONT = "Arial";
const PAGE_W = 11906, MARGIN = 1134, CONTENT_W = PAGE_W - 2 * MARGIN; // A4, 2 cm margins

function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, ...base }));
    else if (t.startsWith("`")) out.push(new TextRun({ text: t.slice(1, -1), font: "Consolas", size: 19, ...base }));
    else out.push(new TextRun({ text: t.slice(1, -1), italics: true, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}

const border = { style: BorderStyle.SINGLE, size: 4, color: "BBBBBB" };
const cellBorders = { top: border, bottom: border, left: border, right: border };

function table(rows) {
  const cells = rows.map((r) => r.replace(/^\||\|$/g, "").split("|").map((c) => c.trim()));
  const head = cells[0];
  const body = cells.slice(2); // skip the |---| separator
  const n = head.length;
  const widths = n === 3 ? [2600, 2600, CONTENT_W - 5200] : Array(n).fill(Math.floor(CONTENT_W / n));
  const mk = (row, isHead) => new TableRow({
    tableHeader: isHead,
    children: row.map((c, i) => new TableCell({
      borders: cellBorders,
      width: { size: widths[i], type: WidthType.DXA },
      shading: isHead ? { fill: "DCE8F2", type: ShadingType.CLEAR, color: "auto" } : undefined,
      margins: { top: 60, bottom: 60, left: 100, right: 100 },
      children: [new Paragraph({ children: runs(c, { size: 19, bold: isHead || undefined }) })],
    })),
  });
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: widths,
    rows: [mk(head, true), ...body.map((r) => mk(r, false))],
  });
}

function build(md) {
  const lines = md.split(/\r?\n/);
  const out = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const t = line.trim();
    if (!t) { i++; continue; }
    if (t.startsWith("```")) {
      i++;
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        out.push(new Paragraph({
          shading: { fill: "F2F2F2", type: ShadingType.CLEAR, color: "auto" },
          indent: { left: 360 },
          children: [new TextRun({ text: lines[i].trim(), font: "Consolas", size: 19 })],
        }));
        i++;
      }
      i++;
      continue;
    }
    if (t.startsWith("|")) {
      const rows = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) rows.push(lines[i++].trim());
      out.push(table(rows));
      out.push(new Paragraph({ children: [] }));
      continue;
    }
    if (t === "---") {
      out.push(new Paragraph({ border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "1F4E79", space: 1 } }, children: [] }));
      i++;
      continue;
    }
    const h = /^(#{1,3}) (.*)$/.exec(t);
    if (h) {
      const level = [HeadingLevel.TITLE, HeadingLevel.HEADING_1, HeadingLevel.HEADING_2][h[1].length - 1];
      out.push(new Paragraph({ heading: level, children: runs(h[2]) }));
      i++;
      continue;
    }
    if (t.startsWith(">")) {
      const parts = [];
      while (i < lines.length && lines[i].trim().startsWith(">")) parts.push(lines[i++].trim().replace(/^>\s?/, ""));
      out.push(new Paragraph({
        indent: { left: 400 },
        border: { left: { style: BorderStyle.SINGLE, size: 12, color: "A96400", space: 8 } },
        children: runs(parts.join(" "), { color: "5A4A2A" }),
      }));
      continue;
    }
    const li = /^(\s*)(- |\d+\. )(.*)$/.exec(line);
    if (li) {
      const level = li[1].length >= 2 ? 1 : 0;
      const numbered = /\d/.test(li[2]);
      let text = li[3];
      i++;
      // continuation lines (indented, not a new item)
      while (i < lines.length && /^\s{2,}\S/.test(lines[i]) && !/^\s*(- |\d+\. |```)/.test(lines[i])) {
        text += " " + lines[i].trim();
        i++;
      }
      out.push(new Paragraph({
        numbering: { reference: numbered ? "numbers" : "bullets", level },
        children: runs(text),
      }));
      continue;
    }
    const indented = /^\s{3,}/.test(line); // a paragraph continuing a list item
    const parts = [t];
    i++;
    while (i < lines.length && lines[i].trim() && !/^(#|>|- |\d+\. |\||```|---)/.test(lines[i].trim())) {
      parts.push(lines[i++].trim());
    }
    out.push(new Paragraph({
      spacing: { after: 120 },
      indent: indented ? { left: 540 } : undefined,
      children: runs(parts.join(" ")),
    }));
  }
  return out;
}

const doc = new Document({
  styles: {
    default: { document: { run: { font: FONT, size: 21 } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal", run: { size: 40, bold: true, color: "1F4E79", font: FONT }, paragraph: { spacing: { after: 160 } } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 30, bold: true, color: "1F4E79", font: FONT }, paragraph: { spacing: { before: 280, after: 140 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 25, bold: true, color: "2E75B6", font: FONT }, paragraph: { spacing: { before: 220, after: 100 }, outlineLevel: 1 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [
        { level: 0, format: LevelFormat.BULLET, text: "•", style: { paragraph: { indent: { left: 540, hanging: 270 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "–", style: { paragraph: { indent: { left: 1080, hanging: 270 } } } },
      ] },
      { reference: "numbers", levels: [
        { level: 0, format: LevelFormat.DECIMAL, text: "%1.", style: { paragraph: { indent: { left: 540, hanging: 360 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "–", style: { paragraph: { indent: { left: 1080, hanging: 270 } } } },
      ] },
    ],
  },
  sections: [{
    properties: { page: { size: { width: PAGE_W, height: 16838 }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } } },
    children: build(fs.readFileSync(SRC, "utf8")),
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUT, buf);
  console.log(`wrote ${OUT} (${(buf.length / 1024).toFixed(0)} KB)`);
});
