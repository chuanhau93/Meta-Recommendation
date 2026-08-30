"""WP4 Phase 0 baseline, pinned as tests.

- ``test_harness_runs`` keeps the eval wired up as the dataset grows.
- ``test_no_hard_constraint_violations_surface`` is the WP4 acceptance target.
  It is ``xfail(strict)`` today because B0 has no constraint filter; when the
  Phase 1 filter lands this turns into an unexpected pass and the marker must be
  removed. That flip is the signal Phase 1 is done.
"""

import pytest

from tests.wp4.eval_constraints import evaluate


@pytest.mark.backend_unit
def test_harness_runs():
    report = evaluate()
    assert report.cases, "no cases evaluated"
    assert report.total_pool_violators > 0, "dataset has no labeled violators to detect"
    for case in report.cases:
        assert case.surfaced_titles, f"{case.id}: graph surfaced nothing"
        assert not case.label_checker_disagreements, (
            f"{case.id}: constraints.violations() disagrees with human labels:\n  "
            + "\n  ".join(case.label_checker_disagreements)
        )


@pytest.mark.backend_unit
@pytest.mark.xfail(strict=True, reason="B0 has no hard-constraint filter; Phase 1 target")
def test_no_hard_constraint_violations_surface():
    report = evaluate()
    assert report.total_leaked == 0, (
        f"{report.total_leaked}/{report.total_pool_violators} violating items still surfaced\n\n"
        + report.render()
    )
