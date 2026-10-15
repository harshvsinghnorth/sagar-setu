# Sagar Setu — Synopsis Report

**An Agentic, Evidence-Grounded Marine Advisory System for Indian Small-Craft Fishermen**

Mid-term review · 13 October 2026
Harshvardhan Singh · Supervisor: Ms. Anusha Chhabra

---

## Abstract

India's ocean information agency, INCOIS, publishes some of the best small-craft marine
guidance in the world — a validated wave and wind forecast, a boat-specific capsizing
advisory, and a satellite-derived fishing-zone advisory with two decades of catch
validation behind it. A fisherman preparing to leave harbour at four in the morning
nevertheless has to open three separate web products, read them in English or as
colour-coded maps, and combine them in his head. This work asks whether a conversational
agent can do that combining for him — in his own language, over a single question — without
ever being the thing that decides whether he goes to sea.

The proposed system, **Sagar Setu**, places a language model on both sides of a
deterministic core. A planner interprets the question and dispatches parallel data
fetches; a fixed, unit-tested rule engine applies published small-craft thresholds and
returns the verdict; a second model pass explains that verdict in the user's language; and
a mechanical verifier deletes any number in the generated answer that is not present in an
evidence ledger of fetched observations. Every value the user sees carries its source,
its valid time, its distance from the query point and its staleness.

A working implementation answers questions at five harbours spanning the Arabian Sea, the
Bay of Bengal and the Andamans. On a 92-day, 460-harbour-morning backtest across the 2026
south-west monsoon, the day-ahead *do-not-sail* verdict achieved a **93.9 % hit rate at a
3.1 % false-alarm ratio**, with no dangerous morning ever graded *go*.

---

## 1. Introduction and Problem Definition

### 1.1 Context

Marine fishing supports roughly four million people along India's 11,098 km coastline, the
large majority of them operating craft under twelve metres. These are open or
partly-decked boats, often without radar, weather fax or reliable offshore connectivity.
The decision that matters is made once a day, in the dark, before the boat leaves: *go, or
stay*. A wrong decision in one direction costs a day's income; in the other it can cost
the boat and the crew.

Two further decisions ride alongside it. *Where should I fish?* — the difference between a
full hold and a wasted tank of diesel. And, in the Palk Bay and Gulf of Mannar, *where is
the border?* — Indian fishermen are detained by the Sri Lankan Navy for crossing the
International Maritime Boundary Line every year, and the boundary is invisible at sea.

India already produces the information needed for all three. The gap is not data. The gap
is the last two hundred metres between a government web portal and a man standing on a
beach at 4 a.m. holding a ₹6,000 Android phone.

### 1.2 Problem statement

> Given a free-form question asked in any of India's scheduled languages, produce a single,
> trustworthy operational answer — safety verdict, fishing guidance and boundary warning
> together — derived verifiably from official marine data products, delivered inside a
> latency budget short enough to be used before a boat leaves, and degrading honestly and
> visibly when data sources are slow or unreachable.
>
> The language model must never be the component that decides whether it is safe to go to
> sea.

### 1.3 Objectives

| # | Objective |
|---|---|
| **O1** | Integrate safety, fishing-zone and maritime-boundary information, currently published as three disconnected products, behind one conversational interface. |
| **O2** | Design an architecture in which the safety verdict is produced by deterministic, unit-tested rules, structurally outside the language model's reach. |
| **O3** | Build an evidence ledger that records provenance, valid time, spatial distance and staleness for every observation, and a verifier that mechanically removes any generated number absent from it. |
| **O4** | Support question-answering in Indian languages end to end, beginning with Tamil and Hindi. |
| **O5** | Guarantee a complete, honest answer under source failure through a cache → live → stale-cache → snapshot fallback chain that declares its own degradation. |
| **O6** | Evaluate the system at the level the user acts on — the verdict — using standard warning-verification statistics (POD, FAR, CSI) rather than model-fit metrics alone. |

---

## 2. Literature Review

Eight studies were selected from a wider survey of twenty, on two criteria: each bears
directly on one component of the system, and preference was given to recent work — half of
the eight were published in 2023 or later. They fall into two groups. The first covers the
fisherman's three information needs and the systems already built to meet them. The second
covers the language-model techniques this work depends on, and their known failure modes.

### 2.1 Localised marine weather for small-boat fishers

