"""Command-line interface: ingest | search | ask | validate | stats."""
from __future__ import annotations

import argparse
import sys
import textwrap
from collections import Counter
from pathlib import Path

from .docs import VALID_CATEGORIES, VALID_REGIONS, chunk_document, load_documents, validate_meta
from .index import DEFAULT_EMBED_MODEL, Index

ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE = ROOT / "knowledge"
INDEX_DIR = ROOT / "index"


def _print_hits(hits, full: bool) -> None:
    if not hits:
        print("No matches. Try other words, or drop --category/--region filters.")
        return
    for n, h in enumerate(hits, 1):
        c = h.chunk
        flag = "  [HIGH-RISK TOPIC]" if c.risk == "high" else ""
        print(f"\n[{n}] {c.title}" + (f" > {c.section}" if c.section else "") + flag)
        print(f"    {c.path}  | regions: {', '.join(c.regions)} | score {h.score:.3f}")
        body = c.text if full else textwrap.shorten(c.text.replace("\n", " "), 400)
        print(textwrap.indent(body, "    "))
        if c.warning:
            print(f"    !! CRITICAL WARNING: {c.warning}")


def cmd_ingest(args) -> int:
    docs = load_documents(Path(args.knowledge))
    bad = {d.path: p for d in docs if (p := validate_meta(d.meta))}
    for path, problems in bad.items():
        print(f"WARN {path}: {'; '.join(problems)}", file=sys.stderr)
    chunks = [c for d in docs for c in chunk_document(d, max_chars=args.max_chars)]
    idx = Index(chunks)
    if args.embed:
        try:
            idx.build_embeddings(args.embed_model)
        except ImportError:
            print("sentence-transformers not installed; building BM25-only index.", file=sys.stderr)
    idx.save(Path(args.index))
    mode = "hybrid (BM25 + embeddings)" if idx.embeddings is not None else "BM25"
    print(f"Indexed {len(docs)} documents -> {len(chunks)} chunks [{mode}] in {args.index}")
    return 0


def cmd_search(args) -> int:
    idx = Index.load(Path(args.index))
    _print_hits(idx.search(args.query, k=args.k, category=args.category, region=args.region), args.full)
    return 0


def cmd_ask(args) -> int:
    from .llm import ask

    idx = Index.load(Path(args.index))

    def answer(q: str) -> None:
        hits = idx.search(q, k=args.k, category=args.category, region=args.region)
        if not hits:
            print("Nothing in the knowledge base matches that question.")
            return
        try:
            print("\n" + ask(q, hits) + "\n")
        except RuntimeError as e:
            print(f"(LLM unavailable: {e})\nShowing raw references instead:")
            _print_hits(hits, full=True)
            return
        print("Sources:")
        for n, h in enumerate(hits, 1):
            print(f"  [{n}] {h.chunk.path} — {h.chunk.section or h.chunk.title}")

    if args.question:
        answer(" ".join(args.question))
        return 0
    print("Survival RAG — type a question, or 'quit'.")
    while True:
        try:
            q = input("\n? ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in {"q", "quit", "exit"}:
            break
        if q:
            answer(q)
    return 0


def cmd_validate(args) -> int:
    docs = load_documents(Path(args.knowledge))
    failures = 0
    for d in docs:
        problems = validate_meta(d.meta)
        if problems:
            failures += 1
            print(f"FAIL {d.path}: {'; '.join(problems)}")
    print(f"{len(docs) - failures}/{len(docs)} documents valid")
    return 1 if failures else 0


def cmd_stats(args) -> int:
    idx = Index.load(Path(args.index))
    by_cat = Counter(c.category for c in idx.chunks)
    by_region = Counter(r for c in idx.chunks for r in c.regions)
    docs = {c.path for c in idx.chunks}
    print(f"{len(docs)} documents, {len(idx.chunks)} chunks, embeddings: {idx.embed_model_name or 'none'}")
    print("\nChunks by category:")
    for k, v in by_cat.most_common():
        print(f"  {k:<16}{v}")
    print("\nChunks by region:")
    for k, v in by_region.most_common():
        print(f"  {k:<18}{v}")
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # Windows consoles default to cp1252
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    p = argparse.ArgumentParser(prog="survival_rag", description="Offline survival knowledge RAG")
    p.add_argument("--knowledge", default=str(KNOWLEDGE), help="knowledge base directory")
    p.add_argument("--index", default=str(INDEX_DIR), help="index directory")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("ingest", help="build the index from knowledge/")
    s.add_argument("--embed", action="store_true", help="also build dense embeddings")
    s.add_argument("--embed-model", default=DEFAULT_EMBED_MODEL)
    s.add_argument("--max-chars", type=int, default=1200)
    s.set_defaults(func=cmd_ingest)

    def add_filters(sp):
        sp.add_argument("-k", type=int, default=5, help="number of results")
        sp.add_argument("--category", choices=sorted(VALID_CATEGORIES))
        sp.add_argument("--region", choices=sorted(VALID_REGIONS - {"all"}))

    s = sub.add_parser("search", help="retrieve matching passages (no LLM needed)")
    s.add_argument("query")
    s.add_argument("--full", action="store_true", help="print full chunk text")
    add_filters(s)
    s.set_defaults(func=cmd_search)

    s = sub.add_parser("ask", help="answer with a local LLM (interactive if no question)")
    s.add_argument("question", nargs="*")
    add_filters(s)
    s.set_defaults(func=cmd_ask)

    s = sub.add_parser("validate", help="check frontmatter of every knowledge file")
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser("stats", help="summarize the built index")
    s.set_defaults(func=cmd_stats)

    args = p.parse_args(argv)
    return args.func(args)
