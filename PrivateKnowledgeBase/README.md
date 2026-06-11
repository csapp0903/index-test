# Private Knowledge Base

这是一个私有 PDF 知识库示例项目，用于把《脉冲功率技术基础》这类 PDF 书籍转换成可检索、可引用、可回溯的 Markdown / JSONL 索引。

索引文件只负责定位，最终原文引用必须来自 chunks.jsonl 或 pages/page_xxxx.md。

## 目录结构

```text
PrivateKnowledgeBase/
├─ 01_Books/
│  └─ PulsedPower/
├─ 02_Papers/
│  └─ PulsedPower/
├─ 03_Notes/
│  ├─ Books/
│  ├─ Papers/
│  ├─ Concepts/
│  └─ Topics/
├─ 90_ExtractedText/
│  └─ Books/
├─ 99_Index/
│  └─ topics/
└─ scripts/
```

## 依赖安装

需要 Python 3.10+。主脚本优先使用 PyMuPDF 读取 PDF 自带文本层，使用 PyYAML 写入元数据。

```bash
pip install pymupdf pyyaml
```

## 处理《脉冲功率技术基础》

先把 PDF 放到：

```text
01_Books/PulsedPower/pulsed_power_technology_foundations.pdf
```

然后在 `PrivateKnowledgeBase/` 目录运行：

```bash
python scripts/kb_index_one_book.py \
  --kb-root "." \
  --pdf "01_Books/PulsedPower/pulsed_power_technology_foundations.pdf" \
  --doc-id "pulsed_power_technology_foundations" \
  --title "脉冲功率技术基础" \
  --category "PulsedPower" \
  --language "zh" \
  --overwrite
```

PowerShell 示例：

```powershell
python scripts/kb_index_one_book.py `
  --kb-root "." `
  --pdf "01_Books/PulsedPower/pulsed_power_technology_foundations.pdf" `
  --doc-id "pulsed_power_technology_foundations" `
  --title "脉冲功率技术基础" `
  --category "PulsedPower" `
  --language "zh" `
  --overwrite
```

## 索引文件作用

- `metadata.yml`: 记录书籍元数据、PDF 来源、页数和抽取状态。
- `pages/page_xxxx.md`: 每页单独的原文文本入口。
- `pages_manifest.jsonl`: 每页状态、字符数和文件路径清单。
- `pages.md`: 合并版页面文本，便于人工浏览，不建议默认全文读取。
- `chunks.jsonl`: 面向机器检索的分块文本，回答问题时优先引用这里。
- `toc.json`: PDF 内置目录。
- `chapter_summaries.md`: 章节摘要模板，不作为原文证据。
- `book_summary.md`: 书籍摘要模板，不作为原文证据。
- `formula_notes.md`: 疑似公式抽取异常页提示。
- `extraction_report.md`: 抽取结果统计和警告。

## 推荐使用顺序

ChatGPT、Claude、Codex 或其他 agent 使用知识库时，建议按以下顺序读取：

1. `99_Index/master_index.md`
2. `99_Index/topic_index.md` 或 `99_Index/topics/pulsed_power.md`
3. `90_ExtractedText/Books/pulsed_power_technology_foundations/book_summary.md`
4. `90_ExtractedText/Books/pulsed_power_technology_foundations/chapter_summaries.md`
5. `90_ExtractedText/Books/pulsed_power_technology_foundations/chunks.jsonl`
6. 只在需要核对原文时读取相关 `pages/page_xxxx.md`
7. 只有在校验公式、图表或页码时才回到 PDF 原件

## 辅助脚本

简单关键词检索：

```bash
python scripts/kb_search.py \
  --chunks "90_ExtractedText/Books/pulsed_power_technology_foundations/chunks.jsonl" \
  --query "储能 快速释放 脉冲形成网络 Marx 发生器" \
  --top-k 8
```

生成证据包：

```bash
python scripts/kb_make_evidence_pack.py \
  --chunks "90_ExtractedText/Books/pulsed_power_technology_foundations/chunks.jsonl" \
  --query "脉冲功率系统为什么要先储能再快速释放" \
  --out "evidence_pack.md"
```

检查回答引用：

```bash
python scripts/kb_check_answer.py \
  --evidence evidence_pack.md \
  --answer answer.md \
  --out check_report.md
```
