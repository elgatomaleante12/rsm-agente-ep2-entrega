from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from .database import rows


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def tokens(text: str) -> list[str]:
    stop = {
        "de",
        "del",
        "la",
        "el",
        "los",
        "las",
        "un",
        "una",
        "y",
        "o",
        "para",
        "que",
        "hay",
        "en",
        "me",
        "quedan",
        "queda",
        "stock",
    }
    return [tok for tok in normalize(text).split() if tok and tok not in stop]


def cosine_score(query: str, document: str) -> float:
    q = Counter(tokens(query))
    d = Counter(tokens(document))
    if not q or not d:
        return 0.0
    dot = sum(q[t] * d.get(t, 0) for t in q)
    q_norm = math.sqrt(sum(v * v for v in q.values()))
    d_norm = math.sqrt(sum(v * v for v in d.values()))
    if q_norm == 0 or d_norm == 0:
        return 0.0
    return dot / (q_norm * d_norm)


def inventory_documents(path: Path | None = None) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for row in rows("SELECT * FROM inventory ORDER BY ref", path=path):
        text = (
            f"{row['ref']} {row['name']} categoria {row['category']} stock {row['stock']} "
            f"minimo {row['min_stock']} ubicacion {row['location']} proveedor {row['provider']} "
            f"modelos compatibles {row['compatible_models']}"
        )
        docs.append({"source": "inventory", "title": row["ref"], "text": text, "payload": row})
    return docs


def knowledge_documents(path: Path | None = None) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for row in rows("SELECT * FROM knowledge ORDER BY id", path=path):
        docs.append({"source": row["source"], "title": row["title"], "text": row["content"], "payload": row})
    return docs


def memory_documents(session_id: str, path: Path | None = None) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for row in rows(
        """
        SELECT kind, content, created_at
        FROM memory
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT 30
        """,
        (session_id,),
        path,
    ):
        docs.append(
            {
                "source": "memory",
                "title": f"{row['kind']} {row['created_at']}",
                "text": row["content"],
                "payload": row,
            }
        )
    return docs


def retrieve_context(query: str, session_id: str = "demo", limit: int = 5, path: Path | None = None) -> list[dict[str, Any]]:
    documents = inventory_documents(path) + knowledge_documents(path) + memory_documents(session_id, path)
    ranked = []
    for doc in documents:
        score = cosine_score(query, f"{doc['title']} {doc['text']}")
        if score > 0:
            ranked.append({**doc, "score": round(score, 4)})
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:limit]