Kurup et al. [1] tested whether a localised marine weather service could support safer
artisanal fishing on the coast of Kerala. Using the Weather Research and Forecasting (WRF)
model downscaled to a 5 km grid, and issuing forecasts for 25 km × 25 km zones, they found
three coastal sub-regions with distinct wind regimes, and that such localised forecasts
complement the official forecasts, which are issued for large ocean areas. The study
establishes that a small-boat decision needs local, not regional, information.

**Limitation for this problem.** The output is a better *forecast* — of wind. Turning
it, together with waves, visibility and storm risk, into a go / no-go decision for a
particular boat is still left to the fisherman.

### 2.2 Fishing-zone advisories

Sarangi et al. [2] generated Potential Fishing Zones for the western Bay of Bengal from six
satellite-derived parameters — chlorophyll, sea-surface-temperature fronts, relative winds,
current vectors, Ekman transport and eddies — using feature propagation to keep forecasts
available under cloud. Validated against Fishery Survey of India catch data for 2016–2018,
chlorophyll (food availability) correlated most strongly with catch, followed by fronts and
eddies.

**Limitation for this problem.** The result is a zone map, with no connection to sea safety,
to the user's boat, or to the maritime boundary. The study also shows what producing a
validated PFZ product properly requires, which is why this work **consumes the INCOIS PFZ
advisory rather than re-deriving it**.

### 2.3 Decision-support systems already serving Indian fishers

Two systems are the closest existing relatives of this work.

**Thoondil** (Saka et al. [3]) was developed by the National Centre for Coastal Research
and put into operation by the Tamil Nadu Department of Fisheries after a series of
cyclones. It pairs a web-GIS dashboard for administrators, which tracks fishers at sea and
supports two-way communication, with an Android app offering offline maps with routes to
the nearest port, weather information, potential fishing zones and incident reporting. It
is available in the local language, passed 15,000 downloads within months, and has been
extended to Kozhikode in Kerala.

The **Fisher Friend Mobile Application** (Anabel et al. [4]), developed by the M. S.
Swaminathan Research Foundation with INCOIS, is a decision-support system for small-scale
fishers that brings together potential fishing zones with GPS navigation, ocean-state
forecasts, danger-zone and disaster alerts and market prices in several Indian languages.

Together they show that mobile delivery, local language and the combination of weather with
fishing zones work in practice, and that a state government will operate such a tool.

**Limitation for this problem.** Both are menu-and-screen applications: the fisherman
navigates categories and combines the layers himself. Neither is described as accepting a
free-form question about a specific boat, place and time, issuing a vessel-specific go /
no-go verdict, or showing the source of each number it displays.

### 2.4 The maritime boundary problem

Vincent [5] analyses the persistent Palk Bay fishing conflict across the India–Sri Lanka
International Maritime Boundary Line and argues that it requires joint Indo–Sri Lankan
governance. The study establishes that the boundary problem is recurring and structural
rather than incidental.

**Limitation for this problem.** It is a governance analysis and offers no aid to the
individual fisherman. This work does not address the political dispute; it addresses the
narrower technical need of knowing how far the boundary is and whether the current heading
will cross it.

### 2.5 Grounding language models in external evidence

Retrieval-augmented generation (Lewis et al. [6]) combines a language model's parametric
memory with passages retrieved at query time, improving factual question answering and
addressing the difficulty language models have in providing provenance and updating their
knowledge. This is the principle the system rests on: tomorrow's wave height cannot come
from a model's training data and must be fetched when the question is asked.

**Limitation for this problem.** Retrieval grounds answers in text passages, not live
numeric observations, and does not by itself guarantee that every generated claim is
supported.

### 2.6 Hallucination persists despite retrieval

RAGTruth (Niu et al. [7]) is a corpus of nearly 18,000 naturally generated responses from
a range of language models working in retrieval-augmented settings, manually annotated for
hallucination at both case and word level. It benchmarks hallucination rates across models
and shows that **unsupported content persists even when the correct evidence has been
retrieved**.

**Limitation for this problem.** If retrieval does not guarantee faithfulness, a safety
decision cannot be delegated to the model. This is the direct justification for the
architecture's two research choices: the verdict comes from fixed rules, and every number
in the generated answer is checked mechanically against the evidence ledger.

### 2.7 Indian-language translation

IndicTrans2 (Gala et al. [8]) is the first open translation model covering all 22 scheduled
Indian languages, released with the Bharat Parallel Corpus Collection (230 M sentence pairs)
and the IN22 benchmark.

