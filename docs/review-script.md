# Sagar Setu — review script

*Spoken, ~12 minutes plus questions. [Cues in brackets.] Files: `docs/datasets.md`,
`docs/datasets/Sagar_Setu_Datasets.xlsx`, `map_datasets.png`, `chlorophyll_kochi.png`.*

---

## 1. The problem (1 min)

Every morning, a fisherman with a 9-metre boat on the Kerala or Tamil Nadu coast makes
two decisions. Is it safe to go out? And where should I go? The information to answer
both exists — INCOIS publishes fishing zones, weather models publish waves and wind, the
boundary with Sri Lanka is a known line — but it is spread across half a dozen sources,
most of it in English, none of it conversational, and some of it needs a scientist to
interpret.

Every year fishermen die in weather that was forecast, and every year Tamil Nadu
fishermen are detained for crossing a line they could not see.

## 2. The idea (1 min)

Sagar Setu is a conversational assistant. The fisherman types a question in Tamil, Hindi
or English — "is it safe to go out from Kochi tomorrow morning?", "where are the fish
today?", "how far is the Sri Lanka line on this heading?" — and gets an answer in the
same language, with a map, and with the evidence behind every number.

Two design rules shape everything, and I want to state them up front because they
explain every choice in the datasets.

First: **the system never invents a number.** Every value shown to the user is in what we
call an evidence ledger — with its source, the time it is valid for, how far the nearest
data point is from the user, and how fresh it is. If a source is missing, the answer
says so.

Second: **a language model never decides whether it is safe.** The safety verdict comes
from a deterministic rulebook — published thresholds, worst-case-wins. The AI understands
the question and explains the answer. It does not make the decision.

## 3. The datasets (5 min)

[Open the map.]

This is every spatial dataset on one map, drawn from the actual data we fetched.

The green lines are **INCOIS's Potential Fishing Zone advisory** — 87 lines for the 14th
of September. INCOIS makes these from satellite sea-surface temperature and chlorophyll;
they have twenty years of validation against catch data. We consume this product; we do
not try to predict fishing zones ourselves. We access it through the same server that
INCOIS's own web map uses. Notice the Tamil Nadu and Gujarat coasts are empty — INCOIS
issued no advisory for those sectors that day. The system must say "no advisory for your
sector today", not invent one.

The orange dashed lines are the **international maritime boundaries** from Marine
Regions — the Flanders Marine Institute's dataset, the standard reference used by FAO and
UNEP. The one at the bottom right of India, through the Gulf of Mannar, is the India –
Sri Lanka line. That is our main geofencing test case.

The grey outline is the EEZ, and the blue dots are our five test harbours — chosen to
span both coasts, the Andamans, and different monsoon regimes.

[Open the workbook, Catalogue sheet.]

Ten datasets in all. Let me go through the ones that do the work.

**Open-Meteo** gives us the marine forecast — wave height, period, swell, sea temperature,
currents — and the weather — wind, gusts, visibility — hourly, eight days ahead. It is a
free open-data service built on the European wave and weather models. It answers in about
300 milliseconds from any connection, which is why it is the foundation every other source
falls back to. [Click the Open-Meteo marine sheet — 2,160 real hourly rows.]

**Copernicus Marine**, the EU's ocean service, gives us chlorophyll — a proxy for
plankton, so for productivity. [Open the chlorophyll chart.] This is five years of daily
chlorophyll off Kochi. You can see the south-west monsoon upwelling bloom every June to
September. And you can see that the 2026 bloom is visibly weaker than 2022, 2024 and 2025.
We noticed this in the data while preparing this review — it is exactly the "why is the
catch declining" question, and it is something we intend to test properly, not something
we are claiming today.

The orange dots are a second chlorophyll source — **NOAA's VIIRS satellite** — at the
coastal pixel. They read several times higher. That is not an error: a 4-kilometre
coastal pixel and a 28-kilometre offshore average measure different water. Our rule is to
show both with their distances and flag the disagreement. We never average two sources.

Then the static datasets: INCOIS's **1,223 fish landing centres**, which we use to turn a
place name like "Vypeen" into coordinates without any commercial geocoding service; the
**14 PFZ sectors**; and the EEZ polygon.

[Switch to `datasets.md`, section 4.]

I also want to show what we evaluated and could not use, because that shaped the design.

INCOIS's own gridded data server is reachable, but when we listed its datasets with their
end dates, chlorophyll stopped in 2006, sea-surface temperature in 2011, and winds in
2023. Only the Argo float data is current. So Open-Meteo carries the live forecast role.

**IMD's API** — cyclone track, cyclone cone, lightning, district warnings — returns "API
key missing" on every endpoint. Registration requires a signed letter from the head of the
institute. We have the application drafted. Until we have it, cyclone and lightning are two
of our six safety parameters with no live feed — the system says so in every verdict rather
than pretending.

And one that would have embarrassed us: INCOIS's landing-centre layer has bearing,
distance and depth fields that look like today's advisory. Every record is dated 27 April
2024. We caught it and compute bearing and distance ourselves from the live line
geometry.

