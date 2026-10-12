# Sagar Setu — mid-term presentation script

*13 October 2026 · 11 slides (10 + references) · about 13 minutes, plus questions.*

Bold text is what to stress. Quoted blocks are stage directions, not words to say.

---

## Before you start

- Open the deck in Presenter View — every slide has speaker notes that condense this script.
- Have the web interface already running with a Tamil question already answered in a second tab, in case she asks to see it. Do not start it cold in the room.
- Have the synopsis open at Section 2.11, the comparison table — the page she is most likely to ask about.
- On the three literature slides, do not read the tables. Read the study name, one finding, then the red column. The red column is the point.
- Print this script. Read it twice tonight, then speak from the bold lines.

## If you remember four things

1. The talk follows the marking scheme: problem → literature survey → research gap → objectives → methodology.
2. The gap comes out of the literature: every survey row ends in a red “limitation for our problem”, and those limitations become G1–G6.
3. The AI never decides safety. ClimSight's own finding — deterministic computation beats generation — supports that design.
4. 93.9 % hit rate, 3.1 % false alarms, no dangerous morning ever graded “go”. Then the asks — lead with the IMD letter.

---

## Slide 1 — Title

**0:30**

Good afternoon. My project is **Sagar Setu** — “bridge to the sea” — a decision-support system for India's small-craft fishermen.

In one sentence: **a fisherman asks a question in his own language and gets back a safety decision built from official government data — where the AI explains the decision but never makes it.**

I will follow the review structure: the problem, the literature survey, the research gap and objectives, and the proposed methodology.

> *Do not read the subtitle. Let the three coloured pills sit on screen while you say the one-sentence version.*

**Bridge to slide 2:** “Let me start with the problem.”

---

## Slide 2 — Introduction and problem definition

**1:15**

Context on the left. About **four million people** depend on marine fishing in India, most on boats under twelve metres — no radar, little signal offshore.

Every morning, before dawn, they make one decision: **go, or stay**. And three questions arrive together — is it safe, where are the fish, where is the border.

India already publishes the answer to each. But in three separate products, as maps and bulletins.

So my problem statement, on the right: **given a free-form question in an Indian language, produce one trustworthy operational answer — safety, fishing and border together — derived verifiably from official data, fast enough to use before the boat leaves, and honest when sources fail.**

And one constraint that shapes everything: **the language model must never be the component that decides whether it is safe to go to sea.**

> *Read the red constraint box slowly. Every design decision in the methodology traces back to it.*

**Bridge to slide 3:** “To see what already exists, I surveyed the literature in three groups.”

---

## Slide 3 — Literature survey I — Indian marine information services

**1:45**

The first group is India's own marine information services. Each row reads left to right — the study, what it did, its method and data, the finding, and in red, **its limitation for my problem**.

**Nair et al., 2013, in Current Science**, validated INCOIS's Ocean State Forecast against wave-rider buoys, ship-borne meters and satellite altimeters — scatter index under fifteen percent. An excellent forecast. But it validates the forecast field, not any decision.

**INCOIS's Small Vessel Advisory** is the closest product to my safety work. It computes a Boat Safety Index from wave height, steepness, directional spread and wind-sea growth, per boat width. It independently confirms that steepness and vessel size matter. But it is a colour map, in English, its thresholds are not published, and it knows nothing about fishing zones or borders.

**Pillai and Nair, 2010**, validated the fishing-zone advisories on the Kerala coast from 2006 to 2010 — roughly two to six times the catch inside the zones. A real benefit. But it is a bulletin.

And dissemination — the **Fisher Friend app**, INCOIS's SMS and helplines — reaches nine languages, but it is broadcast. None of it accepts a question.

**So India's marine data is validated and excellent. What no product does is reason across all three and answer a question.**

> *Do not read every cell. For each row: bold study name, one finding, then point at the red column. The Small Vessel Advisory row deserves the most time — it is the strongest item in the review.*

**Bridge to slide 4:** “The second group is the techniques I could build with.”

---

## Slide 4 — Literature survey II — forecasting and AI reasoning techniques

**1:15**

Two halves. **GraphCast and Pangu-Weather** — Science and Nature, 2023 — are machine-learned forecasting models that now rival operational prediction. They are in my review as **the road not taken**: they need decades of reanalysis and heavy compute, and they would replace a forecast INCOIS already provides, validated and free.