**Limitation for this problem.** Translation capability is no longer the bottleneck; no
fisher-facing system yet offers conversation through it.

### 2.8 Summary of reviewed work

| Work | Small-boat safety info | Fishing zones | Border awareness | Indian languages | Answers a free-form question | Go / no-go by fixed rules | Every number verified |
|---|---|---|---|---|---|---|---|
| Kurup et al. [1] | ✓ (wind) | ✗ | ✗ | — | ✗ | ✗ | ✗ |
| Sarangi et al. [2] | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Thoondil — Saka et al. [3] | ✓ | ✓ | — | ✓ | ✗ | ✗ | ✗ |
| Fisher Friend — Anabel et al. [4] | ✓ | ✓ | partial | ✓ | ✗ | ✗ | ✗ |
| RAG systems [6], [7] | ✗ | ✗ | ✗ | partial | ✓ | ✗ | ✗ |
| IndicTrans2 [8] | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| **Sagar Setu (proposed)** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** |

*✓ addressed · ✗ not addressed · partial · — not described in the reviewed source.
Vincent [5] establishes the boundary problem but proposes no tool, so is not tabulated.*

---

## 3. Research Gap

> **The reviewed work addresses the parts of the problem separately — localised weather,
> fishing zones, the boundary, mobile delivery, retrieval-grounded language models. We found
> no published system that lets a fisherman ask one question in his own language and
> receive a single operational decision — safety, fishing and border together — that is
> derived verifiably from official data rather than generated by a model.**

Six specific gaps follow from the review.

**G1 — Fragmentation [1]–[5].** Kurup et al. address wind, Sarangi et al. fishing zones,
Vincent the boundary. Thoondil and Fisher Friend bundle several of these, but as separate
screens that the fisherman must read and combine himself.

**G2 — Interaction mode [3], [4].** The existing systems are menu-driven. Neither accepts a
free-form question carrying the vessel, place, heading and departure time that actually
determine the answer.

**G3 — Language depth [3], [4], [8].** Existing apps offer local-language content. With
IndicTrans2 covering 22 languages, the limit is no longer translation but the absence of a
conversational fisher system to attach it to.

**G4 — Verifiability [6], [7].** Retrieval grounds answers in evidence, but RAGTruth shows
unsupported content persists even with retrieval. No fisher-facing system shows per-number
provenance or checks its numbers mechanically.

**G5 — Structural safety separation [6], [7].** Given G4, any system that lets a language
model generate the safety call inherits its hallucination risk. No reviewed system keeps the
go / no-go decision in tested, deterministic rules separate from the model.

**G6 — Evaluation at the level of action [1], [2].** Kurup et al. validate a forecast and
Sarangi et al. validate zones against catch. Neither evaluates a go / no-go *decision*, the
thing a fisherman acts on, with warning statistics such as hit rate and false-alarm ratio
[10].

| Gap | Evidence | Objective |
|---|---|---|
| G1 Fragmentation | [1]–[5] | O1 |
| G2 Broadcast / menu interaction | [3], [4] | O1 |
| G3 Language depth | [3], [4], [8] | O4 |
| G4 Verifiability | [6], [7] | O3 |
| G5 Safety separation | [6], [7] | O2 |
| G6 Evaluation stops at the forecast | [1], [2] | O6 |
| Operational constraint: unreliable connectivity at sea (Thoondil ships offline maps for this reason) | [3] | O5 |

---

## 4. Proposed Methodology

### 4.1 Architecture

Five stages, with the language model deliberately confined to the first, second and fourth:

1. **Understand the question** *(LLM)* — detect language, resolve the place name to
   coordinates, extract time, vessel class, heading and speed; emit a typed task DAG.
2. **Collect the data** *(LLM-dispatched, plain Python execution)* — three specialists run
   concurrently: Ocean & Weather, Geospatial & Boundary, Analytics & Causal.
3. **Decide if it is safe** *(no model)* — the deterministic risk engine.
4. **Write the answer** *(LLM)* — explain the verdict in the user's language.
5. **Check every number** *(no model)* — the verifier.

All data access passes through a typed tool belt of roughly fifteen Pydantic-validated
functions; a malformed tool call fails at the boundary instead of becoming a wrong number in
an answer.

### 4.2 The evidence ledger

No tool returns a bare float. Every value is an `Observation`:

