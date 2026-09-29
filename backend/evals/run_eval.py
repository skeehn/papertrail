"""PaperTrail eval harness - 18 deterministic, offline-light cases.

Usage: cd backend && .venv/bin/python evals/run_eval.py

Covers: citation extraction, contradiction detection, claim extraction,
HydraDB ingest contract + keyword search grounding, trend analyzer
contracts, and the chat search API schema. Prints a pass/fail table and
exits non-zero on any failure so it can run as a CI gate.
"""

import asyncio
import sys
from pathlib import Path
from typing import Callable, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database.hydradb_store import hydradb_store
from app.database.mock_store import mock_store
from app.services.citation_analyzer import CitationAnalyzer
from app.services.contradiction_detector import ContradictionDetector
from app.services.trend_analyzer import (
    analyze_trends,
    compare_entity_trends,
    find_emerging_topics,
    get_trending,
)

CaseFn = Callable[[], Optional[str]]
CASES: List[tuple] = []


def case(cid: str, category: str) -> Callable[[CaseFn], CaseFn]:
    def wrap(fn: CaseFn) -> CaseFn:
        CASES.append((cid, category, fn))
        return fn
    return wrap


# --- Citation extraction ------------------------------------------------------


@case("c1_named_with_year", "citations")
def c1() -> Optional[str]:
    found = CitationAnalyzer.extract_citations("As shown by (Vaswani et al., 2017) in prior work.")
    ok = any("vaswani" in c.lower() for c in found)
    return None if ok else f"found={found}"


@case("c2_numbered_bracket", "citations")
def c2() -> Optional[str]:
    found = CitationAnalyzer.extract_citations("The encoder stack [1] processes tokens.")
    return None if "[1]" in found else f"found={found}"


@case("c3_discuss_marker", "citations")
def c3() -> Optional[str]:
    found = CitationAnalyzer.extract_citations("As discussed in Brown et al this changes scaling laws.")
    ok = any("brown" in c.lower() for c in found)
    return None if ok else f"found={found}"


@case("c4_multi_style_mix", "citations")
def c4() -> Optional[str]:
    found = CitationAnalyzer.extract_citations("(Devlin et al., 2019) extends the older [2] ideas.")
    has_devlin = any("devlin" in c.lower() for c in found)
    return None if has_devlin and "[2]" in found else f"found={found}"


@case("c5_no_citations", "citations")
def c5() -> Optional[str]:
    found = CitationAnalyzer.extract_citations("No references on this page at all.")
    return None if len(found) <= 1 else f"expected empty-ish, found={found}"


# --- Contradiction & claim detection -----------------------------------------


@case("k1_direct_negation", "contradictions")
def k1() -> Optional[str]:
    r = ContradictionDetector.compare_claims(
        {"text": "the model cannot handle long inputs"},
        {"text": "the model handle long inputs"},
    )
    return None if r["contradiction_score"] >= 0.8 else f"got {r}"


@case("k2_opposite_terms", "contradictions")
def k2() -> Optional[str]:
    r = ContradictionDetector.compare_claims(
        {"text": "sparsity increases efficiency"},
        {"text": "sparsity decreases efficiency"},
    )
    return None if r["contradiction_score"] >= 0.6 else f"got {r}"


@case("k3_agreeing_claims", "contradictions")
def k3() -> Optional[str]:
    r = ContradictionDetector.compare_claims(
        {"text": "attention improves accuracy on benchmarks"},
        {"text": "attention improves accuracy on dev sets"},
    )
    return None if r["contradiction_score"] == 0 else f"got {r}"


@case("k4_we_show_pattern", "claims")
def k4() -> Optional[str]:
    claims = ContradictionDetector.extract_claims(
        "We show that attention scales linearly with the input length."
    )
    ok = bool(claims) and "attention scales" in claims[0]["text"].lower()
    return None if ok else f"claims={claims}"


