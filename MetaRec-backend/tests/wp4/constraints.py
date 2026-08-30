"""Hard-constraint model + checker for product recommendations.

Phase 0 uses this only to *score* baseline output (how many violating items get
surfaced). Phase 1 will reuse `violations()` as the core of the filter step in
`generic_graph.normalize_and_rank`, so keep it dependency-free and deterministic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Price parsing
# ---------------------------------------------------------------------------

_PRICE_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def parse_price(value: Any) -> Optional[float]:
    """Best-effort numeric price from a SerpApi/Amazon `price` field.

    Handles ``"$129.99"``, ``"1,299.00"``, ``"SGD 45"``, and ranges like
    ``"$10.99 - $20.99"`` (a range means variants; we take the LOW end, since a
    buyable variant under budget makes the listing satisfiable).
    Returns None when no number is present.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    matches = _PRICE_NUM.findall(str(value))
    if not matches:
        return None
    numbers = [float(m.replace(",", "")) for m in matches]
    return min(numbers)


# ---------------------------------------------------------------------------
# Constraint model
# ---------------------------------------------------------------------------


@dataclass
class HardConstraints:
    """Everything a product result must satisfy to be shown at all.

    A constraint is inert when left at its default, so a case only sets the
    fields its query actually stated.
    """

    budget_max: Optional[float] = None
    currency: Optional[str] = None
    # Item is a category violation unless its text matches at least one of these.
    category_terms: List[str] = field(default_factory=list)
    # Item is a category violation if its text matches any of these.
    category_exclude_terms: List[str] = field(default_factory=list)
    brand_in: List[str] = field(default_factory=list)
    brand_not_in: List[str] = field(default_factory=list)
    # Every term must appear in the item text (compatibility, e.g. "mac").
    require_terms: List[str] = field(default_factory=list)
    # No term may appear in the item text.
    exclude_terms: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HardConstraints":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def _item_text(item: Dict[str, Any]) -> str:
    parts = [
        item.get("title"),
        item.get("subtitle"),
        item.get("description"),
        " ".join(str(t) for t in (item.get("tags") or [])),
    ]
    raw = item.get("raw")
    if isinstance(raw, dict):
        parts.extend(str(raw.get(k) or "") for k in ("title", "brand", "category", "type"))
    return " ".join(p for p in parts if p).casefold()


def _brand(item: Dict[str, Any]) -> str:
    """Known brand string, casefolded, or "" when the source didn't give one.

    Deliberately does NOT fall back to `subtitle` — the amazon adapter fills
    subtitle with the price when brand is missing, which would poison the check.
    """
    raw = item.get("raw") if isinstance(item.get("raw"), dict) else {}
    brand = raw.get("brand")
    if not brand and isinstance(item.get("subtitle"), str) and not _PRICE_NUM.search(item["subtitle"]):
        brand = item["subtitle"]
    return str(brand or "").strip().casefold()


def violations(item: Dict[str, Any], hc: HardConstraints) -> List[str]:
    """Return the list of constraint keys `item` violates (empty == compliant)."""
    out: List[str] = []
    text = _item_text(item)

    if hc.budget_max is not None:
        price = parse_price(item.get("raw", {}).get("price") if isinstance(item.get("raw"), dict) else None)
        if price is None:
            price = parse_price(item.get("subtitle"))
        if price is not None and price > hc.budget_max:
            out.append("budget")

    if hc.category_terms and not any(term.casefold() in text for term in hc.category_terms):
        out.append("category")
    if any(term.casefold() in text for term in hc.category_exclude_terms):
        out.append("category")

    if hc.brand_in:
        brand = _brand(item)
        # Only a violation when we can positively read a *different* brand.
        # Unknown brand -> benefit of the doubt (title may still name it).
        if brand and not any(
            b.casefold() in brand or b.casefold() in text for b in hc.brand_in
        ):
            out.append("brand")
    if hc.brand_not_in:
        brand = _brand(item)
        if any(b.casefold() in brand or b.casefold() in text for b in hc.brand_not_in):
            out.append("brand")

    for term in hc.require_terms:
        if term.casefold() not in text:
            out.append("compat")
            break
    for term in hc.exclude_terms:
        if term.casefold() in text:
            out.append("exclude")
            break

    return list(dict.fromkeys(out))