The other three make my system possible. **Retrieval-augmented generation** grounds answers in retrieved evidence. **ReAct** interleaves reasoning with tool calls. **Toolformer** shows models learning when to call an API.

Their shared limitation, in red: **grounding is encouraged, not enforced. The model still writes the answer and decides what to trust.**

> *Move briskly. The one idea to land is the red column of the last three rows.*

**Bridge to slide 5:** “The third group is the closest systems to mine — and why that limitation matters.”

---

## Slide 5 — Literature survey III — LLM decision support, reliability, evaluation

**1:30**

**ClimSight**, in npj Climate Action 2025, and **WildfireGPT**, 2025, are the closest relatives: multi-agent LLM systems for climate and wildfire decision support, grounded by retrieval. But they answer analytical questions for planners, ground in documents, and still let the model write the conclusion.

One finding matters a lot to me. ClimSight's extension, XCLIM-AI, reports its **largest gains when indicators are computed deterministically rather than generated.** That is independent support for my design.

**Lin et al., 2025**, surveyed hallucination in AI agents — five workflow stages, eighteen causes — and warn that errors can be physically consequential. That is why my verification is mechanical, not a prompt instruction.

**IndicTrans2** covers all 22 scheduled languages — translation is solved, but nobody has attached it to a marine system. And **Jolliffe and Stephenson** give the standard way to score warnings, POD and FAR — which nobody in this domain has applied to the verdict itself.

> *Pause on the ClimSight finding. It is the single strongest piece of external support for the whole architecture.*

**Bridge to slide 6:** “Putting the three groups side by side gives the research gap.”

---

## Slide 6 — Research gap — comparative analysis

**1:45**

Every row here is a study from the survey. Across the top, the properties my problem needs.

The **Small Vessel Advisory** is the only one with a deterministic safety verdict — and it fails every other column. The fishing-zone advisories and Fisher Friend reach many languages, but they are broadcast. **ClimSight and WildfireGPT** are conversational, but they ground in documents and let the model conclude.

Nobody has the bottom row.

So the gap: **no published system lets a fisherman ask one question in his own language and receive a single operational decision — safety, fishing and border together — that is provably derived from official products rather than generated by a model.**

> *Walk the table row by row with your hand. Pause after “Nobody has the bottom row.” This is the 5-mark research-gap slide.*

**Bridge to slide 7:** “That breaks down into six specific gaps, and each one becomes an objective.”

---

## Slide 7 — Research gaps and objectives

**1:15**

On the left, each gap with its evidence from the survey. On the right, the objective that answers it.

Fragmentation and broadcast-only, **G1 and G2**, become **O1**: one conversational interface across all three products. Language depth becomes **O4**.

**G4 and G5 are the important ones.** Grounding is only at document level and hallucination is unsolved — so **O3**, an evidence ledger and a verifier that deletes any unsupported number. And no architecture keeps safety out of the model — so **O2**, a deterministic, tested safety verdict that sits structurally outside it.

**G6**, evaluation that stops at RMSE, becomes **O6**: evaluate the verdict. And because connectivity at sea is unreliable, **O5**: always answer, and say when the answer is degraded.

**O2 and O3 are my research contribution.**

> *Trace one or two rows across the table with your hand so the gap → evidence → objective link is visible.*

**Bridge to slide 8:** “Here is how the methodology delivers them.”

---

## Slide 8 — Proposed methodology I — architecture and techniques

**1:15**

Five steps. The diagram on the right is the same pipeline — **blue is AI, red is no AI.**

Step one, an LLM planner turns the question into a typed task graph, validated against a schema. Step two, three specialists fetch data in parallel through LangGraph, with a cache, live, stale, snapshot fallback chain.

**Below the red line there is no model.** Step three is the decision: seven parameters, three vessel classes, the worst parameter wins — never an average. Under fifty milliseconds, 115 unit tests.

Step four, the model explains the verdict in the user's language. Step five, every number in that answer, in Latin or Indic digits, is matched against the **evidence ledger**; anything unsupported is stripped and the answer regenerated.

The ledger is what makes that possible: **no tool returns a bare number** — every value carries its source, time, distance and confidence.

> *Tap the red dashed line in the diagram when you say “below the red line there is no model.”*

