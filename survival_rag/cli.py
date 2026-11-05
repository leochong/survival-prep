"""Command-line interface: ingest | search | ask | validate | stats."""
from __future__ import annotations

import argparse
import sys
import textwrap
from collections import Counter
from pathlib import Path

from .docs import VALID_CATEGORIES, VALID_REGIONS, chunk_document, load_documents, validate_meta
from .images import image_chunks, load_images, validate_images
from .index import DEFAULT_EMBED_MODEL, Index

ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE = ROOT / "knowledge"
IMAGES = ROOT / "images"
INDEX_DIR = ROOT / "index"


def _image_line(iid: str, images: dict) -> str:
    e = images.get(iid)
    if not e:
        return f"image: {iid} (not in manifest)"
    return f"image: images/{e['file']} — {e['title']} ({e['license']}, {e['author']})"


def _print_hits(hits, full: bool, images: dict | None = None) -> None:
    images = images or {}
    if not hits:
        print("No matches. Try other words, or drop --category/--region filters.")
        return
    for n, h in enumerate(hits, 1):
        c = h.chunk
        flag = "  [HIGH-RISK TOPIC]" if c.risk == "high" else ""
        kind = "  [IMAGE]" if c.id.startswith("img-") else ""
        print(f"\n[{n}] {c.title}" + (f" > {c.section}" if c.section else "") + kind + flag)
        print(f"    {c.path}  | regions: {', '.join(c.regions)} | score {h.score:.3f}")
        body = c.text if full else textwrap.shorten(c.text.replace("\n", " "), 400)
        print(textwrap.indent(body, "    "))
        for iid in c.images:
            print(f"    {_image_line(iid, images)}")
        if c.warning:
            print(f"    !! CRITICAL WARNING: {c.warning}")


def _build_chunks(args):
    docs = load_documents(Path(args.knowledge))
    chunks = [c for d in docs for c in chunk_document(d, max_chars=args.max_chars)]
    images = load_images(Path(args.images))
    return docs, chunks, images, image_chunks(images, chunks)


def cmd_ingest(args) -> int:
    docs, chunks, images, img_chunks = _build_chunks(args)
    for d in docs:
        if p := validate_meta(d.meta):
            print(f"WARN {d.path}: {'; '.join(p)}", file=sys.stderr)
    for p in validate_images(Path(args.images), Path(args.knowledge), docs):
        print(f"WARN images: {p}", file=sys.stderr)
    idx = Index(chunks + img_chunks)
    idx.images = images
    if args.embed:
        try:
            idx.build_embeddings(args.embed_model)
        except ImportError:
            print("sentence-transformers not installed; building BM25-only index.", file=sys.stderr)
    idx.save(Path(args.index))
    mode = "hybrid (BM25 + embeddings)" if idx.embeddings is not None else "BM25"
    print(f"Indexed {len(docs)} documents + {len(images)} images -> "
          f"{len(idx.chunks)} chunks [{mode}] in {args.index}")
    return 0


def _search(idx: Index, query: str, args):
    hits = idx.search(query, k=args.k * 4 if args.images_only else args.k,
                      category=args.category, region=args.region)
    if args.images_only:
        hits = [h for h in hits if h.chunk.images][: args.k]
    return hits


def cmd_search(args) -> int:
    idx = Index.load(Path(args.index))
    _print_hits(_search(idx, args.query, args), args.full, idx.images)
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
            _print_hits(hits, full=True, images=idx.images)
            return
        print("Sources:")
        for n, h in enumerate(hits, 1):
            print(f"  [{n}] {h.chunk.path} — {h.chunk.section or h.chunk.title}")
        shown = list(dict.fromkeys(i for h in hits for i in h.chunk.images))
        if shown:
            print("Images:")
            for iid in shown:
                print(f"  {_image_line(iid, idx.images)}")

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
    image_problems = validate_images(Path(args.images), Path(args.knowledge), docs)
    for p in image_problems:
        print(f"FAIL images: {p}")
    n_images = len(load_images(Path(args.images)))
    print(f"{n_images} images, {len(image_problems)} image problems")
    return 1 if failures or image_problems else 0


def cmd_stats(args) -> int:
    idx = Index.load(Path(args.index))
    by_cat = Counter(c.category for c in idx.chunks)
    by_region = Counter(r for c in idx.chunks for r in c.regions)
    docs = {c.path for c in idx.chunks if not c.id.startswith("img-")}
    print(f"{len(docs)} documents, {len(idx.images)} images, {len(idx.chunks)} chunks, "
          f"embeddings: {idx.embed_model_name or 'none'}")
    print("\nChunks by category:")
    for k, v in by_cat.most_common():
        print(f"  {k:<16}{v}")
    print("\nChunks by region:")
    for k, v in by_region.most_common():
        print(f"  {k:<18}{v}")
    if idx.images:
        img_root = Path(args.images)
        size = sum((img_root / e["file"]).stat().st_size
                   for e in idx.images.values() if (img_root / e["file"]).is_file())
        print(f"\nImages by category ({size / 1_048_576:.1f} MB on disk):")
        for k, v in Counter(e.get("category", "?") for e in idx.images.values()).most_common():
            print(f"  {k:<16}{v}")
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # Windows consoles default to cp1252
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    p = argparse.ArgumentParser(prog="survival_rag", description="Offline survival knowledge RAG")
    p.add_argument("--knowledge", default=str(KNOWLEDGE), help="knowledge base directory")
    p.add_argument("--images", default=str(IMAGES), help="image directory (with manifest.json)")
    p.add_argument("--index", default=str(INDEX_DIR), help="index directory")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("ingest", help="build the index from knowledge/ and images/")
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
    s.add_argument("--images-only", action="store_true", help="only hits that have images")
    add_filters(s)
    s.set_defaults(func=cmd_search)

    s = sub.add_parser("ask", help="answer with a local LLM (interactive if no question)")
    s.add_argument("question", nargs="*")
    add_filters(s)
    s.set_defaults(func=cmd_ask)

    s = sub.add_parser("validate", help="check frontmatter, image manifest, and image links")
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser("stats", help="summarize the built index")
    s.set_defaults(func=cmd_stats)

    args = p.parse_args(argv)
    return args.func(args)
