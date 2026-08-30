"""Phase 0 harness: run every WP4 case through the live graph and measure how
often hard-constraint-violating products are surfaced.

Run standalone for the report::

    python -m tests.wp4.eval_constraints

or import ``evaluate()`` from the pytest baseline test.

Method: a fake ``amazon.product.search`` adapter returns the case's hand-labeled
candidate pool, so the graph's real normalize/dedupe/rank path decides what the
user would see. We then score the surfaced items against the human labels
(``expect_violations``) and, independently, against ``constraints.violations()``
so a drift between the two shows up.
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

_BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

from langgraph_metarec.graphs.generic_graph import (  # noqa: E402
    GenericGraphAdapters,
    run_generic_domain_graph,
)
from langgraph_metarec.tool_registry import ToolRegistry, ToolSpec  # noqa: E402

from tests.wp4.constraints import violations  # noqa: E402
from tests.wp4.dataset import Case, load_cases  # noqa: E402

PRODUCT_TAGS = ["#thing", "#product", "#shopping"]


def _registry_returning(pool: List[Dict[str, Any]]) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="amazon.product.search",
            domain="product",
            tags={"#thing", "#product", "#shopping"},
            input_schema={"type": "object"},
            output_schema={"type": "array"},
            adapter=lambda params, _pool=pool: list(_pool),
        )
    )
    return registry


@dataclass
class CaseResult:
    id: str
    surfaced_titles: List[str]
    pool_violators: int
    surfaced_violators: int          # by human label
    checker_violators: int           # by constraints.violations()
    first_violator_rank: Optional[int]
    label_checker_disagreements: List[str] = field(default_factory=list)

    @property
    def leaked(self) -> int:
        return self.surfaced_violators

    @property
    def top3_violation(self) -> bool:
        return self.first_violator_rank is not None and self.first_violator_rank <= 3


async def _run_case(case: Case) -> CaseResult:
    result = await run_generic_domain_graph(
        query=case.query,
        domain="product",
        preferences=case.preferences,
        tool_tags=PRODUCT_TAGS,
        adapters=GenericGraphAdapters(tool_registry=_registry_returning(case.pool)),
    )
    labels = case.labels_by_title()
    surfaced_titles = [it.get("title", "") for it in result.items]

    surfaced_violators = 0
    checker_violators = 0
    first_violator_rank: Optional[int] = None
    disagreements: List[str] = []

    for rank, item in enumerate(result.items, start=1):
        title = item.get("title", "")
        human = labels.get(title, [])
        checker = violations(item, case.hard_constraints)
        if human:
            surfaced_violators += 1
            if first_violator_rank is None:
                first_violator_rank = rank
        if checker:
            checker_violators += 1
        if bool(human) != bool(checker):
            disagreements.append(f"{title!r}: label={human} checker={checker}")

    return CaseResult(
        id=case.id,
        surfaced_titles=surfaced_titles,
        pool_violators=len(case.pool_violator_titles),
        surfaced_violators=surfaced_violators,
        checker_violators=checker_violators,
        first_violator_rank=first_violator_rank,
        label_checker_disagreements=disagreements,
    )


@dataclass
class Report:
    cases: List[CaseResult]

    @property
    def total_pool_violators(self) -> int:
        return sum(c.pool_violators for c in self.cases)

    @property
    def total_leaked(self) -> int:
        return sum(c.leaked for c in self.cases)

    @property
    def leak_rate(self) -> float:
        return self.total_leaked / self.total_pool_violators if self.total_pool_violators else 0.0

    @property
    def cases_with_top3_violation(self) -> int:
        return sum(1 for c in self.cases if c.top3_violation)

    def render(self) -> str:
        width = 63
        lines = [
            "WP4 Phase 0 - baseline hard-constraint leak report",
            "=" * width,
            f"{'case':<27}{'pool_viol':>10}{'leaked':>8}{'first_rank':>12}{'top3':>6}",
            "-" * width,
        ]
        for c in self.cases:
            lines.append(
                f"{c.id:<27}{c.pool_violators:>10}{c.leaked:>8}"
                f"{(c.first_violator_rank if c.first_violator_rank else '-'):>12}"
                f"{('YES' if c.top3_violation else '-'):>6}"
            )
        lines += [
            "-" * width,
            f"{'TOTAL':<27}{self.total_pool_violators:>10}{self.total_leaked:>8}",
            "",
            f"leak rate (violating items surfaced / present): {self.leak_rate:.0%}",
            f"cases with a violator in the top 3:             {self.cases_with_top3_violation}/{len(self.cases)}",
        ]
        drift = [d for c in self.cases for d in c.label_checker_disagreements]
        if drift:
            lines += ["", "label vs checker disagreements (tighten constraints.violations or the labels):"]
            lines += [f"  - {d}" for d in drift]
        return "\n".join(lines)


def evaluate() -> Report:
    cases = load_cases()
    results = [asyncio.run(_run_case(c)) for c in cases]
    return Report(cases=results)


if __name__ == "__main__":
    print(evaluate().render())
