#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a minimal private PDF knowledge-base index for one book."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


NO_TEXT = "[NO_TEXT_EXTRACTED]"
MIN_CHUNK_CHARS = 800
TARGET_CHUNK_CHARS = 1200
MAX_CHUNK_CHARS = 1500
OVERLAP_CHARS = 150
MAX_CHUNK_PAGES = 3


try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover - exercised by local environment only
    fitz = None

try:
    import yaml
except ImportError:  # pragma: no cover - exercised by local environment only
    yaml = None


@dataclass
class PageRecord:
    page: int
    text: str
    char_count: int
    status: str
    path: str


@dataclass
class TextUnit:
    page_start: int
    page_end: int
    text: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract one PDF text layer and build a private KB index."
    )
    parser.add_argument("--kb-root", required=True, help="Knowledge-base root directory.")
    parser.add_argument("--pdf", required=True, help="PDF path relative to kb-root.")
    parser.add_argument("--doc-id", required=True, help="Stable document id.")
    parser.add_argument("--title", required=True, help="Book title.")
    parser.add_argument("--category", required=True, help="Book category.")
    parser.add_argument("--language", default="zh", help="Language code.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite previously generated files for this document.",
    )
    return parser.parse_args()


def require_dependencies() -> bool:
    missing: list[str] = []
    if fitz is None:
        missing.append("pymupdf")
    if yaml is None:
        missing.append("pyyaml")
    if not missing:
        return True

    print("缺少依赖，尚未运行抽取。请先安装：", file=sys.stderr)
    print("pip install pymupdf pyyaml", file=sys.stderr)
    print(f"缺少: {', '.join(missing)}", file=sys.stderr)
    return False


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_rel(path_text: str) -> str:
    return path_text.replace("\\", "/").strip("/")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")


def yaml_block(data: dict) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False).strip()


def markdown_page(title: str, doc_id: str, source_pdf: str, page: int, text: str) -> str:
    front_matter = {
        "type": "page_text",
        "doc_id": doc_id,
        "title": title,
        "page": page,
        "source_pdf": source_pdf,
    }
    return (
        f"---\n{yaml_block(front_matter)}\n---\n\n"
        f"# {title} - Page {page}\n\n"
        f"{text.rstrip()}\n"
    )


def extract_pages(
    pdf_doc: "fitz.Document",
    pages_dir: Path,
    title: str,
    doc_id: str,
    source_pdf: str,
) -> list[PageRecord]:
    records: list[PageRecord] = []
    for index in range(pdf_doc.page_count):
        page_no = index + 1
        page = pdf_doc.load_page(index)
        extracted = page.get_text("text") or ""
        extracted = extracted.replace("\r\n", "\n").replace("\r", "\n").strip()
        if extracted:
            text = extracted
            status = "ok"
            char_count = len(extracted)
        else:
            text = NO_TEXT
            status = "no_text"
            char_count = 0

        rel_path = f"pages/page_{page_no:04d}.md"
        write_text(
            pages_dir / f"page_{page_no:04d}.md",
            markdown_page(title, doc_id, source_pdf, page_no, text),
        )
        records.append(PageRecord(page_no, text, char_count, status, rel_path))
    return records


def split_long_text(text: str) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        paragraphs = [line.strip() for line in text.splitlines() if line.strip()]

    pieces: list[str] = []
    buffer: list[str] = []
    buffer_len = 0

    def flush_buffer() -> None:
        nonlocal buffer, buffer_len
        if buffer:
            pieces.append("\n\n".join(buffer).strip())
            buffer = []
            buffer_len = 0

    for para in paragraphs:
        if len(para) > MAX_CHUNK_CHARS:
            flush_buffer()
            start = 0
            while start < len(para):
                end = min(start + TARGET_CHUNK_CHARS, len(para))
                pieces.append(para[start:end].strip())
                if end >= len(para):
                    break
                start = max(end - OVERLAP_CHARS, start + 1)
            continue

        sep_len = 2 if buffer else 0
        if buffer_len + sep_len + len(para) <= MAX_CHUNK_CHARS:
            buffer.append(para)
            buffer_len += sep_len + len(para)
        else:
            flush_buffer()
            buffer.append(para)
            buffer_len = len(para)

    flush_buffer()
    return [piece for piece in pieces if piece]


