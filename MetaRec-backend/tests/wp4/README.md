# WP4 — Constraint-aware Product Recommendation: eval harness

Measures how often the pipeline surfaces **product** results that violate a hard
constraint stated in the query (budget ceiling, category, brand, compatibility).

## Layout

| file | role |
|---|---|
| `constraints.py` | `HardConstraints` model + `violations(item, hc)` checker. Phase 1's filter is built on this. |
| `cases/*.json` | one query per file; each candidate is hand-labeled with `expect_violations`. |
| `dataset.py` | loads the cases. |
| `eval_constraints.py` | runs every case through the real graph with a fake search adapter, prints the leak report. |
| `test_wp4_baseline.py` | pins the harness + the `xfail` acceptance target. |

## Run

```bash
# from MetaRec-backend/, with the venv active
python -m tests.wp4.eval_constraints        # printed leak report
python -m pytest tests/wp4/ -q              # the pinned tests
```

## Adding a case

Copy `cases/case_01_keyboard.json`. Candidate dicts must match the
`amazon.product.search` adapter output (`title, brand, price, rating, reviews,
link, thumbnail, source`). Set `expect_violations` on each candidate to the
constraint keys a human judges it to break (`[]` = compliant). Keep
`hard_constraints` and the labels consistent — `test_harness_runs` fails on
drift between the labels and `constraints.violations()`.

Prefer real captures: run the query against the live system, paste the returned
items, label them. Synthetic pools are fine for coverage but note it in `notes`.

## The acceptance target

`test_no_hard_constraint_violations_surface` is `xfail(strict=True)` today. When
the Phase 1 filter makes it pass, that's an *unexpected* pass — remove the
marker. That flip is the definition of Phase 1 being done.
