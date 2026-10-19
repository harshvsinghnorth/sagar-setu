# Sagar Setu — live demo script

*For showing the working chatbot to the professor. About 8 minutes, then questions.
Every question below is one click: an example button on the start screen, or an entry in the
Question bank panel.*

---

## Before the room (15 minutes before)

1. **Start both servers.** VS Code: `Terminal → Run Task → Sagar Setu: start`. Or two terminals:
   ```
   uv run uvicorn marine.api:app --port 8000
   cd web; npm run dev
   ```
   Open **http://localhost:5173**. The status dot (top left) must be **green, "model: gemini"**.
2. **Warm the cache.** Ask the first demo question once. INCOIS's fishing-zone server is often
   slow the first time (it timed out several times this month). After one answer, everything
   is cached for an hour.
3. **Open the backups in browser tabs:**
   - `docs/question_bank_results.md`: the full bank with the model (53 questions, answers recorded).
   - `docs/question_bank_offline.md`: the same bank with the network blocked.
4. **Choose the boat** in the "boat" box: leave it at *traditional (<12 m)*. Those are the
   only limits that come from the specification; the larger-boat limits are our own estimate.
5. If the wifi is bad, don't fight it. The system is built for that (see "If something
   goes wrong" below).

---

## The demo (≈ 8 minutes)

### 1 · The basic question — English (1½ min)

**Click:** *Is it safe to go out from Kochi tomorrow morning?*

**Say:** "A fisherman asks one question. The coloured card is the verdict. **It comes from a
rule engine, plain code with fixed limits, not from the AI.** The AI only writes the sentence
explaining it."

**Point at:**
- the verdict card's list of parameters, each with its limit;
- the **Evidence ledger** on the right: every number in the answer is a row there, with its
  source, the time it is for, how far the data point is, and how fresh it is;
- the line under the answer: *"all numbers verified against the ledger"*.

> If she asks how it decides, say: "worst-of. One parameter over its limit makes the whole
> verdict *do not sail*. We never average."

### 2 · The same question in Tamil (1 min)

**Click:** the Tamil example (*நாளை காலை இராமேஸ்வரத்தில் இருந்து 90 டிகிரி திசையில் 8 நாட் வேகத்தில் போகலாமா?*)

**Say:** "Same pipeline. The question is in Tamil, and the answer comes back in Tamil. The
verdict was computed in exactly the same way. Because he gave a heading and a speed, it also
checks whether that course reaches the Sri Lanka border."

**Point at:** the grey line under the answer, *"TA · safety · …"*: language detected, and
numbers verified.

### 3 · Where are the fish — and the map (1 min)

**Click:** *Where are the fish near Paradip today?*

**Say:** "The fishing zones are INCOIS's official advisory. **We use it, we don't predict
fish ourselves.** What we add is the direction and distance from his harbour."

**Point at:** the green zones on the map and the "PFZ #1 · 40 km NE"-style labels.

### 4 · The border, before he reaches it (1 min)

**Click:** *How far is the Sri Lanka border from Rameswaram if I head 90 at 8 knots?*

**Say:** "Fishermen are arrested on this line every year. The system projects his course
forward and **warns before the crossing, not after**. It says how many minutes away the line
is on this heading."

### 5 · The route (1 min)

**Click:** *What is the best route from Kochi to the fishing zone?*
(or, in the Question bank, R03, the Tamil Rameswaram route)

**Say:** "A route that stays inside Indian waters, away from the border by a safety margin,
off land, and round any patch of sea that is too rough for this boat. Then **the whole route**
goes through the same rule engine, not just the harbour."

**Point at:** the purple route and the dashed straight line. For Rameswaram, the route goes
round the Dhanushkodi spit, because the straight line crosses land.

### 6 · The question bank (1 min)

**Click:** *Question bank (53)* at the top.