def page_units(records: list[PageRecord]) -> list[TextUnit]:
    units: list[TextUnit] = []
    for record in records:
        if record.status != "ok":
            continue
        if len(record.text) <= MAX_CHUNK_CHARS:
            units.append(TextUnit(record.page, record.page, record.text))
            continue
        for piece in split_long_text(record.text):
            units.append(TextUnit(record.page, record.page, piece))
    return units


def combine_units(units: list[TextUnit]) -> list[TextUnit]:
    chunks: list[TextUnit] = []
    current: TextUnit | None = None

    for unit in units:
        if current is None:
            current = TextUnit(unit.page_start, unit.page_end, unit.text)
            continue

        page_span = unit.page_end - current.page_start + 1
        combined_text = f"{current.text.rstrip()}\n\n{unit.text.lstrip()}"
        can_merge = page_span <= MAX_CHUNK_PAGES and len(combined_text) <= MAX_CHUNK_CHARS

        if can_merge and len(current.text) < MIN_CHUNK_CHARS:
            current = TextUnit(current.page_start, unit.page_end, combined_text)
            continue

        if can_merge and current.page_start == unit.page_start and len(current.text) < TARGET_CHUNK_CHARS:
            current = TextUnit(current.page_start, unit.page_end, combined_text)
            continue

        chunks.append(current)
        current = TextUnit(unit.page_start, unit.page_end, unit.text)

    if current is not None:
        chunks.append(current)

    return chunks


def add_adjacent_overlap(chunks: list[TextUnit]) -> list[TextUnit]:
    if not chunks:
        return chunks

    overlapped: list[TextUnit] = [chunks[0]]
    for chunk in chunks[1:]:
        prev = overlapped[-1]
        prefix = prev.text[-OVERLAP_CHARS:].strip()
        new_start = min(chunk.page_start, prev.page_end)
        page_span = chunk.page_end - new_start + 1
        if len(prefix) >= 100 and page_span <= MAX_CHUNK_PAGES:
            text = f"{prefix}\n\n{chunk.text.lstrip()}"
            overlapped.append(TextUnit(new_start, chunk.page_end, text))
        else:
            overlapped.append(chunk)
    return overlapped


def build_chunks(
    records: list[PageRecord],
    doc_id: str,
    title: str,
    category: str,
    source_pdf: str,
) -> list[dict]:
    units = page_units(records)
    chunk_units = add_adjacent_overlap(combine_units(units))
    page_counters: dict[int, int] = {}
    chunks: list[dict] = []

    for unit in chunk_units:
        page_counters[unit.page_start] = page_counters.get(unit.page_start, 0) + 1
        chunk_id = f"{doc_id}_p{unit.page_start:04d}_c{page_counters[unit.page_start]:03d}"
        chunks.append(
            {
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "title": title,
                "type": "book",
                "category": category,
                "page_start": unit.page_start,
                "page_end": unit.page_end,
                "chapter": "",
                "section": "",
                "keywords": [],
                "text": unit.text.strip(),
                "source_pdf": source_pdf,
            }
        )
    return chunks


def load_toc(pdf_doc: "fitz.Document") -> list[dict]:
    toc_items: list[dict] = []
    for item in pdf_doc.get_toc(simple=True):
        if len(item) < 3:
            continue
        level, title, page = item[:3]
        toc_items.append({"level": int(level), "title": str(title), "page": int(page)})
    return toc_items


