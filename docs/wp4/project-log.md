# FYP Project Log — Ong Chuan Hau — WP4: Constraint-aware Product Recommendation

## Baseline

- **Pinned commit (B0):** `9c093469eb1a9bbf3fb43bff677994ce8facd70e`
- Branch cut from: `main` (== `origin/main` HEAD)
- Date pinned: 28 Aug 2026
- Commit message: "Merge pull request #16 from Im-jn/feat/itinerary — Itinerary Planning mode with NeSy solver"
- Working branch: `feat/wp4-constraint-aware-product`

---

## B0 Baseline Failure Case #1 — 28 Aug 2026

Query: "recommend me a quiet mechanical keyboard under $120 for Mac"
Follow-up brand selection: Corsair
System: current MetaRec baseline (B0), commit `9c093469eb1a9bbf3fb43bff677994ce8facd70e`
LLM: openai/gpt-oss-20b via Groq

Constraints stated by query: budget <= $120, category = mechanical keyboard,
Mac-compatible, quiet.

Results returned: 9 items total.

**VIOLATIONS FOUND:**
1. Corsair K65 Plus Wireless RGB 75% — $129.99 — exceeds $120 budget (8.3% over)
2. Corsair K100 AIR Wireless RGB — $186.03 — exceeds $120 budget (55% over)
3. Corsair K55 CORE RGB — listed as "Membrane Wired Gaming Keyboard" —
   violates "mechanical" category constraint despite mechanical being
   explicitly requested

Non-violating items (for contrast): Corsair K70 CORE TKL ($89.99),
Corsair K70 CORE with Palmrest ($109.99), Corsair K65 Plus Renewed ($69.99)
— all within budget and correctly mechanical.

**RELEVANCE TO WP4:** direct, first-hand evidence of the exact failure
mode the proposal's acceptance criteria addresses — "zero hard-constraint
violations... never show something over budget." Current B0 ranker
(`_item_score` in `generic_graph.py`) sorts only by (rating, reviews_count,
popularity, title) with no constraint filtering at all, which explains why
category and price constraints are silently ignored.

**NEXT STEP:** use this exact query + result set as a labeled test case when
building the hard-constraint filter (Phase 1 of M2).

---

## Phase 0 — baseline leak harness — 30 Aug 2026

Built `MetaRec-backend/tests/wp4/` — a labeled-dataset harness that feeds a
hand-labeled candidate pool through the real graph
(`run_generic_domain_graph`, fake `amazon.product.search` adapter) and counts
how many hard-constraint-violating items survive to `result.items`.

- `constraints.py` — `HardConstraints` model + `violations(item, hc)` checker
  (price parse, category include/exclude, brand in/not-in, require/exclude
  terms). Reused as the Phase 1 filter core.
- `dataset.py` / `cases/*.json` — one case per query; each candidate carries
  `expect_violations` (human ground truth).
- `eval_constraints.py` — `python -m tests.wp4.eval_constraints` prints the
  leak report. `test_wp4_baseline.py` pins it: `test_harness_runs` (always on)
  + `test_no_hard_constraint_violations_surface` (`xfail(strict)`, the WP4
  acceptance target — flips to pass when Phase 1 lands).

`capture.py` — `python -m tests.wp4.capture "<query>" --pref k=v --out cases/X.json`
runs the query against the **live** SerpApi adapter and writes a case skeleton;
fill `hard_constraints` and label every `expect_violations` by hand.

**B0 numbers (dataset still growing):**

| case | kind | pool violators | surfaced (leak) | first violator rank |
|---|---|---|---|---|
| case_01_keyboard | transcribed | 3 | 3 (100%) | 3 — top 3 |
| case_02_keyboard_live | SerpApi | 3 | 3 (100%) | 4 |
| case_03_mouse | clean control | 0 | — | — |
| case_04_headphones | clean control | 0 | — | — |
| case_05_sony_headphones | SerpApi, brand+budget | 3 | 3 (100%) | 6 |
| **total** | | **9** | **9 (100%)** | — |

`_item_score` sorts by (rating, reviews, popularity, title), so a well-reviewed
over-budget item (K100 AIR $186; Logitech MX Mechanical $153 / 2.2k reviews;
Sony WH-1000XM5 $200) outranks compliant cheaper options. No filter anywhere =
**every violator present in the pool is surfaced.**

**Finding — when B0 leaks:** a *loose* single budget on a category with many
cheap options (mouse < $50, headphones < $100) returns 10 compliant items on
SerpApi relevance alone — 0 leak. Leak needs a **tight budget vs the category's
price band**, a **brand** filter, a **category Amazon's text search ignores**,
or a **compound** constraint. The dataset needs a majority of these.

**Finding — brand is unreliable:** SerpApi returns `brand` for some amazon
results and `null` for others in the same response. `constraints._brand()` only
trusts a real brand string (never the price-filled `subtitle`); `brand_in` is a
violation only when a *different* brand is positively readable. Hand-label brand
cases.

**Findings for Phase 1:**
- `_amazon_product_search_adapter` (tool_registry.py) captures only
  `title, brand, link, rating, reviews, price, thumbnail` — **no category
  field**. Category constraints can only be enforced from the title today;
  either add a category/`type` passthrough or accept title-substring matching.
- SerpApi amazon frequently returns `brand: null`; don't rely on it for the
  brand constraint — fall back to title.
- `price` is a display string (`"$129.99"`, sometimes a `"$x - $y"` range) —
  needs parsing; there is no `extracted_price` passthrough.

**NEXT:** grow the dataset to ~15 cases across budget / category / brand-include
/ brand-exclude / compatibility / attribute, then re-baseline before writing the
filter.
