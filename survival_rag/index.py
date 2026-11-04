"""Hybrid retrieval index: pure-Python BM25 (always) + optional dense embeddings.

BM25 needs nothing beyond the standard library, so search works on any machine
with Python 3.9+. If `sentence-transformers` and `numpy` are installed, `ingest
--embed` adds a semantic index and results are merged with reciprocal-rank fusion.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .docs import Chunk

STOPWORDS = set(
    """a an and are as at be but by can do does for from has have how i if in into is it
    its me my no not of on or our so than that the their then there these they this to
    too was we what when where which who why will with you your should would could""".split()
)

DEFAULT_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


_SUFFIXES = (  # tiny suffix normalizer: purification/purify/purifying -> purif
    ("ification", "if"), ("ifying", "if"), ("ified", "if"), ("ify", "if"),
    ("ization", "iz"), ("izing", "iz"), ("ized", "iz"), ("ize", "iz"),
    ("ations", "at"), ("ation", "at"),
)


def _stem(tok: str) -> str:
    for suffix, repl in _SUFFIXES:
        if len(tok) > len(suffix) + 2 and tok.endswith(suffix):
            return tok[: -len(suffix)] + repl
    if len(tok) > 4 and tok.endswith("ies"):
        return tok[:-3] + "y"
    if len(tok) > 3 and tok.endswith("s") and not tok.endswith(("ss", "us", "is")):
        return tok[:-1]
    return tok


def tokenize(text: str) -> list[str]:
    return [_stem(t) for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOPWORDS]


@dataclass
class Hit:
    chunk: Chunk
    score: float


class Index:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1, self.b = k1, b
        self.tfs: list[Counter] = []
        self.df: Counter = Counter()
        for c in chunks:
            tf = Counter(tokenize(c.context_text() + " " + " ".join(c.tags)))
            self.tfs.append(tf)
            self.df.update(tf.keys())
        self.lengths = [sum(tf.values()) for tf in self.tfs]
        self.avgdl = (sum(self.lengths) / len(self.lengths)) if self.lengths else 0.0
        self.embeddings = None  # numpy array, optional
        self.embed_model_name: str | None = None

    # ------------------------------------------------------------------ build
    def build_embeddings(self, model_name: str = DEFAULT_EMBED_MODEL) -> None:
        from sentence_transformers import SentenceTransformer  # optional dependency

        model = SentenceTransformer(model_name)
        texts = [c.context_text() for c in self.chunks]
        self.embeddings = model.encode(
            texts, batch_size=32, show_progress_bar=True, normalize_embeddings=True
        )
        self.embed_model_name = model_name

    # ------------------------------------------------------------------- I/O
    def save(self, out_dir: Path) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        with (out_dir / "chunks.jsonl").open("w", encoding="utf-8") as f:
            for c in self.chunks:
                f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
        manifest = {"num_chunks": len(self.chunks), "embed_model": self.embed_model_name}
        (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        emb_path = out_dir / "embeddings.npy"
        if self.embeddings is not None:
            import numpy as np

            np.save(emb_path, self.embeddings)
        elif emb_path.exists():
            emb_path.unlink()  # stale embeddings would no longer line up with chunks

    @classmethod
    def load(cls, index_dir: Path) -> "Index":
        chunks_path = index_dir / "chunks.jsonl"
        if not chunks_path.exists():
            raise FileNotFoundError(
                f"No index at {index_dir}. Run: python -m survival_rag ingest"
            )
        with chunks_path.open(encoding="utf-8") as f:
            chunks = [Chunk.from_dict(json.loads(line)) for line in f if line.strip()]
        idx = cls(chunks)
        manifest = json.loads((index_dir / "manifest.json").read_text(encoding="utf-8"))
        emb_path = index_dir / "embeddings.npy"
        if manifest.get("embed_model") and emb_path.exists():
            try:
                import numpy as np

                idx.embeddings = np.load(emb_path)
                idx.embed_model_name = manifest["embed_model"]
            except ImportError:
                pass  # fall back to BM25 only
        return idx

    # ---------------------------------------------------------------- search
    def _allowed(self, c: Chunk, category: str | None, region: str | None) -> bool:
        if category and c.category != category.lower():
            return False
        if region and region.lower() not in c.regions and "all" not in c.regions:
            return False
        return True

    def bm25(self, query: str, candidates: list[int]) -> list[tuple[int, float]]:
        q = tokenize(query)
        n = len(self.chunks)
        scored = []
        for i in candidates:
            tf, dl, s = self.tfs[i], self.lengths[i], 0.0
            for term in q:
                f = tf.get(term)
                if not f:
                    continue
                idf = math.log(1 + (n - self.df[term] + 0.5) / (self.df[term] + 0.5))
                s += idf * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            if s > 0:
                scored.append((i, s))
        return sorted(scored, key=lambda x: -x[1])

    def dense(self, query: str, candidates: list[int]) -> list[tuple[int, float]]:
        if self.embeddings is None or not candidates:
            return []
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            return []
        import numpy as np

        if getattr(self, "_model", None) is None:
            self._model = SentenceTransformer(self.embed_model_name)
        q = self._model.encode([query], normalize_embeddings=True)[0]
        sims = self.embeddings[candidates] @ q
        order = np.argsort(-sims)
        return [(candidates[j], float(sims[j])) for j in order]

    def search(
        self,
        query: str,
        k: int = 5,
        category: str | None = None,
        region: str | None = None,
    ) -> list[Hit]:
        candidates = [i for i, c in enumerate(self.chunks) if self._allowed(c, category, region)]
        lexical = self.bm25(query, candidates)
        semantic = self.dense(query, candidates)
        if not semantic:
            return [Hit(self.chunks[i], s) for i, s in lexical[:k]]
        # Reciprocal rank fusion of both result lists
        fused: dict[int, float] = {}
        for ranking in (lexical[:50], semantic[:50]):
            for rank, (i, _) in enumerate(ranking):
                fused[i] = fused.get(i, 0.0) + 1.0 / (60 + rank)
        best = sorted(fused.items(), key=lambda x: -x[1])[:k]
        return [Hit(self.chunks[i], s) for i, s in best]
