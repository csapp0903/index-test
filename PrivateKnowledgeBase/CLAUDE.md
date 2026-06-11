# Knowledge Base Agent Rules

## 项目目标

这是一个私有 PDF 知识库项目。目标是把 PDF 书籍和论文转换成可检索、可引用、可回溯的 Markdown / JSONL 索引。

## 核心原则

1. 不要把 PDF 全文打印到对话或终端。
2. 大文本只写入文件，不进入聊天上下文。
3. PDF 原件只作为底层证据，不作为常规检索入口。
4. 常规检索顺序是：
   - 99_Index/
   - book_summary.md / chapter_summaries.md
   - chunks.jsonl
   - pages/page_xxxx.md
   - 必要时才查看 PDF 原件
5. 每个 chunk 必须保留 doc_id、page_start、page_end、source_pdf。
6. 不要编造章节摘要、页码或公式。
7. 如果无法提取某页文本，标记为 [NO_TEXT_EXTRACTED]。
8. 公式抽取不稳定时，只标记，不强行修正。
9. 默认不覆盖已有索引，除非用户明确传入 --overwrite。
10. 最终回答必须引用原文 page 或 chunk，不要只引用 summary。
