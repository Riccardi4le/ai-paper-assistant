"""Retrieval evaluation for the FAISS index.

Measures recall@k and MRR on three query styles derived from each indexed
paper:
  - title-as-query          (sanity check)
  - first 100 chars of abstract  (realistic)
  - last sentence of abstract    (harder: the tail of the chunk)

No labeled data required: the "gold" answer is the paper the query was
derived from. A healthy retriever should find it in the top results.

Run:
    python -m evals.retrieval_eval
    python -m evals.retrieval_eval --limit 50 --k 5

Requires the full runtime (torch, sentence-transformers, faiss) because it
imports ``api.main``.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from statistics import mean

# Importing api.main initializes the embedder and loads/creates the FAISS
# index at import time, so evals run against the live index.
from api import main as api_main  # noqa: E402


def _pick_queries(title: str, abstract: str) -> dict[str, str]:
    title = (title or "").strip()
    abstract = (abstract or "").strip()
    first_100 = abstract[:100] if abstract else ""
    # Last sentence = last segment after the final period (fallback: last 100 chars)
    last_sent = ""
    if abstract:
        parts = [p.strip() for p in abstract.split(".") if p.strip()]
        last_sent = parts[-1] if parts else abstract[-100:]
    return {
        "title": title,
        "abstract_head": first_100,
        "abstract_tail": last_sent,
    }


def _rank_of(target_paper_id: int, ranked_ids: list[int]) -> int | None:
    for i, pid in enumerate(ranked_ids, start=1):
        if pid == target_paper_id:
            return i
    return None


def evaluate(db_path: str, limit: int, k: int) -> dict[str, dict[str, float]]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, title, summary FROM papers ORDER BY id LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        print("Nessun paper nel DB. Esegui un ingest prima.")
        sys.exit(1)

    strategies = ["title", "abstract_head", "abstract_tail"]
    results: dict[str, dict[str, list[float]]] = {
        s: {"recall@1": [], f"recall@{k}": [], "reciprocal_rank": []} for s in strategies
    }

    for pid, title, summary in rows:
        queries = _pick_queries(title, summary)
        for strat in strategies:
            q = queries[strat]
            if not q:
                continue
            hits = api_main.semantic_search_papers(q, limit=max(k, 10))
            ranked_ids = [h["id"] for h in hits]
            rank = _rank_of(pid, ranked_ids)
            results[strat]["recall@1"].append(1.0 if rank == 1 else 0.0)
            results[strat][f"recall@{k}"].append(1.0 if rank and rank <= k else 0.0)
            results[strat]["reciprocal_rank"].append(1.0 / rank if rank else 0.0)

    summary: dict[str, dict[str, float]] = {}
    for strat, metrics in results.items():
        summary[strat] = {m: (mean(v) if v else 0.0) for m, v in metrics.items()}
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="FAISS retrieval recall@k eval")
    parser.add_argument("--limit", type=int, default=50, help="max papers to evaluate")
    parser.add_argument("--k", type=int, default=5, help="top-k cutoff")
    parser.add_argument("--db", type=str, default=api_main.DB_PATH, help="SQLite path")
    args = parser.parse_args()

    print(f"Index size: {int(api_main.faiss_index.ntotal)} chunks")
    print(f"Evaluating up to {args.limit} papers, k={args.k}\n")

    summary = evaluate(args.db, args.limit, args.k)

    width = max(len(s) for s in summary) + 2
    header = f"{'strategy':<{width}} {'recall@1':>10} {'recall@'+str(args.k):>10} {'MRR':>10}"
    print(header)
    print("-" * len(header))
    for strat, m in summary.items():
        print(
            f"{strat:<{width}} "
            f"{m['recall@1']:>10.3f} "
            f"{m[f'recall@{args.k}']:>10.3f} "
            f"{m['reciprocal_rank']:>10.3f}"
        )


if __name__ == "__main__":
    main()
