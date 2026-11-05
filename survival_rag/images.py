"""Image support: a JSON manifest of licensed images, linked into chunks and indexed by caption.

Pure standard library. Images are never "understood" by the engine — they are retrieved
through their human-written captions, alt text, and tags, plus the doc sections that
embed them. That keeps search fully offline and dependency-free.
"""
from __future__ import annotations

import json
from pathlib import Path

from .docs import (
    IMAGE_RE,
    VALID_CATEGORIES,
    VALID_RISK,
    Chunk,
    Document,
    _as_list,
    extract_image_refs,  # noqa: F401  (re-exported for callers)
    image_id,
    validate_meta,
)

MANIFEST_NAME = "manifest.json"
MAX_IMAGE_BYTES = 400 * 1024
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

REQUIRED_IMAGE_FIELDS = (
    "id", "file", "title", "caption", "alt", "category", "region", "tags",
    "source_url", "author", "license",
)

# Licenses that allow redistribution in this repo. Anything else is rejected.
ALLOWED_LICENSES = {
    "PD", "PD-USGov", "CC0-1.0",
    "CC-BY-2.0", "CC-BY-2.5", "CC-BY-3.0", "CC-BY-4.0",
    "CC-BY-SA-2.0", "CC-BY-SA-2.5", "CC-BY-SA-3.0", "CC-BY-SA-4.0",
}

# The one sentence every high-risk plant photo must carry.
PHOTO_DISCLAIMER = "a photo alone is never enough"


def load_images(images_root: Path) -> dict[str, dict]:
    """Load images/manifest.json as {id: entry}. Missing manifest -> no images."""
    path = Path(images_root) / MANIFEST_NAME
    if not path.exists():
        return {}
    entries = json.loads(path.read_text(encoding="utf-8"))
    return {e["id"]: e for e in entries if isinstance(e, dict) and "id" in e}


def _load_raw_manifest(images_root: Path) -> list:
    path = Path(images_root) / MANIFEST_NAME
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def validate_images(images_root: Path, knowledge_root: Path, docs: list[Document]) -> list[str]:
    """Return human-readable problems with the image manifest, files, and doc references."""
    images_root, knowledge_root = Path(images_root), Path(knowledge_root)
    problems: list[str] = []
    try:
        raw = _load_raw_manifest(images_root)
    except json.JSONDecodeError as e:
        return [f"{MANIFEST_NAME}: invalid JSON ({e})"]
    if not isinstance(raw, list):
        return [f"{MANIFEST_NAME}: must be a JSON list of image entries"]

    seen: dict[str, dict] = {}
    for n, e in enumerate(raw):
        label = e.get("id", f"entry #{n}") if isinstance(e, dict) else f"entry #{n}"
        if not isinstance(e, dict):
            problems.append(f"{label}: not an object")
            continue
        for f in REQUIRED_IMAGE_FIELDS:
            if not e.get(f):
                problems.append(f"{label}: missing field '{f}'")
        iid = e.get("id")
        if iid in seen:
            problems.append(f"{label}: duplicate id")
        file = e.get("file", "")
        if file and image_id(file) != iid:
            problems.append(f"{label}: id must equal the filename stem ('{image_id(file)}')")
        if e.get("license") and e["license"] not in ALLOWED_LICENSES:
            problems.append(f"{label}: license '{e['license']}' is not on the allowlist")
        meta_problems = validate_meta({
            "title": e.get("title"), "category": e.get("category", ""),
            "region": e.get("region"), "tags": e.get("tags"), "risk": e.get("risk", "low"),
        })
        problems += [f"{label}: {p}" for p in meta_problems if not p.startswith("missing")]
        if file:
            fp = images_root / file
            if not fp.is_file():
                problems.append(f"{label}: file not found: images/{file}")
            elif fp.stat().st_size > MAX_IMAGE_BYTES:
                problems.append(f"{label}: {fp.stat().st_size // 1024} KB exceeds {MAX_IMAGE_BYTES // 1024} KB")
        if (e.get("category") == "plants" and str(e.get("risk", "low")).lower() == "high"
                and PHOTO_DISCLAIMER not in str(e.get("caption", "")).lower()):
            problems.append(f"{label}: high-risk plant caption must say '{PHOTO_DISCLAIMER}'")
        if iid:
            seen[iid] = e

    for iid, e in seen.items():
        for other in _as_list(e.get("lookalikes")):
            if other not in seen:
                problems.append(f"{iid}: unknown lookalike '{other}'")
            elif iid not in _as_list(seen[other].get("lookalikes")):
                problems.append(f"{iid}: lookalike '{other}' does not link back")

    listed = {str(Path(e.get("file", ""))).replace("\\", "/") for e in seen.values()}
    if images_root.is_dir():
        for fp in sorted(images_root.rglob("*")):
            if fp.suffix.lower() in IMAGE_EXTS:
                rel = fp.relative_to(images_root).as_posix()
                if rel not in listed:
                    problems.append(f"orphan image not in manifest: images/{rel}")

    for doc in docs:
        doc_dir = (knowledge_root / doc.path).parent
        for m in IMAGE_RE.finditer(doc.body):
            link, file = m.group(2), m.group(3)
            if image_id(file) not in seen:
                problems.append(f"{doc.path}: references images/{file}, which is not in the manifest")
            elif (doc_dir / link).resolve() != (images_root / file).resolve():
                problems.append(f"{doc.path}: broken relative link '{link}'")
            if not m.group(1).strip():
                problems.append(f"{doc.path}: image images/{file} has empty alt text")
    return problems


def image_chunks(images: dict[str, dict], doc_chunks: list[Chunk]) -> list[Chunk]:
    """One searchable chunk per image, built from its caption, alt text, and tags.

    The image inherits the critical warning of the documents that embed it (or uses its
    own `critical_warning`), so lookalike warnings are never separated from a photo.
    """
    used_by: dict[str, list[Chunk]] = {}
    for c in doc_chunks:
        for iid in c.images:
            used_by.setdefault(iid, []).append(c)
    out = []
    for iid, e in images.items():
        refs = used_by.get(iid, [])
        warning = str(e.get("critical_warning") or next((c.warning for c in refs if c.warning), ""))
        docs_seen = list(dict.fromkeys(f"{c.title} > {c.section}" if c.section else c.title for c in refs))
        # "What it looks like" lets appearance questions ("what does X look like") match every image equally,
        # so the subject words decide the ranking.
        text = f"{e.get('caption', '').strip()}\n\nWhat it looks like: {e.get('alt', '').strip()}"
        if e.get("lookalikes"):
            names = [images[o]["title"] for o in _as_list(e["lookalikes"]) if o in images]
            if names:
                text += f"\n\nCompare with lookalikes: {'; '.join(names)}."
        if docs_seen:
            text += f"\n\nSee: {'; '.join(docs_seen[:3])}."
        category = str(e.get("category", "")).lower()
        risk = str(e.get("risk", "low")).lower()
        out.append(Chunk(
            id=f"img-{iid}",
            path=f"images/{e.get('file', '')}",
            title=f"Image: {e.get('title', iid)}",
            section="",
            category=category if category in VALID_CATEGORIES else "meta",
            regions=_as_list(e.get("region")) or ["all"],
            tags=_as_list(e.get("tags")),
            risk=risk if risk in VALID_RISK else "low",
            text=text,
            warning=warning,
            images=[iid],
        ))
    return out
