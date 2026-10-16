import { useMemo, useState } from "react";
import type { BankQuestion, QuestionBank as Bank } from "../api";

const LANG: Record<string, string> = { en: "EN", ta: "தமிழ்", hi: "हिन्दी", ml: "മലയാളം" };

/** The fisherman question bank as a clickable demo panel, grouped by question type. */
export default function QuestionBank({
  bank,
  onAsk,
  onClose,
  disabled,
}: {
  bank: Bank;
  onAsk: (q: string) => void;
  onClose: () => void;
  disabled: boolean;
}) {
  const cats = Object.keys(bank.categories);
  const [cat, setCat] = useState<string>("all");
  const shown = useMemo(
    () => bank.questions.filter((q) => cat === "all" || q.category === cat),
    [bank, cat],
  );
  const count = (c: string) => bank.questions.filter((q) => q.category === c).length;

  return (
    <div className="bank">
      <div className="bank-head">
        <div>
          <b>Question bank</b> <span className="muted">· {bank.questions.length} questions fishermen ask</span>
          {bank.summary && (
            <div className="muted bank-score">
              last scored run: understood {bank.summary.understood} · answers behaved {bank.summary.behaved}
            </div>
          )}
        </div>
        <button className="bank-close" onClick={onClose} aria-label="Close question bank">×</button>
      </div>
      <div className="bank-cats">
        <button className={cat === "all" ? "on" : ""} onClick={() => setCat("all")}>All</button>
        {cats.map((c) => (
          <button key={c} className={cat === c ? "on" : ""} onClick={() => setCat(c)}>
            {bank.categories[c]} <span className="muted">{count(c)}</span>
          </button>
        ))}
      </div>
      <div className="bank-list">
        {shown.map((q) => (
          <Item key={q.id} q={q} onAsk={onAsk} disabled={disabled} />
        ))}
      </div>
    </div>
  );
}

function Item({ q, onAsk, disabled }: { q: BankQuestion; onAsk: (q: string) => void; disabled: boolean }) {
  const r = q.last_run;
  const mark = !r ? null : r.understood && r.behaved ? "ok" : r.understood ? "warn" : "miss";
  return (
    <button className="bank-q" onClick={() => onAsk(q.q)} disabled={disabled} lang={q.lang}>
      <span className="bank-tags">
        <span className="bank-id">{q.id}</span>
        <span className="bank-lang">{LANG[q.lang] ?? q.lang}</span>
        {q.style !== "plain" && <span className="bank-style">{q.style}</span>}
        {mark && <span className={`bank-mark ${mark}`} title="result of the last scored run">{mark === "ok" ? "✓" : mark === "warn" ? "!" : "✗"}</span>}
      </span>
      <span className="bank-text">{q.q}</span>
      {q.en && <span className="bank-en muted">{q.en}</span>}
    </button>
  );
}