**Say:** "You asked us for a question bank. These are 53 questions a fisherman would ask, in
English, Tamil, Hindi, Malayalam and mixed Hindi-English, including off-topic ones. We use it
as a **test**, not as training data. Each question records what the system should
*understand*: the place, day and boat. The answer itself changes every day with the sea.
The ticks are the last full run."

**Click one Hindi question** to show it answering live.

### 7 · The network goes down (1 min, the closing point)

**Say:** "The last thing: fishermen and demo rooms both have bad networks. If the internet
goes, it still answers, **in Tamil and Hindi too**. It uses its stored copy of the data, says
so on screen, and plans and writes the answer without the AI. In our wifi-off rehearsal it
answered 44 of the 53 questions, all correctly. The 9 it could not answer are general
explanations and off-topic questions, and it says so in the asker's language."

**Show:** the tab with `docs/question_bank_offline.md`. Only if there is time and she asks to
see it live: stop the API, start it with `FORCE_OFFLINE=1`, and ask the Tamil example. The
status line turns amber, *deterministic mode — model unreachable*, and a banner explains it.

---

## If something goes wrong

| What you see | What it means | What to do / say |
|---|---|---|
| Red dot, *server not reachable* | The API is not running | Start it (step 1 above). While it starts, use the recorded results tab. |
| Amber dot, *deterministic mode — model unreachable* | No internet to the AI, or the free daily quota is used up | **Carry on — this is the feature.** Answers come from templates; verdicts are unchanged. |
| *live data unreachable, using stored copy* | A data source is down | Point at the yellow banner above the answer: it says which data is stored. "It never hides that." |
| The first answer takes 10 s or more | The fishing-zone server is slow; the cache is cold | "First fetch of the day; the next one comes from the cache." Ask the next question. |
| It understood the wrong place or day | Planner miss | Show the grey line under the answer (what it understood), then rephrase with the harbour name. |
| *The answer was cut off* | The server stopped mid-answer | Ask again; if it repeats, restart the API. |

---

## Likely questions

**"Is the AI deciding whether it's safe?"**
No. The verdict is computed by fixed rules in plain code, in under 50 ms. The AI receives the
verdict and explains it. A second check then rejects any number in its answer that is not in
the evidence ledger.

**"Where do the limits come from?"**
The small-boat limits are the starting values in our specification: 2.5 m waves and 27 knots
of wind for *do not sail*. The limits for bigger boats are **our own estimate, not from a
source**, and the screen says so. Replacing all of them with INCOIS's official small-craft
warning criteria is pending.

**"What happens if INCOIS or the weather service is down?"**
It tries its recent cache, then a stored snapshot. Every number then carries a lower
confidence, and the answer says the data is stored. The demo above can show it.

**"How do you know the Tamil is right?"**
With the model, Gemini writes the Tamil and our checker verifies every number. Offline, the
Tamil comes from templates we wrote. **A native speaker still has to review those templates**,
and that is on our list.

**"Did you train the AI on the question bank?"**
No, on purpose. If we trained on it, we could no longer use it to test. The bank checks
understanding (place, day, boat, language) and behaviour (a verdict, verified numbers, the
right language). It does not check fixed answers, because tomorrow's sea is different.

**"What doesn't it do yet?"**
- No lightning or cyclone feed yet: the IMD key needs a college letter. The screen says
  *"not checked: lightning, cyclone"*.
- No speech input.
- The coastline is a 1:10 million map, not a navigation chart. The route says so.

---

## The numbers to remember

- **Warning check over 92 days at 5 harbours:** warned of 31 of 33 dangerous mornings
  (93.9 %), and no dangerous morning graded *go*.
- **Question bank with the model:** 53 of 53 understood and answered correctly (run of
  19 Oct 2026, median about 6 s per question).
- **Question bank with the network blocked:** 44 of 53 answered, all correct, median 0.15 s.
  The other 9 are explanations and off-topic questions, which need the model.
- **Tests:** 194 automated tests, run on every change.
