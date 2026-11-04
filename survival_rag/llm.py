"""Answer generation against any OpenAI-compatible *local* endpoint.

Works out of the box with Ollama (default), llama.cpp `llama-server`, LM Studio,
or vLLM. Uses only the standard library (urllib) so no SDK is required.

Environment variables:
    SURVIVAL_LLM_BASE_URL  default http://localhost:11434/v1   (Ollama)
    SURVIVAL_LLM_MODEL     default llama3.2
    SURVIVAL_LLM_API_KEY   default "local" (ignored by most local servers)
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .index import Hit

SYSTEM_PROMPT = """You are an offline survival reference assistant. People may be using you \
in a real emergency with no internet and no professional help available.

Rules:
1. Answer ONLY from the numbered reference excerpts provided. Cite them like [1], [2].
2. If the excerpts do not cover the question, say so plainly. Do not invent doses, \
plant identifications, or procedures.
3. Lead with the most urgent, actionable steps first, as a short numbered list.
4. Always repeat any CRITICAL WARNING, lookalike, contraindication, or "do not" \
from the excerpts that is relevant.
5. For medical questions, state when the situation exceeds field care and the person \
needs evacuation to a doctor/hospital if any is reachable.
6. Never confirm a plant or mushroom is safe to eat based on a description alone; \
remind the user that positive identification is required.
7. Be concise. Use plain language a stressed, tired person can follow."""


def build_context(hits: list[Hit]) -> str:
    parts = []
    for n, h in enumerate(hits, 1):
        c = h.chunk
        parts.append(f"[{n}] (source: {c.path}; regions: {', '.join(c.regions)})\n{c.context_text()}")
    return "\n\n---\n\n".join(parts)


def ask(question: str, hits: list[Hit], timeout: int = 300) -> str:
    base = os.environ.get("SURVIVAL_LLM_BASE_URL", "http://localhost:11434/v1").rstrip("/")
    model = os.environ.get("SURVIVAL_LLM_MODEL", "llama3.2")
    key = os.environ.get("SURVIVAL_LLM_API_KEY", "local")

    payload = {
        "model": model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Reference excerpts:\n\n{build_context(hits)}\n\nQuestion: {question}",
            },
        ],
    }
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, TimeoutError) as e:
        raise RuntimeError(
            f"Could not reach local LLM at {base} ({e}). "
            "Start one (e.g. `ollama serve` + `ollama pull llama3.2`) or use `search` instead."
        ) from e
    return data["choices"][0]["message"]["content"].strip()
