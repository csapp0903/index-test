#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a compact evidence pack from KB search results."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from kb_search import excerpt, load_chunks, search_chunks, tokenize


def render_evidence_pack(results: list[dict], query: str, excerpt_chars: int) -> str:
    lines = ["# Evidence Pack", "", f"- query: {query}", ""]
    terms = tokenize(query)
    if not results:
        lines.extend(["未找到匹配证据。", ""])
        return "\n".join(lines)

    for index, item in enumerate(results, start=1):
        chunk = item["chunk"]
        page_start = chunk.get("page_start", "")
        page_end = chunk.get("page_end", page_start)
        lines.extend(
            [
                f"## Evidence {index}",
                "",
                f"- source: {chunk.get('title', '')}",
                f"- page: p.{page_start}-p.{page_end}",
                f"- chunk_id: {chunk.get('chunk_id', '')}",
                f"- excerpt: {excerpt(str(chunk.get('text', '')), terms, excerpt_chars)}",
                "- supports: 待人工判断。",
                "",
            ]
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an evidence pack from chunks.")
    parser.add_argument("--chunks", required=True, help="Path to chunks.jsonl.")
    parser.add_argument("--query", required=True, help="Question or keyword query.")
    parser.add_argument("--out", required=True, help="Output Markdown path.")
    parser.add_argument("--top-k", type=int, default=8, help="Number of evidence items.")
    parser.add_argument("--excerpt-chars", type=int, default=300, help="Excerpt length.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    chunks_path = Path(args.chunks)
    if not chunks_path.exists():
        print(f"找不到 chunks 文件: {chunks_path}", file=sys.stderr)
        return 1

    chunks = load_chunks(chunks_path)
    results = search_chunks(chunks, args.query, args.top_k)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        render_evidence_pack(results, args.query, args.excerpt_chars),
        encoding="utf-8",
        newline="\n",
    )
    print(f"evidence pack written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
