"""Load knowledge-base markdown files, parse frontmatter, and split them into chunks.

Pure standard library (PyYAML is used if present, otherwise a minimal parser).
Designed to run on low-power hardware (Raspberry Pi, old laptops) fully offline.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

REQUIRED_FIELDS = ("title", "category", "region", "tags")

VALID_CATEGORIES = {
    "medical",
    "plants",
    "survival",
    "maps",
    "navigation",
    "building",
    "chemistry",
    "food",
    "communications",
    "meta",
}

VALID_REGIONS = {
    "all",
    "northeast",
    "southeast",
    "midwest",
    "great-plains",
    "southwest",
    "great-basin",
    "rocky-mountains",
    "pacific-northwest",
    "california",
    "alaska",
    "hawaii",
}

VALID_RISK = {"low", "medium", "high"}

FRONTMATTER_RE = re.compile(r"\A---\s*\r?\n(.*?)\r?\n---\s*\r?\n", re.S)
HEADING_RE = re.compile(r"^(#{1,4})\s+(.*\S)\s*$")

# ![alt text](../../images/02-plants-and-herbal/water-hemlock.jpg)
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(\s*([^)\s]*?images/([^)\s]+))\s*\)")


def image_id(file: str) -> str:
    """An image's id is its filename stem (ids must therefore be unique repo-wide)."""
    return Path(file).stem


def extract_image_refs(text: str) -> tuple[str, list[str]]:
    """Return (text with image markup replaced by its alt text, list of image ids)."""
    ids: list[str] = []

    def repl(m: re.Match) -> str:
        iid = image_id(m.group(3))
        if iid not in ids:
            ids.append(iid)
        alt = m.group(1).strip()
        return f"[Image: {alt}]" if alt else "[Image]"

    return IMAGE_RE.sub(repl, text), ids


@dataclass
class Document:
    path: str
    meta: dict
    body: str


@dataclass
class Chunk:
    id: str
    path: str
    title: str
    section: str
    category: str
    regions: list[str]
    tags: list[str]
    risk: str
    text: str
    warning: str = ""
    images: list[str] = field(default_factory=list)  # ids from images/manifest.json

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Chunk":
        known = cls.__dataclass_fields__
        return cls(**{k: v for k, v in d.items() if k in known})  # old indexes lack 'images'

    def context_text(self) -> str:
        """Text that is indexed and handed to the LLM, with a breadcrumb header."""
        header = f"{self.title} > {self.section}" if self.section else self.title
        out = f"[{header}]\n{self.text}"
        if self.warning:
            out += f"\n\nCRITICAL WARNING: {self.warning}"
        return out


# --------------------------------------------------------------------------- #
# Frontmatter
# --------------------------------------------------------------------------- #

def _scalar(value: str):
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [_scalar(v) for v in inner.split(",")] if inner else []
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _mini_yaml(raw: str) -> dict:
    """Very small YAML subset: `key: value`, inline lists, and `- item` lists."""
    meta: dict = {}
    current_key = None
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        stripped = line.strip()
        if stripped.startswith("- ") and current_key:
            if not isinstance(meta.get(current_key), list):
                meta[current_key] = []
            meta[current_key].append(_scalar(stripped[2:]))
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            current_key = key.strip()
            meta[current_key] = _scalar(value) if value.strip() else []
    return meta