def chapter_summaries(title: str, toc_items: list[dict], total_pages: int) -> str:
    lines = [f"# {title} - Chapter Summaries", ""]
    if not toc_items:
        lines.extend(
            [
                "## 待补充章节",
                "",
                "### Page Range",
                "",
                "待补充。",
                "",
                "### 核心内容",
                "",
                "待补充。",
                "",
                "### 适合回答的问题",
                "",
                "- 待补充。",
                "",
                "### 推荐关键词",
                "",
                "- 待补充。",
                "",
                "### 原文入口",
                "",
                "- `chunks.jsonl`",
                "- `pages/`",
                "",
            ]
        )
        return "\n".join(lines)

    lines.extend(["注：页码范围根据 PDF 目录自动推断，需人工确认。", ""])
    for index, item in enumerate(toc_items):
        next_page = total_pages + 1
        for later in toc_items[index + 1 :]:
            if later["page"] > item["page"]:
                next_page = later["page"]
                break
        page_start = max(1, min(item["page"], total_pages))
        page_end = max(page_start, min(next_page - 1, total_pages))
        heading_level = min(max(item["level"] + 1, 2), 6)
        heading = "#" * heading_level
        lines.extend(
            [
                f"{heading} {item['title']}",
                "",
                "### Page Range",
                "",
                f"p.{page_start}-p.{page_end}",
                "",
                "### 核心内容",
                "",
                "待补充。",
                "",
                "### 适合回答的问题",
                "",
                "- 待补充。",
                "",
                "### 推荐关键词",
                "",
                "- 待补充。",
                "",
                "### 原文入口",
                "",
                "- `chunks.jsonl`",
                f"- `pages/page_{page_start:04d}.md`",
                "",
            ]
        )
    return "\n".join(lines)


def book_summary(title: str) -> str:
    return f"""# {title} - Book Summary

## 主要内容

待补充。

## 适合回答的问题

- 脉冲功率基本概念
- 储能与快速释放
- 脉冲形成网络
- 高压开关
- Marx 发生器
- 传输线与脉冲形成
- 待人工确认和补充

## 不适合回答的问题

- 普通低压模拟电路的详细设计
- 运算放大器应用细节
- 小信号放大器设计
- 待人工确认和补充

## 推荐检索入口

- `chapter_summaries.md`
- `chunks.jsonl`
- `pages/`

## 说明

本文件第一版为索引模板，不能作为原文证据。最终回答必须回到 chunks.jsonl 或 pages/page_xxxx.md 中查找原文依据。
"""


def formula_warning(record: PageRecord) -> bool:
    if record.status != "ok":
        return False
    text = record.text
    symbol_count = len(re.findall(r"[=+\-/\^_∑∫√]", text))
    formula_term = re.search(r"公式|方程|equation|formula|式", text, flags=re.IGNORECASE)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    short_symbol_lines = sum(
        1
        for line in lines
        if len(line) <= 28 and len(re.findall(r"[=+\-/\^_∑∫√]", line)) >= 2
    )
    very_short_lines = sum(1 for line in lines if len(line) <= 6)
    broken_ratio = very_short_lines / max(len(lines), 1)

    return (
        symbol_count >= 18
        or short_symbol_lines >= 3
        or (formula_term is not None and symbol_count >= 2)
        or (len(lines) >= 8 and broken_ratio >= 0.45 and symbol_count >= 4)
    )


def compact_excerpt(text: str, limit: int = 300) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def formula_notes(records: list[PageRecord]) -> tuple[str, list[int]]:
    warning_pages: list[int] = []
    lines = ["# Formula Notes", ""]
    for record in records:
        if not formula_warning(record):
            continue
        warning_pages.append(record.page)
        lines.extend(
            [
                f"## Page {record.page}",
                "",
                "### 原始抽取片段",
                "",
                compact_excerpt(record.text, 300),
                "",
                "### 状态",
                "",
                "疑似公式或公式附近文本，需要人工校验。",
                "",
            ]
        )

    if not warning_pages:
        lines.extend(["未检测到明显疑似公式抽取异常页面。", ""])
    return "\n".join(lines), warning_pages