**Bridge to slide 9:** “And the dataset behind it.”

---

## Slide 9 — Proposed methodology II — dataset and tools

**1:30**

**Every source here was tested live before I wrote any code against it.**

**Open-Meteo** marine and weather is the primary source for waves, wind and visibility — hourly, free, no key. **INCOIS** provides the daily fishing-zone advisories, plus 14 sectors and 1,223 named landing centres. **Marine Regions** provides India's EEZ and the IMBL. Chlorophyll comes from **NOAA** and **Copernicus**, where I have an account.

Two red rows, honestly. **IMD** — cyclone and lightning — needs an API key; without it, two of the seven safety checks have no data. And **INCOIS's open ERDDAP archive is stale** — its sea temperature series stops in 2011 — so it is not used.

Two derived datasets: a frozen seven-day snapshot for five harbours and the Gulf of Mannar, so it runs offline; and a 92-day evaluation set. Tools are along the bottom. **Total data cost: zero.**

> *She cares most about datasets — slow down here. Raise the two red rows yourself before she asks.*

**Bridge to slide 10:** “Finally, how well it works so far.”

---

## Slide 10 — Evaluation method and preliminary results

**1:15**

Last review, you asked how often we are right. Prediction is the verdict from the evening-before forecast; truth is the verdict from the model's analysis of that morning; **460 harbour-mornings** through the monsoon.

Day ahead, **93.9 %** of dangerous mornings were warned, and only **3.1 %** of warnings wasted a good day. **Both misses were graded caution — none were graded go.** It fails toward safety.

The limitation: truth here is model analysis, not a buoy, so this is an **upper bound**.

Four of six phases are complete. Three things would materially improve it: **an IMD API key, which needs a letter on college letterhead**; INCOIS's small-craft criteria; and buoy data from INCOIS or NIOT.

Thank you. I am happy to take questions.

> *Say each of the three needs, then stop talking. Advance to the references slide and leave it on screen during questions.*

---

## Timing

| Slides | Content | Time |
|---|---|---|
| 1 – 2 | Opening and problem definition | 1:45 |
| 3 – 5 | Literature survey (three slides) | 4:30 |
| 6 – 7 | Research gap and objectives | 3:00 |
| 8 – 9 | Methodology: architecture, dataset, tools | 2:45 |
| 10 | Evaluation and status | 1:15 |
| 11 | References — leave on screen for questions | — |
| | **Total** | **≈ 13:15** |

**If you are told to cut to eight minutes: on slide 4 say only the red-column line; on slide 7 cover only G4/G5 → O2/O3; on slide 9 cover only the two red rows. Never cut slides 3, 5 or 6 — they carry the 15 literature-and-gap marks.**

---

## Questions she is likely to ask

**Q. How did you choose the literature?**

Three groups, matching the three parts of the problem. First, the domain: India's own marine information services, because that is what a fisherman uses today. Second, the techniques I could build with: machine-learned forecasting as the alternative I rejected, and tool-using language models as the approach I took. Third, the closest systems to mine, plus reliability and evaluation. Every reference was checked against its publisher or repository record.

**Q. Why not just let the AI decide? The models are very good now.**

Three reasons. I cannot test it — a rule table can be unit-tested and audited by anyone; a model's judgement cannot. There is no training data for it — no dataset of boats that did and did not come back. And Lin et al. show agent errors can be physically consequential. If someone drowns, “the model decided” is not an acceptable answer. The model is very good at language, so I use it for language.

**Q. Isn't this just a wrapper around some APIs? Where is the novelty?**

The fetching is ordinary engineering. The contribution is O2 and O3: an architecture where the safety verdict is structurally outside the model, not just prompted to be; and an evidence ledger with a verifier that mechanically deletes any number the model produced that is not in it. ClimSight and WildfireGPT ground in documents and still let the model write the conclusion.

**Q. How is your work different from INCOIS's Small Vessel Advisory?**

SVAS is the closest existing product and I build on it rather than compete with it. It gives a boat safety index as a colour map, in English, with unpublished thresholds, and separately from fishing zones and borders. My system takes a question in the user's language, combines safety, fishing zones and boundary warnings for one boat, place and time, and shows the source of every number. SVAS is also my calibration target — it independently uses steepness and vessel size, as I do.

**Q. Where does 93.9 % come from? Is that a real measurement?**