```python
class Observation(BaseModel):
    variable: str        # "significant_wave_height"
    value: float
    unit: str            # "m"
    source: str          # "open_meteo/mfwam"
    valid_time: datetime # what the value is FOR
    fetched_at: datetime # when we got it
    distance_km: float   # query point to nearest grid node
    confidence: float    # lowered when we fall down the source chain
    note: str | None     # "served from snapshot, network unavailable"
```

A typical briefing records about 130 observations. The ledger is rendered in the interface
beneath every answer, with staleness shown prominently — a six-hour-old forecast and a
six-minute-old one must not look alike on screen.

### 4.3 The deterministic risk engine

Seven parameters, three vessel classes (traditional < 12 m, motorised 12–20 m, mechanised
> 20 m), evaluated as a pure function in under 50 ms:

| Parameter | Go | Caution | Do not sail |
|---|---|---|---|
| Significant wave height | < 1.5 m | 1.5 – 2.5 m | > 2.5 m |
| Sustained wind | < 19 kt | 19 – 27 kt | > 27 kt |
| Sea steepness (Hs/T²) | low | short-period swell | breaking-sea regime |
| Lightning proximity | none < 50 km | 50 – 100 km closing | any strike < 50 km |
| Cyclone cone of uncertainty | no intersect | intersect 72 – 120 h | intersect < 48 h |
| Visibility | > 5 km | 2 – 5 km | < 2 km |

**The worst parameter decides. Never an average.** Averaging across six parameters is how a
system sends a boat out under a thunderhead because the waves happened to be calm. Missing
wave or wind data can never produce a *go*.

These values are provisional starting points. INCOIS's Small Vessel Advisory Service [9]
computes a Boat Safety Index from wave height, wave steepness, directional spread and the
rapid growth of wind sea, issued per vessel beam-width class (< 4 m, 6 m, 7 m). It
independently selects steepness and vessel size, as this work does, and is the calibration
target; its numeric thresholds are not published, so calibration is an identified task, not
a completed one.

### 4.4 Data sources

| Source | Provides | Access |
|---|---|---|
| Open-Meteo Marine + Weather | Wave height/period/direction, swell, currents, wind, gusts, visibility | Free, no key — the reliability floor |
| INCOIS PFZ (GeoServer WFS) | Daily Potential Fishing Zone advisories by sector | Open, cached daily |
| INCOIS static layers | 14 PFZ sectors, 1,223 named landing centres | Open, committed |
| Marine Regions (VLIZ) | Indian EEZ, IMBL, boundary polygons | Static GeoJSON |
| NOAA CoastWatch | Chlorophyll-a | Open |
| Copernicus Marine | Chlorophyll-a, physics | Free account |
| IMD | Cyclone track, lightning, district warnings | **Pending access key** |
| INCOIS ERDDAP | SST and chlorophyll archive | Open, but stale (SST ends 2011) — not used |

Every fetch follows a four-step chain: **fresh cache → live (2 s budget) → stale cache →
frozen snapshot**, with confidence 0.95 / 1.00 / 0.70 / 0.50 respectively. The system
produces a complete, honest answer with the network unplugged, and says that it is doing so.

### 4.5 Tools and techniques

Python 3.11 · Pydantic · LangGraph · FastAPI with SSE streaming · xarray/netCDF4 · Shapely ·
httpx (async) · pytest · React 19 + Vite + MapLibre GL · model-agnostic LLM layer (Gemini
free tier, Ollama, or none). Total external cost to date: **₹0**.

### 4.6 Evaluation method

Prediction: the verdict computed from the forecast available the evening before. Truth: the
verdict computed from the same model's final analysis for that morning. Sample: 92 mornings
× 5 harbours = 460 harbour-mornings per lead time, across the 2026 south-west monsoon.
Scored with POD, FAR, CSI and a 3×3 confusion matrix [10].

This is forecast-versus-analysis, which is an **upper bound** on true skill; no public
INCOIS or NIOT buoy feed is available to us. The harness runs unchanged against buoy data
if access is obtained — this is the single most valuable thing the department could help
secure.

---

## 5. Progress and Preliminary Results

Four of six planned phases are complete: data-source verification and snapshotting; the
typed tool belt and risk engine; the LangGraph agent system with planner and verifier; and
the FastAPI + MapLibre interface. The implementation is approximately 4,700 lines of Python
and 630 of TypeScript, with 115 passing unit tests concentrated on the risk and geospatial
modules.

**Verdict skill, 92 days × 5 harbours, pooled (do-not-sail event):**

