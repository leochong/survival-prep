# survival-prep

An **offline-first retrieval-augmented generation (RAG) knowledge base** of survival skills for a long-term grid-down / disaster / "apocalypse" scenario in the United States.

- **62 curated documents, ~580 retrieval chunks** across medicine, regional plants, survival how-to, maps, navigation, building, low-resource chemistry, food, and communications.
- **29 openly licensed reference images:** deadly plants next to their edible lookalikes, plus first aid, knots, fire, shelter, and navigation diagrams. Images are found by their captions, so image search also works with zero dependencies.
- **Search works with zero dependencies.** The core is pure Python standard library (BM25), so it runs on a Raspberry Pi or an old laptop with no internet.
- **Optional semantic search** with `sentence-transformers` embeddings (hybrid BM25 + vector, reciprocal-rank fusion).
- **Optional local LLM answers** through any OpenAI-compatible local server (Ollama, llama.cpp, LM Studio). There is no cloud dependency.
- **Safety-aware.** Every document carries a `risk` level, and high-risk docs carry a `critical_warning` that is attached to *every* chunk retrieved from them, so lookalike and contraindication warnings are never separated from the instructions they belong to.

> ⚠️ **Disclaimer.** This is reference material for emergencies when professional help is unavailable. It is not a substitute for training, a doctor, or positive in-person plant identification. Take a first-aid / wilderness first responder course, learn your local plants with an expert, and verify everything while you still can.

## Repository layout

```
knowledge/                       # the corpus: markdown + YAML frontmatter
  01-emergency-medical/          # triage, bleeding, wounds, fractures, burns, cold/heat,
                                 # ORS, CPR, envenomation, med kit, childbirth, dental
  02-plants-and-herbal/          # foraging rules, deadly lookalikes, mushrooms, medicinal herbs
    regions/                     # northeast, southeast, midwest, great-plains, southwest,
                                 # great-basin + nevada-reno-las-vegas,
                                 # rocky-mountains, pacific-northwest, california, alaska, hawaii
  03-survival-howto/             # priorities, water purification, finding water, fire, shelter,
                                 # sanitation, signaling, nuclear/CBRN, knots & cordage
  04-maps/                       # offline map library, reading topo maps, regional hazards
  05-navigation/                 # map & compass, no-compass methods, GPS/UTM/grid
  06-building/                   # rain catchment, water filters, rocket stoves, shelters,
                                 # off-grid solar, root cellars, hand tools
  07-low-resource-chemistry/     # chemical safety, lye & soap, charcoal, lime, disinfectants,
                                 # glues/candles/tanning/salt/vinegar
  08-food-and-agriculture/       # preservation, storage & nutrition, gardening & seeds,
                                 # fishing/trapping/game, small livestock
  09-communications/             # emergency radio, PACE communication plan
images/                          # licensed reference images, mirroring knowledge/ folders
  manifest.json                  # caption, alt text, tags, region, risk, lookalikes, license
  README.md                      # credits table (author, license, source for every image)
maps/offline/                    # your downloaded map files (git-ignored)
survival_rag/                    # the RAG engine (stdlib-only core)
tools/fetch_usgs_topo.py         # download USGS topo GeoPDFs for an area, while online
tests/                           # unit tests + corpus integrity + retrieval checks
```

## Quick start

```bash
# 1. Build the index (stdlib only, takes about a second)
python -m survival_rag ingest

# 2. Search, no LLM needed
python -m survival_rag search "how many drops of bleach per gallon"
python -m survival_rag search "edible berries" --region pacific-northwest
python -m survival_rag search "tourniquet" --category medical --full

# 3. Ask a local LLM (interactive if no question is given)
ollama pull llama3.2           # once, while online
python -m survival_rag ask "my friend was bitten by a rattlesnake, what do I do?"
python -m survival_rag ask --region southwest
```

Other commands: `validate` checks frontmatter and the image manifest, and `stats` summarizes the index.

## Images

Docs embed images with ordinary markdown (`![alt text](../../images/...)`), so they render on GitHub and in any markdown viewer. Retrieval uses them in two ways:

- **Attached to text.** Every chunk from a section that embeds an image lists that image, and `search` prints its path, license, and author under the hit.
- **As their own results.** Each image is indexed from its caption, alt text, and tags. `search "what does water hemlock look like"` returns the water hemlock photo first, carrying its critical warning.

```bash
python -m survival_rag search "moonseed vs wild grape" --images-only
python -m survival_rag search "how to tie a bowline"
```

The engine never looks at pixels. Images are found only through human-written descriptions, so it works offline on any hardware. Captions of high-risk plant photos always state that a photo alone is never enough for identification. Credits and licenses are listed in [`images/README.md`](images/README.md).

### Optional semantic search

```bash
pip install -r requirements.txt
python -m survival_rag ingest --embed    # downloads and caches all-MiniLM-L6-v2 (~90 MB) once
```

The index then uses hybrid retrieval. If the embedding libraries are missing at query time, it falls back to BM25.

### LLM configuration

| Env var | Default |
|---|---|
| `SURVIVAL_LLM_BASE_URL` | `http://localhost:11434/v1` (Ollama) |
| `SURVIVAL_LLM_MODEL` | `llama3.2` |
| `SURVIVAL_LLM_API_KEY` | `local` |

The system prompt (`survival_rag/llm.py`) makes the model answer only from retrieved excerpts, cite them, repeat critical warnings, flag when medical care is needed, and refuse to confirm plant edibility from a description.

### Using the corpus in another RAG stack

`ingest` writes `index/chunks.jsonl`, one chunk per line with `text`, `title`, `section`, `category`, `regions`, `tags`, `risk`, `warning`, and `images` (ids that map to `index/images.json`). Image chunks have ids starting with `img-`. You can load it directly into LangChain, LlamaIndex, Chroma, and similar tools. Use `Chunk.context_text()` (breadcrumb + text + warning) as the embedded text.

## Offline maps

```bash
python tools/fetch_usgs_topo.py --point 40.015,-105.27 --radius-mi 10 --dry-run
python tools/fetch_usgs_topo.py --point 40.015,-105.27 --radius-mi 10
```

This downloads current USGS 7.5-minute US Topo GeoPDFs into `maps/offline/usgs-topo/<STATE>/`. See `knowledge/04-maps/00-offline-map-sources.md` for OpenStreetMap, phone apps, and what to print.

## Prepare now, while you have internet

1. `pip install -r requirements.txt && python -m survival_rag ingest --embed`
2. `ollama pull llama3.2` (or a larger model if your hardware allows)
3. Download maps for your home area and evacuation routes
4. Copy this whole folder, including `index/`, `maps/offline/`, and model caches, to two USB drives, and keep one in a metal box
5. **Print** the high-risk docs (`risk: high`): bleeding, CPR, water purification, deadly plants, and your regional plant guide. Print them from a markdown viewer so the images come with them: the deadly-plant photos are most useful on paper.

## Contributing content

See [CONTRIBUTING.md](CONTRIBUTING.md) for the frontmatter schema and writing rules. Run `python -m pytest` before committing. The tests validate every document and check that real-world queries retrieve the right docs.
