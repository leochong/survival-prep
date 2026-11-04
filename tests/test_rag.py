from pathlib import Path

import pytest

from survival_rag.docs import (
    Document,
    chunk_document,
    load_documents,
    parse_frontmatter,
    validate_meta,
    _mini_yaml,
)
from survival_rag.index import Index, tokenize

ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE = ROOT / "knowledge"

SAMPLE = """---
title: Test Doc
category: survival
region: [northeast, midwest]
tags: [water, boil]
risk: high
critical_warning: "Boil it."
---

# Test Doc

Intro paragraph.

## Boiling

Bring water to a rolling boil for one minute.

## Bleach

Eight drops per gallon of six percent bleach.
"""


def test_parse_frontmatter():
    meta, body = parse_frontmatter(SAMPLE)
    assert meta["title"] == "Test Doc"
    assert "Boiling" in body


def test_mini_yaml_fallback():
    meta = _mini_yaml("title: X\nregion: [a, b]\ntags:\n- one\n- two\nrisk: 'low'")
    assert meta == {"title": "X", "region": ["a", "b"], "tags": ["one", "two"], "risk": "low"}


def test_validate_flags_bad_values():
    assert validate_meta({"title": "t", "category": "nope", "region": "mars", "tags": []})
    assert not validate_meta({"title": "t", "category": "medical", "region": "all", "tags": []})


def test_chunking_keeps_sections_and_warning():
    meta, body = parse_frontmatter(SAMPLE)
    chunks = chunk_document(Document("x.md", meta, body))
    sections = [c.section for c in chunks]
    assert "Boiling" in sections and "Bleach" in sections
    assert all(c.warning == "Boil it." for c in chunks)
    assert chunks[0].regions == ["northeast", "midwest"]
    assert "CRITICAL WARNING" in chunks[0].context_text()


def test_long_section_is_split():
    meta, _ = parse_frontmatter(SAMPLE)
    body = "## Long\n\n" + "\n\n".join(f"Sentence number {i} about water." * 5 for i in range(40))
    chunks = chunk_document(Document("x.md", meta, body), max_chars=300)
    assert len(chunks) > 5
    assert all(len(c.text) <= 300 for c in chunks)


def test_tokenize_stems_plurals():
    assert tokenize("Berries and Tourniquets") == ["berry", "tourniquet"]


def test_search_ranks_and_filters():
    meta, body = parse_frontmatter(SAMPLE)
    idx = Index(chunk_document(Document("x.md", meta, body)))
    hits = idx.search("how many drops of bleach", k=1)
    assert hits and hits[0].chunk.section == "Bleach"
    assert idx.search("bleach", region="southwest") == []
    assert idx.search("bleach", region="midwest")
    assert idx.search("bleach", category="medical") == []


def test_region_headed_sections_are_narrowed():
    meta = {"title": "Regions", "category": "maps", "region": ["alaska", "hawaii"], "tags": []}
    body = "## Alaska\n\nCold.\n\n## Hawaii\n\nWarm.\n\n## Universal tips\n\nBoth."
    chunks = {c.section: c.regions for c in chunk_document(Document("r.md", meta, body))}
    assert chunks == {"Alaska": ["alaska"], "Hawaii": ["hawaii"], "Universal tips": ["alaska", "hawaii"]}


def test_save_load_roundtrip(tmp_path):
    meta, body = parse_frontmatter(SAMPLE)
    idx = Index(chunk_document(Document("x.md", meta, body)))
    idx.save(tmp_path)
    loaded = Index.load(tmp_path)
    assert len(loaded.chunks) == len(idx.chunks)
    assert loaded.search("boil")[0].chunk.section == "Boiling"


# ---- knowledge base integrity -------------------------------------------------

DOCS = load_documents(KNOWLEDGE)


def test_knowledge_base_not_empty():
    assert len(DOCS) >= 40


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.path)
def test_every_document_valid(doc):
    assert validate_meta(doc.meta) == []
    assert chunk_document(doc), "document produced no chunks"


def test_every_region_has_plant_guide():
    regions = {r for d in DOCS if d.meta.get("category") == "plants" for r in
               (d.meta["region"] if isinstance(d.meta["region"], list) else [d.meta["region"]])}
    for r in ["northeast", "southeast", "midwest", "great-plains", "southwest",
              "rocky-mountains", "pacific-northwest", "california", "alaska", "hawaii"]:
        assert r in regions, f"no plant guide for {r}"


@pytest.mark.parametrize("query,expected_path_part", [
    ("tourniquet placement bleeding arm", "bleeding-control"),
    ("how many drops of bleach per gallon water", "water-purification"),
    ("how do I purify water", "water-purification"),
    ("water hemlock lookalike wild carrot", "deadly-plants"),
    ("north star big dipper", "navigation-without-compass"),
    ("make soap from wood ash", "soap"),
    ("oral rehydration salt sugar recipe", "ors"),
    ("pressure canning botulism green beans", "food-preservation"),
])
def test_real_queries_retrieve_expected_docs(query, expected_path_part):
    idx = Index([c for d in DOCS for c in chunk_document(d)])
    paths = [h.chunk.path for h in idx.search(query, k=3)]
    assert any(expected_path_part in p for p in paths), paths