def pages_combined(title: str, doc_id: str, source_pdf: str, records: list[PageRecord]) -> str:
    front_matter = {
        "type": "extracted_pages",
        "doc_id": doc_id,
        "title": title,
        "source_pdf": source_pdf,
    }
    lines = [
        "---",
        yaml_block(front_matter),
        "---",
        "",
        f"# {title} - Extracted Pages",
        "",
    ]
    for record in records:
        lines.extend(
            [
                f"## Page {record.page} {{#page-{record.page}}}",
                "",
                record.text.rstrip(),
                "",
                "---",
                "",
            ]
        )
    return "\n".join(lines)


def extraction_report(
    doc_id: str,
    title: str,
    source_pdf: str,
    total_pages: int,
    records: list[PageRecord],
    chunks: list[dict],
    toc_items: list[dict],
    formula_pages: list[int],
) -> str:
    no_text_pages = [record.page for record in records if record.status == "no_text"]
    extracted_pages = total_pages - len(no_text_pages)
    no_text_text = ", ".join(f"p.{page}" for page in no_text_pages) if no_text_pages else "无"
    formula_text = ", ".join(f"p.{page}" for page in formula_pages) if formula_pages else "无"

    return f"""# Extraction Report

## 基本信息

- doc_id: {doc_id}
- title: {title}
- source_pdf: {source_pdf}
- total_pages: {total_pages}
- extracted_pages: {extracted_pages}
- no_text_pages: {len(no_text_pages)}
- total_chunks: {len(chunks)}
- toc_items: {len(toc_items)}
- formula_warning_pages: {len(formula_pages)}

## 输出文件

- metadata.yml
- pages/
- pages_manifest.jsonl
- pages.md
- chunks.jsonl
- toc.json
- chapter_summaries.md
- book_summary.md
- formula_notes.md

## 警告

- 无文本页: {no_text_text}
- 疑似公式页: {formula_text}
"""


def write_global_indexes(
    kb_root: Path,
    title: str,
    doc_id: str,
    category: str,
    language: str,
    source_pdf: str,
    overwrite: bool,
) -> None:
    index_dir = kb_root / "99_Index"
    topic_dir = index_dir / "topics"
    extracted_dir = f"90_ExtractedText/Books/{doc_id}"
    files = {
        index_dir
        / "master_index.md": """# Private Knowledge Base - Master Index

## 书籍索引

- `book_index.md`

## 论文索引

- `paper_index.md`

## 主题索引

- `topic_index.md`

## 分类主题

- `topics/pulsed_power.md`

## 使用规则

1. 先读 master_index.md。
2. 再读 topic_index.md 或 topics/<category>.md。
3. 再读 book_summary.md / chapter_summaries.md。
4. 再检索 chunks.jsonl。
5. 最后只读取相关 pages/page_xxxx.md。
6. 不要直接读取 PDF 原件，除非需要校验公式、图表或页码。
""",
        index_dir
        / "book_index.md": f"""# Book Index

## {title}

- doc_id: {doc_id}
- type: book
- category: {category}
- language: {language}
- source_pdf: `{source_pdf}`
- extracted_dir: `{extracted_dir}/`
- book_summary: `{extracted_dir}/book_summary.md`
- chapter_summaries: `{extracted_dir}/chapter_summaries.md`
- chunks: `{extracted_dir}/chunks.jsonl`
- pages: `{extracted_dir}/pages/`
""",
        index_dir / "paper_index.md": "# Paper Index\n\n暂无论文条目。\n",
        index_dir
        / "topic_index.md": f"""# Topic Index

## PulsedPower / 脉冲功率

- topic_file: `topics/pulsed_power.md`
- 相关书籍：
  - {title}
- 推荐检索顺序：
  1. `topics/pulsed_power.md`
  2. `{extracted_dir}/book_summary.md`
  3. `{extracted_dir}/chapter_summaries.md`
  4. `{extracted_dir}/chunks.jsonl`
  5. `{extracted_dir}/pages/`
""",
        topic_dir
        / "pulsed_power.md": f"""# Pulsed Power Topic Index

## {title}

- doc_id: {doc_id}
- 适用范围：
  - 脉冲功率基本概念
  - 储能与快速释放
  - 高压开关
  - 脉冲形成网络
  - Marx 发生器
  - 传输线与脉冲形成
- 推荐入口：
  - `{extracted_dir}/book_summary.md`
  - `{extracted_dir}/chapter_summaries.md`
  - `{extracted_dir}/chunks.jsonl`
  - `{extracted_dir}/pages/`
- 注意：
  - 本文件是导航索引，不是原文证据。
  - 最终回答必须回到 chunks.jsonl 或 pages/page_xxxx.md 查找原文依据。
""",
    }

    for path, content in files.items():
        if path.exists() and not overwrite:
            continue
        write_text(path, content)


