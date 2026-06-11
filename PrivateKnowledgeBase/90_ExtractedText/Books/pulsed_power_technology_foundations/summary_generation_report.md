# Summary Generation Report

## 输入文件

- metadata.yml
- toc.json
- pages_manifest.jsonl
- chunks.jsonl
- formula_notes.md
- extraction_report.md

## 输出文件

- chapter_summaries.md
- book_summary.md
- key_concepts.md
- study_guide.md
- qa_seed.md

## 处理策略

- generated_at: 2026-06-11T09:21:03+00:00
- 使用了 TOC: 是，`toc.json` 包含 271 个条目。
- 是否按章节生成: 是，按 PDF 内置目录识别出 14 个章级/前置范围。
- 是否存在无文本页: 否。
- 是否存在公式抽取异常页: 是，`extraction_report.md` 标记 344 页疑似公式抽取异常。
- 是否备份旧文件: 是，生成 chapter_summaries.md.bak, book_summary.md.bak
- 摘要依据: 以 `toc.json` 章节结构为骨架，结合 `chunks.jsonl` 页码范围、关键词命中、`extraction_report.md` 的无文本页和公式异常页信息生成。

## 需要人工确认的内容

- 章节边界：当前边界来自 PDF 内置目录自动推断，仍需人工确认。
- 公式：公式页较多，涉及公式、方程、符号推导时必须回到原文页面或 PDF 校验。
- 无文本页：当前报告显示无文本页为 0。
- 自动归纳的主题：`book_summary.md`、`key_concepts.md` 和 `study_guide.md` 中的综合性表述均需按具体问题回查原文。
- 关键概念定义：概念定义为导航摘要，不能替代原文证据。

## 注意事项

本次生成的摘要是导航层，不是最终证据层。最终回答必须回到 `chunks.jsonl` 或 `pages/page_xxxx.md`。
