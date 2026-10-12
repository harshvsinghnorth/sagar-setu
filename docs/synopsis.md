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

### 2.1 Operational ocean forecasting for Indian waters

INCOIS operates the Ocean State Forecast (OSF) service, issuing wave height, period,
direction, currents and sea-surface temperature for the Indian Ocean. Nair et al. [1]
report the system's performance against wave-rider buoys, ship-mounted wave-height meters
and satellite altimeters, finding a scatter index generally below 15 % for significant wave
height, and a correlation of 0.98 with an RMS error of 0.35 m at Gopalpur during Cyclone
Phailin. The service is operational, validated and publicly reachable — which is why this
work consumes it rather than attempting to improve on it.

### 2.2 Small-craft safety advisories

INCOIS's **Small Vessel Advisory and Forecast Service (SVAS)** [2] is the closest existing
product to the safety half of this work. It is an impact-based service that identifies
potential vessel-overturning zones up to **ten days in advance** using a **Boat Safety
Index** computed from significant wave height, wave steepness, directional spread and the
rapid development of wind sea. Advisories are issued per vessel **beam-width category —
under 4 m, 6 m and 7 m** — covering the fishing fleets of all nine coastal states.

Two observations follow. First, SVAS validates the parameter choice made in this work:
steepness and vessel size, not wave height alone, govern capsizing. An INCOIS presentation
on small-craft advisories [3] notes that capsizing is *not a phase-averaged phenomenon*,
which is precisely why a threshold table rather than a regression is the defensible
instrument. Second, SVAS is delivered as a colour-coded map on a web portal. It answers
*where*, for a reader who already knows to look, in English. It does not answer a question.

### 2.3 Fishing-zone advisories and their measured benefit

INCOIS issues Potential Fishing Zone (PFZ) advisories from sea-surface temperature and
ocean-colour chlorophyll fronts. Pillai and Nair [4] validated these advisories along the
Kerala coast over 2006–2010, using both catch data from active fishers and controlled
experiments run simultaneously inside and outside notified zones. Catch per unit effort was
higher inside the zones — roughly two to six times the catch, and two to seven times the
monetary benefit. Reported multipliers vary widely between studies and most evidence comes from
institute-affiliated researchers, so the effect size should be treated with caution — but
the direction is consistent and the product has two decades of operational history. This
work therefore **consumes the PFZ advisory and does not attempt to re-derive it**.

### 2.4 The last-mile dissemination problem

Delivery has been studied more than it has been solved. The Fisher Friend Mobile
Application distributes advisories in nine Indian languages across seven coastal states;
INCOIS operates multilingual SMS and a 24×7 helpline; a telecom pilot extended mobile
signal roughly 30 km offshore specifically to carry ocean-state forecasts [5]. INCOIS's own
service review notes that helpline numbers "need to be popularised among fishers."

Every one of these channels is **broadcast**. A bulletin is pushed; a map is published; an
SMS arrives. None of them accepts *"I am leaving Rameswaram at five tomorrow morning,
heading ninety degrees at eight knots in a nine-metre boat — is that sensible?"* The
information is multilingual, but the interaction is not conversational, and the specific
combination of vessel, heading, time and place that determines the real answer cannot be
expressed.

### 2.5 Machine-learned weather forecasting

Data-driven global forecast models now match or exceed physics-based numerical weather
prediction on headline scores — GraphCast [6] and Pangu-Weather [7] being the prominent
examples. This literature is relevant chiefly as a road deliberately not taken. Training a
competitive forecast model requires decades of reanalysis, substantial compute, and
validation infrastructure that a student project cannot supply, and the operational product
it would compete with is already validated and free. The contribution available here is in
*reasoning over* official forecasts, not in replacing them.

### 2.6 Language models as tool-using agents

The technique that makes this work possible is the use of language models as planners that
call external tools rather than as sources of fact. ReAct [8] interleaves reasoning traces
with tool actions; Toolformer [9] shows models can learn when to call an API;
retrieval-augmented generation [10] established the general pattern of grounding generation
in retrieved external evidence rather than parametric memory.

### 2.7 Domain advisory systems built on language models

Two recent systems are the closest architectural relatives of this work.

**ClimSight** (Kuznetsov et al. [11]) couples an LLM with local climate data through an
agent-based architecture that routes queries to specialised modules, using retrieval to
ground responses in climate models and reports. A subsequent extension, XCLIM-AI, couples
the LLM interpretation layer with *deterministic computation* of climate indicators,
reporting that the largest gains in actionability and uncertainty reporting appear when
deterministic indicator computation is integrated rather than generated. That finding is
the single strongest external support for the architecture proposed here.

**WildfireGPT** (Xie et al. [12]) is a retrieval-augmented multi-agent LLM system for
natural-hazard decision support, grounded in hazard projections, observational datasets and
scientific literature, and evaluated across ten expert-led case studies.