def main() -> int:
    args = parse_args()
    if not require_dependencies():
        return 2

    kb_root = Path(args.kb_root).resolve()
    source_pdf = normalize_rel(args.pdf)
    pdf_path = (kb_root / source_pdf).resolve()
    output_rel = f"90_ExtractedText/Books/{args.doc_id}"
    output_dir = kb_root / output_rel
    pages_dir = output_dir / "pages"

    if not pdf_path.exists():
        print(f"找不到 PDF: {pdf_path}", file=sys.stderr)
        return 1

    if output_dir.exists() and not args.overwrite and any(output_dir.iterdir()):
        print(
            f"输出目录已存在: {output_dir}\n"
            "如需重新生成，请传入 --overwrite。",
            file=sys.stderr,
        )
        return 1

    if output_dir.exists() and args.overwrite:
        shutil.rmtree(output_dir)
    pages_dir.mkdir(parents=True, exist_ok=True)

    created_at = now_iso()
    with fitz.open(pdf_path) as pdf_doc:
        total_pages = pdf_doc.page_count
        toc_items = load_toc(pdf_doc)
        records = extract_pages(pdf_doc, pages_dir, args.title, args.doc_id, source_pdf)

    manifest_rows = [
        {
            "doc_id": args.doc_id,
            "title": args.title,
            "page": record.page,
            "path": record.path,
            "char_count": record.char_count,
            "status": record.status,
        }
        for record in records
    ]
    chunks = build_chunks(records, args.doc_id, args.title, args.category, source_pdf)
    formula_markdown, formula_pages = formula_notes(records)
    updated_at = now_iso()

    metadata = {
        "doc_id": args.doc_id,
        "type": "book",
        "title": args.title,
        "authors": [],
        "language": args.language,
        "category": args.category,
        "source_pdf": source_pdf,
        "output_dir": output_rel,
        "status": "extracted",
        "total_pages": total_pages,
        "created_at": created_at,
        "updated_at": updated_at,
    }

    write_text(output_dir / "metadata.yml", yaml_block(metadata) + "\n")
    write_jsonl(output_dir / "pages_manifest.jsonl", manifest_rows)
    write_text(output_dir / "pages.md", pages_combined(args.title, args.doc_id, source_pdf, records))
    write_jsonl(output_dir / "chunks.jsonl", chunks)
    write_text(
        output_dir / "toc.json",
        json.dumps(toc_items, ensure_ascii=False, indent=2) + "\n",
    )
    write_text(
        output_dir / "chapter_summaries.md",
        chapter_summaries(args.title, toc_items, total_pages),
    )
    write_text(output_dir / "book_summary.md", book_summary(args.title))
    write_text(output_dir / "formula_notes.md", formula_markdown)
    write_text(
        output_dir / "extraction_report.md",
        extraction_report(
            args.doc_id,
            args.title,
            source_pdf,
            total_pages,
            records,
            chunks,
            toc_items,
            formula_pages,
        ),
    )
    write_global_indexes(
        kb_root,
        args.title,
        args.doc_id,
        args.category,
        args.language,
        source_pdf,
        args.overwrite,
    )

    no_text_pages = sum(1 for record in records if record.status == "no_text")
    print("索引生成完成")
    print(f"- pages: {total_pages}")
    print(f"- extracted_pages: {total_pages - no_text_pages}")
    print(f"- chunks: {len(chunks)}")
    print(f"- report: {output_rel}/extraction_report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