def parse_frontmatter(text: str) -> tuple[dict, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    raw = m.group(1)
    try:
        import yaml  # type: ignore

        meta = yaml.safe_load(raw) or {}
        if not isinstance(meta, dict):
            meta = _mini_yaml(raw)
    except ImportError:
        meta = _mini_yaml(raw)
    except Exception:  # malformed YAML (e.g. '?' or ':' inside a flow list) — be forgiving
        meta = _mini_yaml(raw)
    return meta, text[m.end():]


def _as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [v.strip().lower() for v in value.split(",") if v.strip()]
    return [str(v).strip().lower() for v in value if str(v).strip()]


def validate_meta(meta: dict) -> list[str]:
    """Return a list of human-readable problems with a document's frontmatter."""
    problems = [f"missing field '{f}'" for f in REQUIRED_FIELDS if f not in meta]
    cat = str(meta.get("category", "")).lower()
    if cat and cat not in VALID_CATEGORIES:
        problems.append(f"unknown category '{cat}'")
    for r in _as_list(meta.get("region")):
        if r not in VALID_REGIONS:
            problems.append(f"unknown region '{r}'")
    risk = str(meta.get("risk", "low")).lower()
    if risk not in VALID_RISK:
        problems.append(f"unknown risk '{risk}'")
    return problems


# --------------------------------------------------------------------------- #
# Loading & chunking
# --------------------------------------------------------------------------- #

def load_documents(root: Path) -> list[Document]:
    docs = []
    for path in sorted(root.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        if not meta:
            continue  # README-style files without frontmatter are not indexed
        docs.append(Document(path=path.relative_to(root).as_posix(), meta=meta, body=body))
    return docs


def _split_sections(body: str) -> list[tuple[str, str]]:
    """Split markdown into (heading-path, text) sections."""
    sections: list[tuple[str, str]] = []
    stack: list[tuple[int, str]] = []
    buf: list[str] = []

    def flush():
        text = "\n".join(buf).strip()
        if text:
            path = " > ".join(h for lvl, h in stack if lvl > 1)  # H1 is the title
            sections.append((path, text))
        buf.clear()

    in_code = False
    for line in body.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
        m = None if in_code else HEADING_RE.match(line)
        if m:
            flush()
            level = len(m.group(1))
            stack = [(lvl, h) for lvl, h in stack if lvl < level]
            stack.append((level, m.group(2)))
        else:
            buf.append(line)
    flush()
    return sections


def _pack(paragraphs: list[str], max_chars: int) -> list[str]:
    chunks, cur = [], ""
    for p in paragraphs:
        if len(p) > max_chars:  # hard-split giant paragraphs on sentence boundaries
            if cur:
                chunks.append(cur)
                cur = ""
            sentences = re.split(r"(?<=[.!?])\s+", p)
            for s in sentences:
                if len(cur) + len(s) + 1 > max_chars and cur:
                    chunks.append(cur)
                    cur = ""
                cur = f"{cur} {s}".strip()
            continue
        if len(cur) + len(p) + 2 > max_chars and cur:
            chunks.append(cur)
            cur = ""
        cur = f"{cur}\n\n{p}".strip()
    if cur:
        chunks.append(cur)
    return chunks


def _slug(text: str) -> str:
    text = re.sub(r"^(desert|the)\s+", "", text.strip().lower())
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def chunk_document(doc: Document, max_chars: int = 1200) -> list[Chunk]:
    meta = doc.meta
    title = str(meta.get("title", Path(doc.path).stem))
    regions = _as_list(meta.get("region")) or ["all"]
    tags = _as_list(meta.get("tags"))
    out: list[Chunk] = []
    for section, text in _split_sections(doc.body):
        # In multi-region docs, a section headed by a region name ("## Pacific Northwest")
        # applies only to that region, so region-filtered searches stay precise.
        chunk_regions = regions
        top = _slug(section.split(" > ")[0]) if section else ""
        if len(regions) > 1 and top:
            named = [r for r in regions if r != "all" and re.search(rf"(^|-){r}(-|$)", top)]
            if len(named) == 1:  # "## Reno and the Great Basin" -> great-basin only
                chunk_regions = named
        # Images embedded in a section belong to every chunk of that section.
        text, section_images = extract_image_refs(text)
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        for i, piece in enumerate(_pack(paragraphs, max_chars)):
            digest = hashlib.sha1(f"{doc.path}|{section}|{i}".encode()).hexdigest()[:12]
            out.append(
                Chunk(
                    id=digest,
                    path=doc.path,
                    title=title,
                    section=section,
                    category=str(meta.get("category", "")).lower(),
                    regions=chunk_regions,
                    tags=tags,
                    risk=str(meta.get("risk", "low")).lower(),
                    text=piece,
                    warning=str(meta.get("critical_warning", "") or ""),
                    images=list(section_images),
                )
            )
    return out
