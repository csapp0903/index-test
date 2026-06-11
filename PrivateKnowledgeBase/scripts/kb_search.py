#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple keyword search over KB chunks."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def load_chunks(path: Path) -> list[dict]:
    chunks: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                chunks.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at line {line_no}: {exc}") from exc
    return chunks


def tokenize(query: str) -> list[str]:
    terms = re.findall(r"[\w\u4e00-\u9fff]+", query.lower())
    return [term for term in terms if term]


def score_chunk(chunk: dict, terms: list[str]) -> int:
    haystack = " ".join(
        str(chunk.get(key, ""))
        for key in ("title", "chapter", "section", "text")
    ).lower()
    score = 0
    for term in terms:
        score += haystack.count(term)
    return score


def excerpt(text: str, terms: list[str], limit: int) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= limit:
        return cleaned

    lower = cleaned.lower()
    first_hit = min(
        [lower.find(term) for term in terms if lower.find(term) >= 0] or [0]
    )
    start = max(0, first_hit - limit // 3)
    end = min(len(cleaned), start + limit)
    snippet = cleaned[start:end].strip()
    if start > 0:
        snippet = "…" + snippet
    if end < len(cleaned):
        snippet += "…"
    return snippet


def search_chunks(chunks: list[dict], query: str, top_k: int = 8) -> list[dict]:
    terms = tokenize(query)
    if not terms:
        return []

    scored: list[tuple[int, dict]] = []
    for chunk in chunks:
        score = score_chunk(chunk, terms)
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda item: (-item[0], item[1].get("page_start", 0)))
    return [{"score": score, "chunk": chunk} for score, chunk in scored[:top_k]]


def render_results(results: list[dict], query: str, excerpt_chars: int) -> str:
    lines = ["# Search Results", "", f"- query: {query}", ""]
    if not results:
        lines.extend(["未找到匹配结果。", ""])
        return "\n".join(lines)

    terms = tokenize(query)
    for index, item in enumerate(results, start=1):
        chunk = item["chunk"]
        page_start = chunk.get("page_start", "")
        page_end = chunk.get("page_end", page_start)
        lines.extend(
            [
                f"## Result {index}",
                "",
                f"- source: {chunk.get('title', '')}",
                f"- page: p.{page_start}-p.{page_end}",
                f"- chunk_id: {chunk.get('chunk_id', '')}",
                f"- score: {item['score']}",
                f"- excerpt: {excerpt(str(chunk.get('text', '')), terms, excerpt_chars)}",
                "",
            ]
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search private KB chunks.")
    parser.add_argument("--chunks", required=True, help="Path to chunks.jsonl.")
    parser.add_argument("--query", required=True, help="Keyword query.")
    parser.add_argument("--top-k", type=int, default=8, help="Number of results.")
    parser.add_argument("--excerpt-chars", type=int, default=300, help="Excerpt length.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = Path(args.chunks)
    if not path.exists():
        print(f"找不到 chunks 文件: {path}", file=sys.stderr)
        return 1
    try:
        chunks = load_chunks(path)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    results = search_chunks(chunks, args.query, args.top_k)
    print(render_results(results, args.query, args.excerpt_chars))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