It is a backtest over 92 mornings at five harbours through this monsoon — 460 harbour-mornings. For each, I take the forecast available the evening before, run it through my safety engine, and compare that verdict with the verdict from the same model's final analysis. That is standard warning verification from Jolliffe and Stephenson. It regenerates with one command.

**Q. But you have no buoy data. So how do you know you are right?**

I do not, fully, and the synopsis says so. My truth is the model's analysis, not a physical measurement, so my figures are an upper bound. The harness is written so that with buoy observations I change the truth source and rerun. That is one of my three asks.

**Q. This is an ISRO/INCOIS problem statement, but your primary source is Open-Meteo. Why?**

Because INCOIS's own open data archive is largely stale — their public sea-temperature series stops in 2011 and chlorophyll in 2006. I tested all of it before writing any code. I use INCOIS for what is live and excellent: fishing-zone advisories, sector and landing-centre layers, boundary lines. Open-Meteo is the reliability floor for waves and wind. With IMD and deeper INCOIS access, Indian sources move up the fallback chain — it is built for that substitution.

**Q. Did you train a model?**

No, deliberately. GraphCast and Pangu-Weather are in my survey as the road not taken: training a competitive forecaster needs decades of reanalysis and compute, and would replace a product INCOIS already provides, validated and free. My contribution is reasoning over official forecasts, not replacing them.

**Q. What if the translation is wrong in Tamil?**

The verdict is computed before any translation, so translation cannot change it. And the verifier checks numbers in both Latin and Indic digits, so a fabricated figure is caught in Tamil too. The remaining risk is tone, which is why the target path is Bhashini, the government service — Phase 5, waiting on keys.

**Q. Have you validated your safety thresholds?**

Not yet, and I say so in the report and in the code. They are sensible starting values. INCOIS's Boat Safety Index is the right calibration target, but its numeric criteria are not published. Getting them is one of my asks.

**Q. What happens when there is no internet at sea?**

Four-step fallback: fresh cache, live fetch with a two-second budget, stale cache, then a frozen snapshot committed in the repository. It always gives a complete answer, always says which source answered, and lowers its stated confidence.

**Q. Will you finish it?**

Four of six phases are done and it works end to end today. What remains is the official translation path, optional features and hardening. The real risk is the three access blockers, which is why I am raising them now.

---

## The three asks

| Ask | What it needs | Why |
|---|---|---|
| IMD API key | A request letter on college letterhead. Unlocks lightning and cyclone — two of the seven safety checks are coded and tested but have no data. | Highest value |
| INCOIS small-craft criteria | The numeric thresholds behind the Boat Safety Index. Ask whether the department has an INCOIS contact. | Replaces “provisional” |
| INCOIS / NIOT buoy data | Turns the evaluation from model-against-model into model-against-the-sea. | Strengthens results |

---

## If she asks about the synopsis

| Section | What is in it |
|---|---|
| Abstract | The argument in three paragraphs, ending on the 93.9 % result. |
| §1  Introduction and Problem Definition | Context, the boxed problem statement, six objectives. — 5 marks |
| §2  Literature Review | Eleven subsections plus the comparison table (2.11). — 10 marks |
| §3  Research Gap | One bold sentence, then gaps G1–G6, each mapped to an objective. — 5 marks |
| §4  Proposed Methodology | Architecture, Observation schema, threshold table, data sources, tools, evaluation method. — 5 marks |
| §5  Progress and Results | Four of six phases, 115 tests, the accuracy table, latency. |
| §6  Remaining Work | Phases 5 and 6, plus three blockers with reasons. |
| References | Fifteen, each checked against the publisher record. |

---

## Numbers worth knowing cold

| Figure | Value |
|---|---|
| Phases complete | 4 of 6 |
| Unit tests passing | 115 |
| Day-ahead hit rate (POD) | 93.9 % |
| Day-ahead false-alarm ratio (FAR) | 3.1 % |
| Backtest sample | 92 mornings × 5 harbours = 460 |
| Misses graded GO | Zero (both graded CAUTION) |
| Tamil question, end to end | ~8 seconds |
| Safety decision time | under 50 ms |
| Numbers recorded per question | ~130 |
| Named landing centres | 1,223 |
| PFZ sectors | 14 |
| References | 15, all verified |
| Total external cost | ₹0 |
