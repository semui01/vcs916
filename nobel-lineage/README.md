# Nobel Physics Lineages

A graded, sourced graph of how Nobel Prize in Physics contributions (1901–2026) build on earlier Physics prizes. It is a **Nobel-visible lineage**: it shows only influence that passes through Nobel-recognised work. It is not a complete history of scientific influence.

The interactive report is `output/nobel-lineages.html`.

## Files

| Path | What it is |
|---|---|
| `data/prizes.py` | All 120 prize years: 146 contributions with laureates, official motivation, field tag, kind (theory / experiment / instrument) and year of the key work. Also 5 laureate works the Nobel citation did not cover (e.g. Pauli's neutrino). |
| `data/edges.py` | 165 curated links. Each has a relationship type, confidence, scope (direct vs ancestry), a one-line claim, sources, and whether it was re-checked in this session. |
| `scripts/analyze.py` | Validates the graph (no link may point backwards in work time, no cycles) and computes every Step 6 statistic. Writes `output/results.json`, `nodes.csv`, `edges.csv`, `lineages.csv`. |
| `scripts/build_report.py` | Embeds the results into `scripts/report_template.html` → `output/nobel-lineages.html`. |
| `scripts/verify_against_api.py` | Diffs every motivation and laureate list against `api.nobelprize.org`. **Not yet run** (see provenance). |

Reproduce: `python3 -I scripts/analyze.py && python3 -I scripts/build_report.py`. Uses the standard library only.

## Method

- **Unit.** One node per prize citation. Years with two separate citations get `a`/`b` (e.g. 1936a Hess, 1936b Anderson). The 2003 and 2016 citations are split by laureate because their work spans decades; each still counts as one prize.
- **Direction.** Links run from the earlier *work* to the later *work*, not by award date. The script refuses any directed link that runs backwards in work time.
- **Types** (from the brief): theoretical foundation (TF), experimental confirmation (EC), instrumental/technological foundation (IT), new application or extension (AE), direct discovery follow-up (DF), independent parallel development (PD). PD links are excluded from paths and timing statistics.
- **Confidence → evidence class.** H = documented (Nobel material or primary source states it). M = strong inference. L = speculative. Statistics use H+M directed links. Rankings never count L or PD links.
- **Lineages.** 17 subject groups. Each group's *spine* is the highest-scoring path inside it (1 per H link, 0.5 per M link), computed by the script. Groups are ranked by spine score.

## Headline results

- **Longest fully documented chain: 7 prizes.** van der Waals 1910 → Kamerlingh Onnes 1913 → BCS 1972 → Nambu 2008 → Englert & Higgs 2013 → Glashow, Salam & Weinberg 1979 → Rubbia & van der Meer 1984 (or → 't Hooft & Veltman 1999). The work spans 1873–1983.
- **Longest span with a single subject:** superconductivity to quantum circuits. van der Waals' 1873 equation of state leads to Clarke, Devoret & Martinis' 1985 experiment: 112 years of work and 115 years of awards (1910–2025).
- **Timing (150 directed H+M links).** Median work gap 15 years (mean 20.4). Median award gap 17 years. Theory → experimental confirmation: median 18 years. Discovery → explaining theory: median 4 years. Technology → discovery made with it: median 18 years.
- **Recognition lag.** Median work-to-award time grew from 10 years (prizes 1901–25) to 34 years (2001–26). Theory prizes wait a median 27 years, experimental discoveries 11.
- **Award inversions.** 14 links point from a later prize to an earlier one. The largest: Englert & Higgs (2013) were honoured 34 years after the electroweak theory (1979) that used their mechanism.
- **Most-reused prize:** the 1964 maser–laser prize feeds 9 later prizes.
- **Most laureates behind one discovery.**
  - Direct parents: the 2015 oscillation prize, with 5 parent prizes and 10 laureates.
  - Documented links only, all generations: 1984 and 1999, each with 11 laureates.
  - Including inferred links: 2004, with 44 laureates. That figure is inflated by chained "ancestry" links.
- **Densest areas.**
  - Cosmic rays & neutrinos has the most links per prize (3.4), but it was searched hardest because the brief focused on it.
  - Quantum foundations (1.69) and particle physics (1.57, every prize linked) come next.
- **Isolated:** 15 of 146 contributions (10%) have no Nobel-visible link.

## Neutrino lineage (worked example)

| Proposed arrow | Grade | Note |
|---|---|---|
| Pauli → Reines (1995) | Documented | Outside the Nobel-visible graph: Pauli's 1945 prize was for the exclusion principle |
| Reines → Lederman/Schwartz/Steinberger (1988) | Strong inference | Follows in the science (1956 → 1962); prizes came in reverse order |
| 1988 → Davis/Koshiba (2002) | Speculative | No material dependency found |
| Davis/Koshiba → Kajita/McDonald (2015) | Documented | 2015 scientific background |
| Kajita/McDonald → Halzen (2026) | Speculative | IceCube studies oscillations, but its discovery did not depend on them |

Stronger inputs the proposed chain leaves out:

- Bethe 1967 → Davis (documented).
- Cherenkov 1958 → Kamiokande, Super-K/SNO and IceCube (documented).
- Koshiba → Halzen, neutrino astronomy (strong inference).
- Hess 1936 → Halzen, the cosmic-ray-origin science case (strong inference).
- Reines → Halzen via DUMAND (strong inference).

## Provenance and limitations

- **Network access.** `nobelprize.org`, `api.nobelprize.org` and Wikipedia were blocked by the build environment's network policy. Only web search was available. Motivations and Nobel document URLs come from the Nobel record without being re-downloaded. Run `verify_against_api.py` before quoting motivations verbatim.
- **What was re-checked.** 22 of 165 links were re-checked by web search on 2026-10-06, the day the 2026 prize was announced. The rest cite standard Nobel documents (ceremony speeches, scientific backgrounds) or primary sources from prior knowledge.
- **Generated URLs.** Nobel document URLs follow nobelprize.org's path pattern (`/prizes/physics/<year>/advanced-information/`, `/ceremony-speech/`, `/summary/`). They were not fetched.
- **Selectivity.** Nobel prizes are selective: at most three laureates, no posthumous awards, and Physics only. Chemistry links (Rutherford, Hahn, the Joliot-Curies) are invisible. A missing arrow means "not Nobel-visible", not "no influence".
- **Curator bias.** One analyst chose the links, and topics named in the brief were searched more deeply.
