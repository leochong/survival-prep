from pathlib import Path

import pytest

from survival_rag.docs import (
    Chunk,
    Document,
    chunk_document,
    load_documents,
    parse_frontmatter,
    validate_meta,
    _mini_yaml,
)
from survival_rag.images import (
    ALLOWED_LICENSES,
    MAX_IMAGE_BYTES,
    extract_image_refs,
    image_chunks,
    load_images,
    validate_images,
)
from survival_rag.index import Index, tokenize

ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE = ROOT / "knowledge"
IMAGES_DIR = ROOT / "images"

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
    for r in ["northeast", "southeast", "midwest", "great-plains", "southwest", "great-basin",
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
    ("Reno pinyon pine nuts trees", "nevada-reno-las-vegas"),
    ("Las Vegas edible trees mesquite date palm", "nevada-reno-las-vegas"),
])
def test_real_queries_retrieve_expected_docs(query, expected_path_part):
    idx = Index([c for d in DOCS for c in chunk_document(d)])
    paths = [h.chunk.path for h in idx.search(query, k=3)]
    assert any(expected_path_part in p for p in paths), paths


def test_nevada_sections_are_region_scoped():
    doc = next(d for d in DOCS if "nevada-reno-las-vegas" in d.path)
    by_section = {c.section.split(" > ")[0]: c.regions for c in chunk_document(doc)}
    reno = next(v for k, v in by_section.items() if k.startswith("Reno"))
    vegas = next(v for k, v in by_section.items() if k.startswith("Las Vegas"))
    assert reno == ["great-basin"] and vegas == ["southwest"]


# ---- images ---------------------------------------------------------------------

IMG_SAMPLE = SAMPLE + "\n![Rolling boil in a pot](../../images/03-survival-howto/boil.jpg)\n"


def test_extract_image_refs_replaces_markup_with_alt():
    text, ids = extract_image_refs("Before ![A pot of water](../images/x/boil.jpg) after ![](images/y/fire.png)")
    assert ids == ["boil", "fire"]
    assert text == "Before [Image: A pot of water] after [Image]"


def test_images_attach_to_their_section_only():
    meta, body = parse_frontmatter(IMG_SAMPLE)
    chunks = {c.section: c for c in chunk_document(Document("x.md", meta, body))}
    assert chunks["Bleach"].images == ["boil"]
    assert chunks["Boiling"].images == []
    assert "](" not in chunks["Bleach"].text and "[Image: Rolling boil in a pot]" in chunks["Bleach"].text


def test_old_index_rows_without_images_still_load():
    row = {"id": "a", "path": "p.md", "title": "T", "section": "", "category": "survival",
           "regions": ["all"], "tags": [], "risk": "low", "text": "hello", "warning": ""}
    assert Chunk.from_dict(row).images == []


def test_image_chunk_is_searchable_and_inherits_warning():
    meta, body = parse_frontmatter(IMG_SAMPLE)
    doc_chunks = chunk_document(Document("x.md", meta, body))
    images = {"boil": {"id": "boil", "file": "03-survival-howto/boil.jpg", "title": "Boiling water",
                       "caption": "A pot of water at a rolling boil over a campfire.", "alt": "Pot boiling",
                       "category": "survival", "region": "all", "tags": ["boil"], "risk": "low"}}
    imgs = image_chunks(images, doc_chunks)
    assert imgs[0].images == ["boil"] and imgs[0].warning == "Boil it."
    hit = Index(doc_chunks + imgs).search("campfire pot rolling boil", k=1)[0]
    assert hit.chunk.id == "img-boil"


def test_validate_images_catches_problems(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "x.jpg").write_bytes(b"\xff\xd8" + b"0" * 10)
    (tmp_path / "a" / "orphan.jpg").write_bytes(b"\xff\xd8")
    entry = {"id": "x", "file": "a/x.jpg", "title": "X", "caption": "Deadly berry.", "alt": "x",
             "category": "plants", "region": "all", "tags": ["x"], "risk": "high",
             "lookalikes": ["missing"], "source_url": "u", "author": "a", "license": "All rights reserved"}
    (tmp_path / "manifest.json").write_text(__import__("json").dumps([entry]), encoding="utf-8")
    doc = Document("d.md", {}, "![](../images/a/nope.jpg)")
    problems = "\n".join(validate_images(tmp_path, tmp_path / "k", [doc]))
    for expected in ["not on the allowlist", "a photo alone is never enough", "unknown lookalike",
                     "orphan image", "not in the manifest", "empty alt text"]:
        assert expected in problems, expected


IMAGES = load_images(IMAGES_DIR)


def test_image_library_present():
    assert len(IMAGES) >= 20


def test_image_manifest_and_links_valid():
    assert validate_images(IMAGES_DIR, KNOWLEDGE, DOCS) == []


def test_images_small_licensed_and_referenced():
    referenced = {i for d in DOCS for i in extract_image_refs(d.body)[1]}
    total = 0
    for iid, e in IMAGES.items():
        size = (IMAGES_DIR / e["file"]).stat().st_size
        total += size
        assert size <= MAX_IMAGE_BYTES, iid
        assert e["license"] in ALLOWED_LICENSES, iid
        assert iid in referenced, f"{iid} is not used by any knowledge doc"
    assert total < 50 * 1024 * 1024


@pytest.mark.parametrize("query,image", [
    ("what does water hemlock look like", "water-hemlock"),
    ("what does death camas look like", "death-camas"),
    ("moonseed crescent seed vs wild grape", "moonseed"),
    ("how to tie a bowline", "bowline"),
    ("how to splint a broken forearm", "forearm-splint"),
    ("find the north star big dipper", "polaris-big-dipper"),
    ("contour lines topographic map", "topo-map-contours"),
    ("Reno pinyon pine nut tree", "singleleaf-pinyon"),
])
def test_real_queries_retrieve_expected_images(query, image):
    doc_chunks = [c for d in DOCS for c in chunk_document(d)]
    idx = Index(doc_chunks + image_chunks(IMAGES, doc_chunks))
    found = [i for h in idx.search(query, k=3) for i in h.chunk.images]
    assert image in found, found


def test_deadly_plant_image_hits_carry_warnings():
    doc_chunks = [c for d in DOCS for c in chunk_document(d)]
    for c in image_chunks(IMAGES, doc_chunks):
        if c.category == "plants" and c.risk == "high":
            assert c.warning, c.id
            assert "photo alone is never enough" in c.text.lower(), c.id


def test_every_image_is_credited():
    credits = (IMAGES_DIR / "README.md").read_text(encoding="utf-8")
    for e in IMAGES.values():
        assert f"`{e['file']}`" in credits and e["source_url"] in credits, e["id"]