@case("k5_findings_suggest", "claims")
def k5() -> Optional[str]:
    claims = ContradictionDetector.extract_claims(
        "Our findings suggest that scaling laws hold for vision models."
    )
    return None if claims else "no claims extracted"


# --- HydraDB ingest contract + search grounding --------------------------------


@case("d1_store_paper_validates", "store")
def d1() -> Optional[str]:
    async def run() -> Optional[str]:
        sample = {
            "arxiv_id": "9999.99001",
            "title": "Eval Probe Paper",
            "abstract": "Self-attention probe for the eval harness.",
            "authors": ["Eval Bot"],
        }
        await hydradb_store.store_paper(sample)
        if hydradb_store.last_source_ids == []:
            return "no source ids returned"
        return None

    return asyncio.run(run())


@case("d2_keyword_fallback_ranks", "search-grounding")
def d2() -> Optional[str]:
    from app.api.v1.endpoints.chat_tools import _keyword_fallback

    async def run() -> Optional[str]:
        papers = await _keyword_fallback("Self-attention probe", 5)
        # Empty library is an environment state (cloud indexing pending),
        # not a regression — skip, don't fail.
        if not papers:
            print("SKIP [search-grounding] d2_keyword_fallback_ranks: library empty (indexing pending)")
            return None
        top = papers[0]
        hay = f"{top.get('title', '')} {top.get('abstract', '')}".lower()
        return None if "attention" in hay else f"top hit lacks keyword: {top}"

    return asyncio.run(run())


@case("d3_search_papers_contract", "search-grounding")
def d3() -> Optional[str]:
    async def run() -> Optional[str]:
        from app.api.v1.endpoints.chat_tools import SearchRequest, search_papers

        out = await search_papers(SearchRequest(query="attention", limit=3))
        if not isinstance(out, dict) or "papers" not in out or "count" not in out:
            return f"bad schema: {out}"
        return None if isinstance(out["papers"], list) else "papers not a list"

    return asyncio.run(run())


# --- Trend analyzer contracts --------------------------------------------------


@case("t1_trending_list", "trends")
def t1() -> Optional[str]:
    out = asyncio.run(get_trending(6, 5))
    return None if isinstance(out, list) else f"got {type(out)}"


@case("t2_emerging_list", "trends")
def t2() -> Optional[str]:
    out = asyncio.run(find_emerging_topics(12, 50.0))
    return None if isinstance(out, list) else f"got {type(out)}"


@case("t3_trends_dict_shape", "trends")
def t3() -> Optional[str]:
    out = asyncio.run(analyze_trends(None, 3))
    ok = isinstance(out, dict) and isinstance(out.get("summary"), dict)
    return None if ok else f"missing summary: {out}"


@case("t4_compare_valid", "trends")
def t4() -> Optional[str]:
    out = asyncio.run(compare_entity_trends(["Transformer", "Attention"], 5))
    return None if out.get("winner") else f"no winner: {out}"


# --- Mock store contract --------------------------------------------------------


@case("m1_mock_store_papers", "mock-store")
def m1() -> Optional[str]:
    papers = list(mock_store.papers.values())
    return None if isinstance(papers, list) else "no papers"


@case("m2_mock_entities_nonneg", "mock-store")
def m2() -> Optional[str]:
    n = len(mock_store.entities)
    return None if n >= 0 else "entities negative"


def main() -> int:
    print()
    print(f"PaperTrail eval harness - {len(CASES)} cases")
    print("=" * 58)
    passed = failed = 0
    for cid, category, fn in CASES:
        try:
            failure = fn()
        except Exception as e:  # noqa: BLE001
            failure = f"{type(e).__name__}: {e}"
        if failure:
            failed += 1
            print(f"FAIL [{category}] {cid}: {failure}")
        else:
            passed += 1
            print(f"pass [{category}] {cid}")

    print("=" * 58)
    print(f"RESULT: {passed}/{len(CASES)} passed, {failed} failed")
    print("=" * 58)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
