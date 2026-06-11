#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lightweight evidence-pack citation checker."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


PAGE_RE = re.compile(r"\bp\.(\d+)(?:\s*-\s*p?\.(\d+))?", re.IGNORECASE)
CHUNK_RE = re.compile(r"\b[\w-]+_p\d{4}_c\d{3}\b")
FILE_RE = re.compile(r"`([^`]+\.(?:md|jsonl|pdf|yml|json))`")


def page_numbers(text: str) -> set[int]:
    pages: set[int] = set()
    for match in PAGE_RE.finditer(text):
        start = int(match.group(1))
        end = int(match.group(2) or start)
        if end < start:
            start, end = end, start
        pages.update(range(start, end + 1))
    return pages


def render_report(evidence_text: str, answer_text: str) -> str:
    evidence_pages = page_numbers(evidence_text)
    answer_pages = page_numbers(answer_text)
    missing_pages = sorted(answer_pages - evidence_pages)

    evidence_chunks = set(CHUNK_RE.findall(evidence_text))
    answer_chunks = set(CHUNK_RE.findall(answer_text))
    missing_chunks = sorted(answer_chunks - evidence_chunks)

    evidence_files = set(FILE_RE.findall(evidence_text))
    answer_files = set(FILE_RE.findall(answer_text))
    external_files = sorted(answer_files - evidence_files)

    status = "pass" if not missing_pages and not missing_chunks and not external_files else "needs_review"
    lines = [
        "# Check Report",
        "",
        f"- status: {status}",
        f"- evidence_pages: {', '.join('p.' + str(p) for p in sorted(evidence_pages)) or '无'}",
        f"- answer_pages: {', '.join('p.' + str(p) for p in sorted(answer_pages)) or '无'}",
        "",
        "## 页码检查",
        "",
    ]
    if missing_pages:
        lines.append("- answer.md 引用了 evidence_pack.md 中未出现的页码: " + ", ".join(f"p.{p}" for p in missing_pages))
    else:
        lines.append("- 未发现 evidence_pack.md 之外的页码引用。")

    lines.extend(["", "## Chunk 检查", ""])
    if missing_chunks:
        lines.append("- answer.md 引用了 evidence_pack.md 中未出现的 chunk: " + ", ".join(missing_chunks))
    else:
        lines.append("- 未发现 evidence_pack.md 之外的 chunk 引用。")

    lines.extend(["", "## 文件引用检查", ""])
    if external_files:
        lines.append("- answer.md 引用了 evidence_pack.md 中未出现的文件: " + ", ".join(f"`{name}`" for name in external_files))
    else:
        lines.append("- 未发现 evidence_pack.md 之外的文件引用。")

    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check answer citations against an evidence pack.")
    parser.add_argument("--evidence", required=True, help="Path to evidence_pack.md.")
    parser.add_argument("--answer", required=True, help="Path to answer.md.")
    parser.add_argument("--out", required=True, help="Output check_report.md path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    evidence_path = Path(args.evidence)
    answer_path = Path(args.answer)
    if not evidence_path.exists():
        print(f"找不到 evidence 文件: {evidence_path}", file=sys.stderr)
        return 1
    if not answer_path.exists():
        print(f"找不到 answer 文件: {answer_path}", file=sys.stderr)
        return 1

    report = render_report(
        evidence_path.read_text(encoding="utf-8"),
        answer_path.read_text(encoding="utf-8"),
    )
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8", newline="\n")
    print(f"check report written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