Both ground their output in **retrieved documents**, and both answer **analytical** questions
for planners and researchers. Neither issues an operational go/no-go decision to a layperson
who will act on it within hours, and neither grounds in live numeric observations carrying
per-value provenance.

### 2.8 Hallucination and the limits of grounding

Lin et al. [13] survey hallucination in LLM-based agents, proposing a taxonomy across the
agent workflow — reasoning, execution, perception, memorisation and communication — and
cataloguing eighteen triggering causes. They observe that agent errors can be "physically
consequential" and cascade through long task chains. Related work on tool-use failure
identifies **tool bypass**, in which a model simulates a tool's output instead of calling it
— a failure mode that defeats auditing precisely when auditing matters most.

This literature is why prompt instructions such as *"only use the data provided"* are
treated in this work as insufficient. The system is designed so that an unsupported number
is **mechanically removed**, not merely discouraged.

### 2.9 Indian-language NLP

IndicTrans2 (Gala et al. [14]) is the first open translation model covering all 22 scheduled
Indian languages, released with the Bharat Parallel Corpus Collection (230 M bitext pairs)
and the IN22 benchmark. With Bhashini, the National Language Translation Mission's API
layer, it makes multilingual operation a solved engineering problem rather than a research
one — removing the usual excuse for shipping marine advisories in English.

### 2.10 Forecast verification methodology

Warning systems are conventionally scored with the 2×2 contingency table — probability of
detection, false-alarm ratio, critical success index — as set out by Jolliffe and
Stephenson [15]. This framework is adopted here, because the quantity a fisherman acts on is
a categorical warning, not a wave height, and because misses and false alarms carry utterly
different costs and must therefore be reported separately rather than merged into a single
accuracy figure.

### 2.11 Summary of reviewed systems

| System | Conversational | Indian languages | Live numeric data | Deterministic safety verdict | Per-number provenance | Safety + fish + boundary together | Verdict-level accuracy reported |
|---|---|---|---|---|---|---|---|
| INCOIS OSF [1] | ✗ | partial | ✓ | n/a (forecast, not verdict) | ✗ | ✗ | ✗ (RMSE/SI reported) |
| INCOIS SVAS [2] | ✗ | ✗ | ✓ | ✓ (Boat Safety Index) | ✗ | ✗ | ✗ |
| INCOIS PFZ [4] | ✗ | ✓ (10) | ✓ | n/a | ✗ | ✗ | ✓ (catch-based) |
| Fisher Friend app [5] | ✗ (broadcast) | ✓ (9) | ✓ | ✗ | ✗ | partial | ✗ |
| ClimSight [11] | ✓ | ✗ | partial | ✗ (LLM-generated) | ✗ (document-level) | ✗ | ✗ |
| WildfireGPT [12] | ✓ | ✗ | partial | ✗ (LLM-generated) | ✗ (document-level) | ✗ | expert case studies |
| **Sagar Setu (proposed)** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓ (POD/FAR/CSI)** |

---

## 3. Research Gap

> **India has excellent marine data products and workable one-way delivery channels, but no
> published system lets a fisherman ask one question in his own language and receive a single
> operational decision — safety, fishing and boundary together — that is provably derived from
> those products rather than generated by a model.**

Six specific gaps follow from the review.

**G1 — Fragmentation.** Safety (SVAS), fishing zones (PFZ) and maritime boundaries are three
separate products with three interfaces and no shared query. No published work reasons
across all three for a single user question.

**G2 — Interaction mode.** All existing dissemination is broadcast: bulletins, SMS, map
portals, helplines. None accepts a free-form query carrying the vessel, heading, speed and
departure time that actually determine the answer.

**G3 — Language depth.** Existing products reach nine or ten languages as *translated
output*. With IndicTrans2 [14] covering 22 languages, the limiting factor is no longer
translation capability but the absence of a conversational marine system to attach it to.

**G4 — Verifiability.** ClimSight [11] and WildfireGPT [12] ground generation in retrieved
documents. Agent hallucination surveys [13] show that fabrication and tool bypass remain
open problems. No marine advisory system publishes a per-observation provenance ledger with
a mechanical post-generation check that deletes unsupported numbers.

**G5 — Structural safety separation.** No published marine advisory architecture *prevents*
the language model from making the go/no-go call. XCLIM-AI's deterministic-computation layer
[11] is the nearest published idea, and it computes climate indicators for analysts, not
operational safety verdicts for fishermen.

**G6 — Evaluation at the level of action.** Validation literature reports RMSE and scatter
index for wave height [1]. A fisherman does not act on RMSE; he acts on a verdict. Hit rate
and false-alarm ratio for the *verdict itself* are not reported anywhere in this domain.

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

