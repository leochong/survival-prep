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

## Checks

```bash
python -m survival_rag validate
python -m pytest
python -m survival_rag ingest
```

If you add an important topic, add a query to `test_real_queries_retrieve_expected_docs` in `tests/test_rag.py` to make sure it is retrievable.
