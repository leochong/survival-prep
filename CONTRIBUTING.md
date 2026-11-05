# Contributing knowledge

Each document is a markdown file under `knowledge/` that starts with YAML frontmatter. Files without frontmatter (like READMEs) are not indexed.

## Frontmatter schema

```yaml
---
title: Controlling Severe Bleeding          # required
category: medical                           # required: medical | plants | survival | maps | navigation |
                                            #   building | chemistry | food | communications | meta
region: all                                 # required: all, or one/list of: northeast, southeast, midwest,
                                            #   great-plains, southwest, great-basin, rocky-mountains, pacific-northwest,
                                            #   california, alaska, hawaii
tags: [bleeding, tourniquet, trauma]        # required: retrieval keywords and synonyms
risk: high                                  # low | medium | high (default low)
critical_warning: "One sentence that must never be separated from this content."   # optional
sources: [Stop the Bleed, TCCC Guidelines]  # where the facts come from
last_reviewed: 2026-11-03
---
```

- `critical_warning` is appended to **every chunk** from the document, so use it for lookalikes, contraindications, and lethal mistakes. Keep it to one or two sentences.
- In a multi-region document, a `##` section whose heading is a region name (for example `## Pacific Northwest`) is tagged with only that region.

## Writing rules

1. **Chunk-friendly structure.** The chunker splits on headings, so give each `##`/`###` section a self-contained topic, and make the heading name the topic ("Tourniquet placement", not "Step 3").
2. **Action first.** Use numbered steps, concrete quantities with units (US and metric), and times.
3. **Warnings sit next to instructions.** Put the "do not" in the same section as the "do."
4. **Cite reputable sources** (WHO, CDC, USDA, EPA, Wilderness Medical Society, extension services, established field guides).
5. **Plants:** for every edible, give identifying features, the edible part, season, preparation, and deadly lookalikes.
6. **Out of scope:** weapons manufacture, explosives, or anything designed to harm people.

## Images

Images live in `images/`, in folders that mirror `knowledge/`. Each one has an entry in `images/manifest.json` and a row in the credits table in `images/README.md`.

```json
{
  "id": "water-hemlock",                       // must equal the filename stem; unique repo-wide
  "file": "02-plants-and-herbal/water-hemlock.jpg",
  "title": "Water hemlock (Cicuta maculata)",
  "caption": "2–4 sentences: what is shown and the features that tell it apart. ...",
  "alt": "Short literal description of the picture",
  "category": "plants",                        // same values as docs
  "region": "all",                             // same values as docs
  "tags": ["water-hemlock", "cicuta", "deadly", "lookalike"],
  "risk": "high",
  "lookalikes": ["wild-carrot", "poison-hemlock"],   // optional; must link both ways
  "critical_warning": "One sentence that must travel with this image.",  // optional
  "source_url": "https://commons.wikimedia.org/wiki/File:...",
  "author": "Photographer name",
  "license": "CC-BY-SA-4.0"
}
```

(The comments above are for explanation only; the real file is plain JSON.)

**Rules**

1. **License.** Only `PD`, `PD-USGov`, `CC0-1.0`, `CC-BY-*`, or `CC-BY-SA-*`. Check the license on the file's own page (Wikimedia Commons, USDA PLANTS, CDC PHIL, NPS, USFWS, and US military field manuals are good sources). If you can't confirm a license, leave the image out.
2. **Size.** Resize to at most 1024 px on the long edge and save as JPEG at quality ~80. Files over 400 KB fail validation.
3. **Captions are the search index.** Name the subject and describe the distinguishing features someone would actually check. For a plant with `risk: high`, the caption must include "A photo alone is never enough for identification."
4. **Lookalikes go both ways.** If an edible has a deadly lookalike, add both images and link them to each other.
5. **Embed it in a doc.** Put `![alt text](relative/path/to/images/...)` in the section it illustrates. Every image must be used by at least one doc.
6. **Scope.** No images of weapons, explosives, or real graphic injuries. Training photos with simulated casualties are fine.

## Checks

```bash
python -m survival_rag validate
python -m pytest
python -m survival_rag ingest
```

If you add an important topic, add a query to `test_real_queries_retrieve_expected_docs` in `tests/test_rag.py` to make sure it is retrievable. For an important image, add a query to `test_real_queries_retrieve_expected_images`.
