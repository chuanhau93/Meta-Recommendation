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