| Forecast lead | n | hit rate (POD) | false-alarm ratio (FAR) | CSI | 3-way agreement |
|---|---|---|---|---|---|
| 1 day ahead | 460 | **93.9 %** | **3.1 %** | 91.2 % | 93.5 % |
| 2 days ahead | 460 | 97.0 % | 17.9 % | 80.0 % | 90.2 % |
| 3 days ahead | 460 | 90.9 % | 30.2 % | 65.2 % | 85.0 % |

The two day-ahead misses were graded *caution*, never *go* — the asymmetry the worst-of rule
is designed to produce. Skill degrades with lead time mainly through false alarms, which
argues for presenting the day-ahead verdict as the decision and longer leads as outlook.

Measured end-to-end latency for a Tamil question is approximately 8 s, of which the two
language-model stages account for 7.4 s and the safety decision for 0.0001 s.

---

## 6. Remaining Work

| Phase | Work | Status |
|---|---|---|
| 5 | Bhashini round trip with IndicTrans2 fallback; A* route optimisation; causal productivity query | In progress |
| 6 | Offline hardening, error states, five-location regression, rehearsal | Pending |
| — | Calibrate thresholds against INCOIS SVAS criteria [9] | **Blocked** — criteria not published numerically |
| — | IMD API key for lightning and cyclone parameters | **Blocked** — requires institutional letter |
| — | Buoy observations to replace analysis as evaluation truth | **Blocked** — requires INCOIS/NIOT data access |

---

## References

### Literature reviewed

[1] P. H. Kurup, S. Abhilash, S. Mavath, V. K. Mini, N. Alamirew, and M. Martin, "Validation of localised coastal wind forecasts for artisan fishers of southwestern India," *Weather*, vol. 79, no. 7, pp. 231–241, 2024. doi: 10.1002/wea.4554

[2] R. K. Sarangi, M. Jishad, R. Sharma, *et al.*, "Multiple ocean parameter-based potential fishing zone (PFZ) location generation and validation in the Western Bay of Bengal," *Environmental Monitoring and Assessment*, vol. 196, no. 1, art. 98, 2024. doi: 10.1007/s10661-023-12259-6

[3] S. K. Saka, A. E. Mathew, V. Ganesh, *et al.*, "A Web-GIS and mobile-based application for a safe ocean for fishers," *Marine Technology Society Journal*, vol. 55, no. 3, pp. 50–57, 2021. doi: 10.4031/MTSJ.55.3.10

[4] N. J. Anabel, S. Velvizhi, and D. Suvitha, "Fisher Friend Mobile Application: a decision support system for small scale fishers in India," *CSI Transactions on ICT*, vol. 6, no. 3–4, pp. 257–267, 2018. doi: 10.1007/s40012-018-0212-1

[5] S. Vincent, "Palk Bay fishing problem requires Indo-Sri Lankan joint-governance," *Maritime Affairs: Journal of the National Maritime Foundation of India*, vol. 16, no. 2, pp. 71–88, 2020. doi: 10.1080/09733159.2020.1838717

[6] P. Lewis, E. Perez, A. Piktus, *et al.*, "Retrieval-augmented generation for knowledge-intensive NLP tasks," in *Adv. Neural Inf. Process. Syst. (NeurIPS)*, vol. 33, pp. 9459–9474, 2020.

[7] C. Niu, Y. Wu, J. Zhu, S. Xu, K. Shum, R. Zhong, J. Song, and T. Zhang, "RAGTruth: A hallucination corpus for developing trustworthy retrieval-augmented language models," in *Proc. 62nd Annu. Meeting Assoc. Comput. Linguistics (ACL)*, vol. 1, pp. 10862–10878, 2024.

[8] J. Gala, P. A. Chitale, R. AK, *et al.*, "IndicTrans2: Towards high-quality and accessible machine translation models for all 22 scheduled Indian languages," *Transactions on Machine Learning Research (TMLR)*, 2023. arXiv:2305.16307

### Methodology references

[9] Indian National Centre for Ocean Information Services, "Small Vessel Advisory and Forecast Services (SVAS)," INCOIS Ocean State Forecast portal. [Online]. Available: https://incois.gov.in/portal/osf/SVA_overview.jsp

[10] I. T. Jolliffe and D. B. Stephenson, *Forecast Verification: A Practitioner's Guide in Atmospheric Science*, 2nd ed. Chichester, UK: Wiley-Blackwell, 2012.