These values are provisional starting points. Calibrating them against the INCOIS Boat
Safety Index parameter set [2] — which independently selects steepness, directional spread
and beam width — is an identified task, not a completed one.

### 4.4 Data sources

| Source | Provides | Access |
|---|---|---|
| INCOIS ERDDAP | SST, winds, currents, Argo profiles | Open REST / griddap |
| INCOIS PFZ | Potential Fishing Zone advisories, 12 sectors | Web product, scraped and cached |
| Open-Meteo Marine | Wave height/period/direction, swell, currents | Free, no key — the reliability floor |
| Copernicus Marine | Chlorophyll-a, physics reanalysis | Free account |
| NOAA CoastWatch | Chlorophyll-a fallback | Open |
| Marine Regions (VLIZ) | Indian EEZ, IMBL, boundary polygons | Static GeoJSON |
| IMD | Cyclone track, lightning, district warnings | **Pending access key** |

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
Scored with POD, FAR, CSI and a 3×3 confusion matrix [15].

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
| — | Calibrate thresholds against INCOIS SVAS criteria [2] | **Blocked** — criteria not published numerically |
| — | IMD API key for lightning and cyclone parameters | **Blocked** — requires institutional letter |
| — | Buoy observations to replace analysis as evaluation truth | **Blocked** — requires INCOIS/NIOT data access |

---

## References

[1] B. T. M. Nair, P. Sirisha, K. G. Sandhya, *et al.*, "Performance of the ocean state forecast system at Indian National Centre for Ocean Information Services," *Current Science*, vol. 105, no. 2, pp. 175–181, 2013.

[2] Indian National Centre for Ocean Information Services, "Small Vessel Advisory and Forecast Services (SVAS)," INCOIS Ocean State Forecast portal. [Online]. Available: https://incois.gov.in/portal/osf/SVA_overview.jsp

[3] A. N. Deshmukh, "Small Craft Advisory," ITCOocean training material, INCOIS, Hyderabad.

[4] V. N. Pillai and P. G. Nair, "Potential fishing zone (PFZ) advisories — Are they beneficial to the coastal fisherfolk? A case study along Kerala coast, South India," *Biological Forum*, vol. 2, no. 2, pp. 46–55, 2010.

[5] M. S. Swaminathan Research Foundation, "Fisher Friend Mobile Application," and INCOIS multilingual advisory dissemination services. [Online]. Available: https://incois.gov.in

[6] R. Lam, A. Sanchez-Gonzalez, M. Willson, *et al.*, "Learning skillful medium-range global weather forecasting," *Science*, vol. 382, no. 6677, pp. 1416–1421, 2023.

[7] K. Bi, L. Xie, H. Zhang, X. Chen, X. Gu, and Q. Tian, "Accurate medium-range global weather forecasting with 3D neural networks," *Nature*, vol. 619, pp. 533–538, 2023.

[8] S. Yao, J. Zhao, D. Yu, *et al.*, "ReAct: Synergizing reasoning and acting in language models," in *Proc. ICLR*, 2023.

[9] T. Schick, J. Dwivedi-Yu, R. Dessì, *et al.*, "Toolformer: Language models can teach themselves to use tools," in *Adv. Neural Inf. Process. Syst. (NeurIPS)*, vol. 36, 2023.

[10] P. Lewis, E. Perez, A. Piktus, *et al.*, "Retrieval-augmented generation for knowledge-intensive NLP tasks," in *Adv. Neural Inf. Process. Syst. (NeurIPS)*, vol. 33, pp. 9459–9474, 2020.

[11] I. Kuznetsov, A. A. Jost, D. Pantiukhin, B. Shapkin, T. Jung, and N. Koldunov, "Transforming climate services with LLMs and multi-source data integration," *npj Climate Action*, vol. 4, no. 1, art. 97, 2025. doi: 10.1038/s44168-025-00300-y

[12] Y. Xie, B. Jiang, T. Mallick, *et al.*, "A RAG-based multi-agent LLM system for natural hazard resilience and adaptation," arXiv:2504.17200, 2025.

[13] X. Lin, Y. Ning, J. Zhang, *et al.*, "LLM-based agents suffer from hallucinations: A survey of taxonomy, methods, and directions," arXiv:2509.18970, 2025.

[14] J. Gala, P. A. Chitale, R. AK, *et al.*, "IndicTrans2: Towards high-quality and accessible machine translation models for all 22 scheduled Indian languages," *Transactions on Machine Learning Research (TMLR)*, 2023. arXiv:2305.16307

[15] I. T. Jolliffe and D. B. Stephenson, *Forecast Verification: A Practitioner's Guide in Atmospheric Science*, 2nd ed. Chichester, UK: Wiley-Blackwell, 2012.