## 4. How we verified them (1 min)

Every endpoint was called from our own machine before we wrote code against it. For each
one we checked: does it answer, what is the latest timestamp in the data, and does it have
a value at our harbours. We recorded the URL, status, response time and size of every call
— that is the "Fetch manifest" sheet in the workbook. The documentation was treated as a
hypothesis; the live response was the test. Three of the seven sources in the original
design failed that test, and the design changed.

## 5. Progress (3 min)

We planned six phases and have completed two.

**Phase 1** was what I have just shown: prove the data and freeze it. We cached a week of
real data for five harbours, so the whole system runs with the network unplugged — with
every value labelled as coming from the stored copy.

**Phase 2** built the deterministic core, with no AI in it. Four pieces.

The **evidence ledger** — the receipts. A question about Kochi produces about 130 rows,
each with source, time, distance and confidence.

The **fallback chain** — fresh cache, then live with a two-second budget, then older cache,
then the frozen snapshot. The answer always comes; only the label changes. We tested it by
pointing the system at a dead server.

**Geofencing** — am I inside the EEZ, how far is the nearest boundary and in which
direction, and — the predictive part — if I hold this heading at this speed, when do I
cross it. The warning comes before the crossing, not after.

And the **safety rulebook**. Seven parameters — wave height, wind with gusts, sea
steepness, visibility, lightning, cyclone, boundary — each graded go, caution, or do-not-
sail against a threshold table that depends on the size of the boat. Then the verdict is
simply the worst grade. Never an average. And if wave or wind data is missing, it cannot
say go.

It has 40 unit tests, including the case the rule exists for: calm sea, thunderstorm
overhead — caution, not go.

[Optional live demo — 30 seconds, offline-safe:]

```
uv run python scripts/ask.py kochi
uv run python scripts/ask.py --lat 9.15 --lon 79.40 --heading 90 --speed 8
```

The second one is a boat in the Gulf of Mannar heading east at 8 knots. Sea state is
calm. The verdict is DO NOT SAIL — the heading crosses the Sri Lanka line in 59 minutes.
That one line is the worst-case rule working.

**Phase 3**, the AI layer, is built and working — it understands the question in Tamil or
Hindi and explains the verdict in the same language, and a verifier rejects any number in
its answer that is not in the ledger. I would rather demonstrate that properly next time
than rush it today. Phases 4 to 6 are the web interface with the map, government
translation integration, and hardening.

Everything is on GitHub — 104 tests passing without network or model, and a step-by-step
build log of every decision.

## 6. Where we would value your guidance (1 min)

Three things.

Our safety thresholds — 1.5 and 2.5 metres for craft under 12 metres, 19 and 27 knots of
wind — are starting values. We would like to cite INCOIS's published High Wave Alert
criteria or IMD's fishermen-warning criteria. If you know where the official document
lives, that turns "provisional" into "as published by INCOIS".

The IMD API key. It needs a letter from the department head. One paragraph on letterhead
unlocks cyclone tracking and lightning, which matter most on the Bay of Bengal side.

And the coastal chlorophyll question — Copernicus versus VIIRS near the coast differ by
three times. Whether there is a preferred product for the Indian shelf, or a known
correction, would help our analytics.

---

## Likely questions — short answers

**"Is this live data?"** Static boundaries are downloaded once. Forecasts and the PFZ
advisory are fetched when a question is asked, cached for an hour to six hours. Copernicus
is pre-fetched in the background because it is slow. A frozen snapshot backs everything.

**"Where is the AI?"** Understanding the question in the user's language, and explaining
the answer in it. Not in the decision. The decision is a threshold table and a worst-of
rule, because a safety verdict must be auditable and there is no training data for one.

**"Why not train a model?"** No labelled dataset of small-craft outcomes exists. A trained
safety model would be confident without evidence. INCOIS's fishing-zone product has twenty
years of validation we cannot match — we consume it.

**"How do you stop the language model making things up?"** It only ever sees a one-page
brief derived from the ledger, never the raw data. After it writes, code scans every number
in its answer and checks it exists in the ledger. If not, the draft is rejected and
regenerated; if that fails, a fixed template answer is used instead.

**"What does it cost to run?"** Nothing. Every data source is free. The language model
runs on a free tier and is swappable by configuration.

**"What happens with no internet?"** It answers from the frozen snapshot, labels every
value as such, and lowers the confidence. Tested.

**"Why five harbours?"** Kochi and Veraval on the Arabian Sea, Chennai and Paradip on the
Bay of Bengal, Port Blair in the Andamans — different data coverage, INCOIS sectors, and
monsoon regimes. Nothing is hard-coded to one place.

**"What is the biggest risk to the project?"** Latency on the free model tier for
non-English questions — about eight seconds end to end. We mitigate with a deterministic
fast path for English, pre-warmed caches, and streaming. And the thresholds being
uncalibrated until we find the official criteria.
