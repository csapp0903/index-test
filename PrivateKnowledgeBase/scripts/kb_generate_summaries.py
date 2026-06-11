#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate navigation summaries for the pulsed power KB."""

from __future__ import annotations

import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


KB_ROOT = Path(__file__).resolve().parents[1]
DOC_ID = "pulsed_power_technology_foundations"
TITLE = "脉冲功率技术基础"
BASE = KB_ROOT / "90_ExtractedText" / "Books" / DOC_ID
INDEX = KB_ROOT / "99_Index"
TOTAL_PAGES = 515


CONCEPT_DEFS = {
    "脉冲功率": "脉冲功率是一类特殊的功率调节技术，核心思想是把初级电源的能量在较长时间内积累，再压缩成高瞬时功率的短脉冲，并按负载的时间特性和能量幅度要求输出。该定义依据引言页的原文表述归纳。",
    "储能": "储能是脉冲功率系统把低功率或较慢供能过程转化为高峰值脉冲输出的前提，书中涉及电容储能、电感储能、机械储能等形式。基于当前提取文本归纳。",
    "快速释放": "快速释放指把已存储的能量通过开关、脉冲形成线、压缩网络或相关装置在短时间内传递给负载，从而形成高峰值功率脉冲。基于当前提取文本归纳。",
    "电容储能": "电容储能利用电容器组储存电场能量，是 Marx 发生器、电容器组和多类脉冲功率装置中的重要储能方式。基于目录和当前提取文本归纳。",
    "电感储能": "电感储能利用电感中的磁场能量，常与断路开关、磁脉冲压缩等主题相关，需要结合第5章和第6章原文进一步确认细节。",
    "开关": "开关控制储能系统与负载或脉冲形成网络之间的能量转移时刻，书中分别讨论闭合开关和断路开关。基于章节摘要归纳。",
    "脉冲形成网络": "当前目录明确包含脉冲形成线、Blumlein PFL、径向和螺旋传输线等内容；“脉冲形成网络”作为检索概念需要回到第3章相关 pages 进一步核对。",
    "Marx 发生器": "Marx 发生器通过多级储能元件的充电和放电实现电压叠加，是书中第1章的核心对象。基于目录和当前提取文本归纳。",
    "传输线": "传输线既是脉冲传播和阻抗匹配对象，也是脉冲形成线和 Blumlein 结构的基础。基于第3章目录和当前提取文本归纳。",
    "负载": "负载需求决定脉冲功率系统需要的电压、电流、脉宽、能量和时间特性；引言中也把负载的特定要求列为定义脉冲功率时的重要因素。",
    "峰值功率": "峰值功率是短脉冲输出中占主导地位的指标之一，与储能时间和释放时间的压缩关系密切。基于引言和章节摘要归纳。",
    "脉冲宽度": "脉冲宽度描述脉冲持续时间，是理解能量压缩、击穿时间效应、脉冲形成和测量的重要参数。基于当前提取文本归纳。",
    "能量压缩": "能量压缩指把较长时间积累的能量转化为短时间释放的高瞬时功率脉冲，是脉冲功率技术的核心工程逻辑。基于引言和第3、第6章主题归纳。",
    "高压绝缘": "高压绝缘涉及气体、固体、液体和真空介质中的耐压与击穿问题，是脉冲功率装置可靠运行的基础。基于第8章和第9章目录归纳。",
    "击穿": "击穿是绝缘介质在强电场或短脉冲条件下失去绝缘能力的过程，书中分别讨论气体、固体、液体和真空中的击穿机理。基于第8章和第9章目录归纳。",
    "测量": "测量部分关注脉冲电压和脉冲电流的获取、诊断和设计示例，需结合第10章原文核对具体测量方法。",
}


CHAPTER_NOTES = {
    "引言": {
        "core": [
            "本部分用于建立全书的概念入口，讨论脉冲功率的定义、历史背景、关键工程特征和应用牵引。",
            "当前提取文本显示，作者并不把脉冲功率简单等同于高峰值或短脉宽，而是强调它是一种满足负载电气要求的特殊功率调节技术。",
            "其基本逻辑是先从初级电源积累能量，再把能量压缩为高瞬时功率脉冲，并利用绝缘材料击穿与时间的关系来实现所需输出。",
            "本部分适合回答“脉冲功率是什么”“为什么要先储能再快速释放”“脉冲功率和普通电源有什么区别”等基础问题。",
        ],
        "concepts": ["脉冲功率", "功率调节", "初级电源", "负载", "峰值功率", "能量压缩", "脉冲宽度"],
        "points": [
            "脉冲功率的定义需要同时考虑能量积累、时间压缩和负载需求。",
            "高峰值功率不是唯一特征，绝缘材料击穿与时间相关性也被列为关键因素。",
            "引言是检索全书基本概念时的优先入口。",
        ],
    },
    "信息来源": {
        "core": [
            "本部分主要说明脉冲功率相关信息来源和文献入口，属于导航性内容。",
            "它不展开具体技术原理，但有助于理解该领域资料分散、工程实践和会议文献重要等背景。",
            "用于写回答时，本部分通常只作为文献脉络参考，不应替代后续章节中的技术论述。",
        ],
        "concepts": ["信息来源", "参考文献", "领域资料", "文献检索"],
        "points": [
            "本节适合作为查找进一步资料的入口。",
            "具体技术定义和工程细节应回到后续章节原文确认。",
            "当前摘要只作导航，不作为最终原文证据。",
        ],
    },
    "第1章Marx发生器和类似Marx的电路": {
        "core": [
            "本章围绕 Marx 发生器及类似电压放大电路展开，是理解多级电容储能、充电和放电形成高压脉冲的核心章节。",
            "章节先介绍简单 Marx 发生器的充电周期、建立过程和放电周期，再讨论负载对放电行为的影响。",
            "随后分析脉冲发生器模型、分布电容、级间耦合、增强触发技术以及复杂 Marx 装置示例。",
            "本章还包含 Hermes、PBFA 等装置示例和设计示例，适合把基础电路原理与实际大型脉冲功率源联系起来。",
            "基于目录和当前提取文本归纳，本章重点是“如何把多个储能级联组织成高压脉冲输出”。",
        ],
        "concepts": ["Marx 发生器", "电容储能", "充电周期", "放电周期", "分布电容", "触发技术", "负载"],
        "points": [
            "Marx 发生器通过多级结构实现电压叠加和脉冲输出。",
            "分布电容和负载会影响输出波形、分压和放电过程。",
            "增强触发和级间耦合是提高同步性和可靠性的关键工程问题。",
            "设计示例可作为理解参数选择和装置结构的入口。",
        ],
    },
    "第2章脉冲变压器": {
        "core": [
            "本章讨论脉冲变压器，重点包括 Tesla 变压器、传输线变压器和电磁感应基础。",
            "这些内容服务于脉冲功率系统中的电压变换、能量耦合和高压脉冲产生。",
            "章节从不同变压器结构切入，再进入电磁感应和设计示例，适合理解脉冲功率系统中“升压与耦合”的技术路径。",
            "涉及具体公式和设计参数时，应回到第2章 pages 原文核对。",
        ],
        "concepts": ["脉冲变压器", "Tesla 变压器", "传输线变压器", "电磁感应", "升压", "耦合"],
        "points": [
            "Tesla 变压器和传输线变压器是本章的两个主要对象。",
            "电磁感应基础用于支撑脉冲变压器设计分析。",
            "设计示例用于连接结构、参数和输出需求。",
        ],
    },
    "第3章脉冲形成线": {
        "core": [
            "本章讨论脉冲形成线和传输线，是理解脉冲宽度、波形形成、阻抗和能量传输的关键章节。",
            "章节覆盖普通传输线、同轴脉冲形成线、Blumlein PFL、径向传输线和螺旋传输线。",
            "后续还讨论 PFL 性能参数、脉冲压缩和设计示例，说明如何利用传输结构把储能转换成满足负载要求的脉冲。",
            "基于章节主题归纳，本章适合回答 PFN/PFL、Blumlein、脉冲压缩和传输线在脉冲形成中作用等问题。",
        ],
        "concepts": ["传输线", "脉冲形成线", "PFL", "Blumlein", "径向传输线", "螺旋传输线", "脉冲压缩", "阻抗"],
        "points": [
            "传输线理论是脉冲形成线分析的基础。",
            "不同 PFL 结构对应不同的波形、阻抗和空间布局约束。",
            "脉冲压缩用于进一步提高峰值功率或改善时间特性。",
            "设计示例是查找参数计算和工程权衡的入口。",
        ],
    },
    "第4章闭合开关": {
        "core": [
            "本章讨论闭合开关，即在需要时把储能部分与负载或脉冲形成结构接通的关键器件。",
            "目录显示本章覆盖火花间隙开关、气体放电开关、固体电介质开关、磁开关和固态开关。",
            "闭合开关决定能量释放时刻、开通速度、抖动、可靠性和重复运行能力，是脉冲功率系统工程实现的核心环节之一。",
            "章节公式和器件参数较多，涉及具体开关性能时需要回到 pages 原文核对。",
        ],
        "concepts": ["闭合开关", "火花间隙开关", "气体放电开关", "固体电介质开关", "磁开关", "固态开关", "时延", "抖动"],
        "points": [
            "闭合开关承担快速接通和能量释放控制功能。",
            "不同开关类型在电压、电流、重复频率和寿命方面存在工程取舍。",
            "时延、抖动和击穿行为是评价高压开关的重要指标。",
        ],
    },
    "第5章断路开关": {
        "core": [
            "本章讨论断路开关，关注通过快速断开电流路径来实现电感储能释放、脉冲成形或能量转移。",
            "章节结构包括典型电路、等效电路、断路开关参数、性能和设计示例。",
            "与闭合开关相比，断路开关更强调从导通状态快速转入高阻状态的能力，常与电感储能和脉冲压缩联系在一起。",
            "具体开关参数和波形关系需要回到第5章相关 page 核对。",
        ],
        "concepts": ["断路开关", "电感储能", "等效电路", "开关参数", "开关性能", "脉冲压缩"],
        "points": [
            "断路开关用于控制电感储能系统中的电流中断和能量转移。",
            "等效电路帮助分析开关过程和输出响应。",
            "性能评价需要关注开断速度、耐压、电流能力和损耗。",
        ],
    },
    "第6章吉瓦级至太瓦级脉冲功率装置": {
        "core": [
            "本章把前面讨论的储能、开关、变换和脉冲形成技术提升到大型装置层面，讨论吉瓦级至太瓦级脉冲功率系统。",
            "目录显示内容包括电容储能、电感储能系统、磁脉冲压缩、感应电压叠加器和直线感应加速器。",
            "本章适合回答大型脉冲功率装置如何组织储能、压缩、叠加和输出的问题。",
            "基于章节主题归纳，装置级设计需要同时考虑储能方式、脉冲压缩、绝缘、同步和负载匹配。",
        ],
        "concepts": ["吉瓦级装置", "太瓦级装置", "电容储能", "电感储能", "磁脉冲压缩", "感应电压叠加器", "直线感应加速器"],
        "points": [
            "大型装置是多个基础单元的系统集成。",
            "磁脉冲压缩和电压叠加是提高输出脉冲能力的重要路径。",
            "加速器类应用体现了脉冲功率与高能束流系统的联系。",
        ],
    },
    "第7章电容器组的能量存储": {
        "core": [
            "本章专门讨论电容器组储能，是理解电容储能系统工程实现的集中章节。",
            "章节覆盖基本公式、电路拓扑、充电电源、电容器组组件、安全性、典型配置和设计示例。",
            "它不仅关心能量容量，也关心电压、电流、连接拓扑、充电方式、放电安全和系统保护。",
            "涉及公式和安全边界时，应回到第7章原文核对。",
        ],
        "concepts": ["电容器组", "电容储能", "储能公式", "电路拓扑", "充电电源", "安全性", "典型配置"],
        "points": [
            "电容器组是许多脉冲功率系统的基础储能模块。",
            "拓扑和组件选择影响输出能力、可靠性和维护安全。",
            "安全性是电容储能系统设计不可分割的一部分。",
        ],
    },
    "第8章气体击穿": {
        "core": [
            "本章讨论气体中的电击穿，是理解气体绝缘、火花间隙和放电开关的基础。",
            "目录显示内容包括气体动力学理论、早期击穿实验、火花放电形成机理、电晕放电、伪火花放电、SF6 击穿特性和绝缘优化设计。",
            "本章把放电物理与开关和绝缘工程连接起来，适合回答气体介质为何会击穿、如何影响开关和绝缘设计等问题。",
            "由于公式和物理模型较多，具体机理和参数应回到相关 pages 核对。",
        ],
        "concepts": ["气体击穿", "气体动力学", "火花放电", "电晕放电", "伪火花放电", "SF6", "绝缘优化"],
        "points": [
            "气体击穿机理支撑火花开关和气体绝缘设计。",
            "不同放电形式对应不同的形成条件和工程影响。",
            "SF6 等气体介质的击穿特性对高压绝缘设计很重要。",
        ],
    },
    "第9章固体、液体和真空中的电击穿": {
        "core": [
            "本章把击穿问题扩展到固体、液体、真空和复合电介质，补全脉冲功率系统中的绝缘介质图景。",
            "章节分别讨论固体、液体、真空和复合电介质中的击穿行为，并提供设计示例。",
            "这些内容与 Marx 发生器、PFL、火花开关、Tesla 变压器和全液体脉冲功率系统等装置密切相关。",
            "基于当前提取文本归纳，本章适合回答不同介质绝缘如何失效、为什么制造装配和污染控制重要等问题。",
        ],
        "concepts": ["固体击穿", "液体击穿", "真空击穿", "复合电介质", "沿面闪络", "绝缘子", "介质"],
        "points": [
            "不同介质的击穿机理和工程约束不同。",
            "液体介质常用于 Marx、PFL 和火花开关等部件。",
            "制造、装配、表面状态和污染会影响绝缘可靠性。",
        ],
    },
    "第10章脉冲电压和电流的测量": {
        "core": [
            "本章讨论脉冲电压和脉冲电流测量，是把脉冲功率从设计走向实验验证和诊断的关键章节。",
            "目录显示本章分为脉冲电压测量、脉冲电流测量和设计示例。",
            "高压短脉冲测量通常需要考虑带宽、响应时间、绝缘、接地、干扰和校准等问题；这些属于学习建议和工程常识，具体方法需回到原文确认。",
            "本章适合回答如何测量高压短脉冲、测量链路会带来哪些误差或安全问题等问题。",
        ],
        "concepts": ["脉冲电压测量", "脉冲电流测量", "诊断", "带宽", "校准", "测量安全"],
        "points": [
            "测量是验证脉冲功率系统输出的重要手段。",
            "电压和电流测量分别有不同的传感和诊断路径。",
            "短脉冲测量对时间响应和电磁干扰特别敏感。",
        ],
    },
    "第11章电磁干扰和干扰抑制": {
        "core": [
            "本章讨论电磁干扰及其抑制，关注脉冲功率系统强瞬态输出带来的耦合、屏蔽和设备布局问题。",
            "目录显示内容包括干扰耦合模式、电磁干扰抑制技术、屏蔽良好的设备拓扑和设计示例。",
            "本章适合回答脉冲功率装置为什么容易产生 EMI、干扰如何耦合、如何通过屏蔽和拓扑降低干扰等问题。",
            "具体抑制方案和设计参数需要回到第11章原文核对。",
        ],
        "concepts": ["电磁干扰", "干扰耦合", "屏蔽", "接地", "抑制技术", "设备拓扑"],
        "points": [
            "强脉冲系统容易通过传导、辐射或结构耦合产生干扰。",
            "抑制技术需要和设备拓扑、屏蔽、接地一起设计。",
            "设计示例可作为工程应用入口。",
        ],
    },
    "第12章电磁干扰抑制的拓扑结构": {
        "core": [
            "本章进一步讨论电磁干扰抑制中的拓扑结构，属于第11章之后的工程设计深化。",
            "目录显示内容包括拓扑设计、屏蔽体端口、孔缝、扩散透射性和设计示例。",
            "本章把 EMI 抑制落实到屏蔽体、端口和孔缝等具体结构问题上，适合回答屏蔽结构为什么会失效、端口和孔缝如何影响干扰抑制等问题。",
            "具体模型、公式和结构尺寸需要回到第12章 pages 原文核对。",
        ],
        "concepts": ["拓扑设计", "屏蔽体", "端口", "孔缝", "扩散透射性", "EMI 抑制"],
        "points": [
            "EMI 抑制不仅是材料问题，也是系统拓扑和结构路径问题。",
            "屏蔽体端口和孔缝会成为干扰泄漏的重要路径。",
            "设计示例用于连接结构设计和抑制效果。",
        ],
    },
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def load_json(path: Path):
    return json.loads(read_text(path))


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def page_set_from_report(report: str, label: str) -> set[int]:
    match = re.search(rf"{re.escape(label)}:\s*(.+)", report)
    if not match:
        return set()
    text = match.group(1)
    if "无" in text:
        return set()
    return {int(n) for n in re.findall(r"p\.(\d+)", text)}


def clean_title(title: str) -> str:
    title = title.replace("?", "")
    title = re.sub(r"^(第\d+章)(\S)", r"\1 \2", title)
    title = re.sub(r"^(\d+(?:\.\d+)+)(\S)", r"\1 \2", title)
    return title.strip()


def backup_targets() -> list[str]:
    targets = [
        "chapter_summaries.md",
        "book_summary.md",
        "key_concepts.md",
        "study_guide.md",
        "qa_seed.md",
    ]
    backed_up = []
    for name in targets:
        path = BASE / name
        if path.exists():
            shutil.copy2(path, BASE / f"{name}.bak")
            backed_up.append(f"{name}.bak")
    return backed_up


def derive_chapters(toc: list[dict]) -> list[dict]:
    level2 = [x for x in toc if x.get("level") == 2 and x.get("page", 0) >= 23]
    chapters = []
    for index, item in enumerate(level2):
        start = int(item["page"])
        end = TOTAL_PAGES
        for later in level2[index + 1 :]:
            if int(later["page"]) > start:
                end = int(later["page"]) - 1
                break
        sections = [
            clean_title(x["title"])
            for x in toc
            if x.get("level") == 3 and start <= int(x.get("page", 0)) <= end
        ]
        chapters.append(
            {
                "title": item["title"],
                "clean_title": clean_title(item["title"]),
                "start": start,
                "end": end,
                "sections": sections,
            }
        )
    return chapters


def chunks_for_range(chunks: list[dict], start: int, end: int) -> list[dict]:
    return [
        chunk
        for chunk in chunks
        if int(chunk.get("page_end", 0)) >= start and int(chunk.get("page_start", 0)) <= end
    ]


def domain_keywords(text: str, concepts: list[str]) -> list[str]:
    candidates = [
        "脉冲功率", "储能", "快速释放", "电容", "电感", "Marx", "发生器", "负载", "峰值功率",
        "脉冲宽度", "脉冲形成", "传输线", "Blumlein", "PFL", "开关", "火花间隙", "气体放电",
        "磁开关", "固态开关", "断路开关", "脉冲压缩", "感应电压叠加器", "直线感应加速器",
        "电容器组", "充电电源", "安全性", "击穿", "电晕", "SF6", "绝缘", "液体", "固体",
        "真空", "测量", "电压测量", "电流测量", "电磁干扰", "屏蔽", "接地", "拓扑",
    ]
    counts = Counter()
    for term in candidates + concepts:
        count = text.count(term)
        if count:
            counts[term] += count
    return [term for term, _ in counts.most_common(10)]


def chapter_warning_note(start: int, end: int, formula_pages: set[int], no_text_pages: set[int]) -> list[str]:
    formula = [p for p in sorted(formula_pages) if start <= p <= end]
    no_text = [p for p in sorted(no_text_pages) if start <= p <= end]
    notes = [
        "章节边界来自 PDF 内置目录自动推断，需人工确认。",
        "本摘要是导航层，不作为最终原文证据；最终引用必须回到 `chunks.jsonl` 或对应 `pages/page_xxxx.md`。",
    ]
    if no_text:
        notes.append("本范围包含无文本页：" + ", ".join(f"p.{p}" for p in no_text) + "。")
    else:
        notes.append("本范围未发现无文本页。")
    if formula:
        sample = ", ".join(f"p.{p}" for p in formula[:20])
        more = " 等" if len(formula) > 20 else ""
        notes.append(f"本范围有 {len(formula)} 页被标记为疑似公式抽取异常：{sample}{more}，涉及公式时需人工核对。")
    else:
        notes.append("本范围未被公式检测规则标记。")
    return notes


def render_chapter_summaries(chapters: list[dict], chunks: list[dict], formula_pages: set[int], no_text_pages: set[int]) -> str:
    lines = [
        f"# {TITLE} - Chapter Summaries",
        "",
        "## 说明",
        "",
        "本文件基于 `toc.json`、`chunks.jsonl`、`pages_manifest.jsonl` 和少量页码定位信息生成，用于快速定位知识，不作为最终原文证据。最终回答和引用必须回到 `chunks.jsonl` 或 `pages/page_xxxx.md`。",
        "",
        "章节边界来自 PDF 内置目录自动推断，所有页码范围均需人工确认。",
        "",
    ]
    for chapter in chapters:
        raw_title = chapter["title"]
        hint = CHAPTER_NOTES.get(raw_title, {})
        chapter_chunks = chunks_for_range(chunks, chapter["start"], chapter["end"])
        text = "\n".join(str(c.get("text", "")) for c in chapter_chunks)
        keywords = domain_keywords(text, hint.get("concepts", []))
        if not keywords:
            keywords = hint.get("concepts", [])[:]
        lines.extend(
            [
                f"## {chapter['clean_title']}",
                "",
                "### Page Range",
                "",
                f"p.{chapter['start']}-p.{chapter['end']}",
                "",
                "### 本章核心内容",
                "",
            ]
        )
        for sentence in hint.get("core", ["待人工确认。"]):
            lines.append(sentence)
        if chapter["sections"]:
            lines.append("目录显示本范围包含的主要小节包括：" + "、".join(chapter["sections"][:10]) + ("等。" if len(chapter["sections"]) > 10 else "。"))
        lines.extend(["", "### 关键概念", ""])
        for concept in (hint.get("concepts", []) + [k for k in keywords if k not in hint.get("concepts", [])])[:10]:
            lines.append(f"- {concept}")
        lines.extend(["", "### 重要知识点", ""])
        for idx, point in enumerate(hint.get("points", ["待人工确认。"]), start=1):
            lines.append(f"{idx}. {point}")
        lines.extend(["", "### 适合回答的问题", ""])
        q_title = chapter["clean_title"]
        default_questions = [
            f"{q_title}主要解决什么问题？",
            f"{q_title}中的关键概念如何相互关联？",
            f"工程实践中查阅{q_title}时应优先看哪些页码范围？",
        ]
        for question in default_questions:
            lines.append(f"- {question}")
        lines.extend(["", "### 推荐检索关键词", ""])
        for keyword in keywords[:10]:
            lines.append(f"- {keyword}")
        lines.extend(
            [
                "",
                "### 原文入口",
                "",
                "- `chunks.jsonl`",
                f"- `pages/page_{chapter['start']:04d}.md` ~ `pages/page_{chapter['end']:04d}.md`",
                "",
                "### 注意事项",
                "",
            ]
        )
        for note in chapter_warning_note(chapter["start"], chapter["end"], formula_pages, no_text_pages):
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines)


def render_book_summary(chapters: list[dict]) -> str:
    chapter_list = "\n".join(f"- p.{ch['start']}-p.{ch['end']}: {ch['clean_title']}" for ch in chapters)
    return f"""# {TITLE} - Book Summary

## 说明

本文件是基于 `chunks.jsonl`、`pages/page_xxxx.md` 和 `chapter_summaries.md` 生成的书籍级摘要，用于快速定位知识，不作为最终原文证据。最终回答和引用必须回到 `chunks.jsonl` 或 `pages/page_xxxx.md`。

## 这本书主要讲什么

《{TITLE}》围绕脉冲功率系统的基本概念、关键组成单元、典型装置、绝缘击穿、测量诊断和电磁干扰抑制展开。基于当前提取文本归纳，书中的核心思想是：把能量先以相对较长的时间储存在电容、电感或相关介质中，再通过开关、脉冲形成线、压缩和叠加等方式在短时间内释放到负载，形成高瞬时功率脉冲。全书从引言中的定义和领域背景开始，随后重点讨论 Marx 发生器、脉冲变压器、脉冲形成线、闭合开关和断路开关等基础部件。中部章节进一步讨论吉瓦级至太瓦级装置和电容器组储能，把单元技术提升到系统级。后半部分转向气体、固体、液体和真空介质中的击穿与绝缘问题，并讨论脉冲电压/电流测量。最后两章关注电磁干扰、屏蔽、拓扑和干扰抑制，说明强瞬态系统在工程部署中需要同时考虑测量可靠性和电磁兼容。

## 核心主线

以下主线为基于章节摘要归纳，需结合原文进一步确认细节：

1. 脉冲功率的基本概念：引言说明脉冲功率是满足负载要求的特殊功率调节技术。
2. 储能：Marx 发生器、电容器组、电容储能和电感储能构成能量积累基础。
3. 快速开关：闭合开关和断路开关控制能量释放或电流中断。
4. 脉冲形成：传输线、PFL、Blumlein 和脉冲压缩用于塑造脉冲时间特性。
5. 传输与负载：负载需求决定电压、电流、能量、脉宽和阻抗匹配。
6. 典型装置或应用：大型吉瓦级至太瓦级装置、感应电压叠加器和直线感应加速器体现系统集成。
7. 绝缘、测量与干扰抑制：击穿、诊断和 EMI 控制支撑装置可靠运行。

## 适合回答的问题

- 脉冲功率是什么，以及为什么要先储能再快速释放。
- Marx 发生器、脉冲变压器、PFL/Blumlein、开关和电容器组分别承担什么功能。
- 闭合开关、断路开关和脉冲形成线如何影响输出脉冲。
- 高压绝缘、气体/液体/固体/真空击穿与脉冲功率系统有什么关系。
- 如何理解大型脉冲功率装置的储能、压缩、叠加和测量诊断。
- 脉冲功率系统为什么容易产生电磁干扰，以及如何从屏蔽和拓扑角度抑制。

## 不适合回答的问题

- 普通低压模拟电路细节
- 运算放大器设计
- 小信号放大器
- 与本书内容无关的问题
- 需要图片、图表或复杂公式精确复原的问题，除非回到 PDF 或人工校验

## 关键主题

- 脉冲功率
- 储能
- 快速释放
- 高压开关
- 脉冲形成线 / PFL / Blumlein
- Marx 发生器
- 脉冲变压器
- 传输线
- 负载
- 绝缘与击穿
- 电容器组
- 脉冲电压和电流测量
- 电磁干扰和屏蔽拓扑

## 推荐检索路径

当用户询问基础定义时：

1. 先查 `book_summary.md`
2. 再查 `chapter_summaries.md`
3. 再查 `chunks.jsonl`
4. 最后查对应 `pages/page_xxxx.md`

当用户要求原文引用时：

1. 不要只引用本摘要。
2. 必须回到 `chunks.jsonl` 或 `pages/page_xxxx.md`。

## 学习建议

初学者可以先读引言建立“储能、压缩、负载匹配”的基本图景，再读第1章 Marx 发生器理解典型高压脉冲源。随后建议依次读第3章脉冲形成线、第4章闭合开关、第5章断路开关和第7章电容器组，把储能、开关和脉冲形成串起来。具备基本系统概念后，再读第8章和第9章理解绝缘与击穿问题，读第10章理解测量诊断，最后读第11章和第12章了解 EMI 抑制与工程部署。以上为学习建议，不等同于原文直接要求。

## 工程应用关联

- 高压脉冲源：第1章、第2章、第3章和第6章可作为主要入口。
- 电容储能：第1章和第7章是重点入口，第6章也涉及大型装置储能。
- 开关器件：第4章闭合开关和第5章断路开关是主要入口。
- 脉冲形成：第3章是主要入口，第6章中的磁脉冲压缩也相关。
- 放电负载：引言、第1章和各设计示例涉及负载需求，具体细节需要原文进一步确认。
- 测量与安全：第7章涉及安全性，第10章涉及测量，第11章和第12章涉及 EMI 与屏蔽。安全细节必须回到原文和工程规范进一步确认。

## 章节导航

{chapter_list}
"""


def find_concept_ranges(chunks: list[dict], concept: str) -> list[tuple[int, int]]:
    terms = [concept]
    if concept == "脉冲形成网络":
        terms += ["脉冲形成线", "PFL", "Blumlein"]
    if concept == "快速释放":
        terms += ["快速", "释放", "高瞬时功率", "脉冲压缩"]
    if concept == "测量":
        terms += ["电压测量", "电流测量", "诊断"]
    ranges = []
    for chunk in chunks:
        text = str(chunk.get("text", ""))
        if any(term in text for term in terms):
            ranges.append((int(chunk["page_start"]), int(chunk["page_end"])))
    merged = []
    for start, end in sorted(ranges):
        if not merged or start > merged[-1][1] + 3:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return [(a, b) for a, b in merged[:4]]


def render_key_concepts(chunks: list[dict]) -> str:
    lines = [
        f"# {TITLE} - Key Concepts",
        "",
        "## 说明",
        "",
        "本文件用于快速定位关键概念，不作为最终原文证据。最终引用必须回到 `chunks.jsonl` 或 `pages/page_xxxx.md`。",
        "",
    ]
    keyword_map = {
        "脉冲功率": ["脉冲功率", "峰值功率", "能量压缩", "负载"],
        "储能": ["储能", "能量存储", "电容储能", "电感储能"],
        "快速释放": ["快速释放", "脉冲压缩", "高瞬时功率", "负载"],
        "电容储能": ["电容储能", "电容器组", "1/2CV2", "充电电源"],
        "电感储能": ["电感储能", "断路开关", "1/2LI2", "磁脉冲压缩"],
        "开关": ["闭合开关", "断路开关", "火花间隙", "磁开关", "固态开关"],
        "脉冲形成网络": ["脉冲形成线", "PFL", "Blumlein", "传输线", "脉冲压缩"],
        "Marx 发生器": ["Marx 发生器", "充电周期", "放电周期", "分布电容"],
        "传输线": ["传输线", "同轴脉冲形成线", "Blumlein", "阻抗"],
        "负载": ["负载", "电气需求", "阻抗匹配", "输出脉冲"],
        "峰值功率": ["峰值功率", "平均功率", "瞬时功率", "脉冲宽度"],
        "脉冲宽度": ["脉冲宽度", "时间特性", "短脉冲", "击穿"],
        "能量压缩": ["能量压缩", "脉冲压缩", "高瞬时功率", "储能"],
        "高压绝缘": ["高压绝缘", "气体击穿", "固体击穿", "液体击穿", "真空击穿"],
        "击穿": ["击穿", "火花放电", "电晕放电", "SF6", "沿面闪络"],
        "测量": ["脉冲电压测量", "脉冲电流测量", "诊断", "校准"],
    }
    for concept, definition in CONCEPT_DEFS.items():
        ranges = find_concept_ranges(chunks, concept)
        lines.extend([f"## {concept}", "", "### 简要定义", "", definition, "", "### 相关章节 / 页码范围", ""])
        if ranges:
            for start, end in ranges:
                lines.append(f"- p.{start}-p.{end}")
        else:
            lines.append("- 未在当前提取文本中确认。")
        lines.extend(["", "### 推荐检索关键词", ""])
        for keyword in keyword_map.get(concept, [concept]):
            lines.append(f"- {keyword}")
        first_page = ranges[0][0] if ranges else None
        lines.extend(["", "### 原文入口", "", "- `chunks.jsonl`"])
        if first_page:
            lines.append(f"- `pages/page_{first_page:04d}.md`")
        else:
            lines.append("- 未在当前提取文本中确认。")
        lines.extend(["", "---", ""])
    return "\n".join(lines)


def render_study_guide(chapters: list[dict]) -> str:
    def ref(title_part: str) -> str:
        for ch in chapters:
            if title_part in ch["clean_title"]:
                return f"{ch['clean_title']}（p.{ch['start']}-p.{ch['end']}）"
        return f"{title_part}（待人工确认）"

    return f"""# {TITLE} - Study Guide

## 说明

本文件是学习导读和提问导航，不作为最终原文证据。最终引用必须回到 `chunks.jsonl` 或 `pages/page_xxxx.md`。

## 适合谁学习

本书适合希望理解脉冲功率源、储能、快速开关、脉冲形成、高压绝缘、测量诊断和电磁干扰抑制的学习者。更具体地说，适合高电压技术、强电磁环境、粒子束与加速器、脉冲电源、等离子体应用以及相关工程系统方向的研究人员或工程人员。上述为基于章节内容的学习建议，不是原文直接表述。

## 学习前置知识

- 电路基础：学习建议。
- 电容、电感与能量存储：学习建议。
- 电磁场基础：学习建议。
- 高电压技术基础：学习建议。
- 开关器件基础：学习建议。
- 传输线基础：学习建议。
- 基本测量与实验安全意识：学习建议。

## 推荐学习路线

### 第一阶段：建立整体概念

推荐章节：
- 引言（p.23-p.25）
- {ref("Marx")}

学习目标：
- 理解脉冲功率不是单纯“大功率”，而是储能、时间压缩和负载匹配的功率调节技术。
- 通过 Marx 发生器建立多级储能和高压脉冲输出的直观模型。

### 第二阶段：理解储能与快速释放

推荐章节：
- {ref("电容器组")}
- {ref("吉瓦级")}
- {ref("断路开关")}

学习目标：
- 理解电容储能、电感储能和大型装置中能量组织方式。
- 理解开关和脉冲压缩如何把储能转换为短时高峰值输出。

### 第三阶段：理解脉冲形成与开关

推荐章节：
- {ref("脉冲形成线")}
- {ref("闭合开关")}
- {ref("脉冲变压器")}

学习目标：
- 理解 PFL、Blumlein 和传输线结构如何形成所需脉冲。
- 理解闭合开关、变压器和传输结构在系统中的协同关系。

### 第四阶段：结合工程应用

推荐章节：
- {ref("气体击穿")}
- {ref("固体、液体和真空")}
- {ref("测量")}
- {ref("电磁干扰和干扰抑制")}
- {ref("拓扑结构")}

学习目标：
- 理解高压绝缘和击穿是装置可靠性的基础。
- 理解测量诊断和 EMI 抑制对脉冲功率实验和工程部署的重要性。

## 常见问题

- 什么是脉冲功率？
- 为什么要先储能再快速释放？
- 为什么快速开关很重要？
- PFN/PFL 和 Marx 发生器分别解决什么问题？
- 脉冲功率和普通电源有什么区别？
- 为什么绝缘和击穿问题在脉冲功率系统中特别重要？
- 高压短脉冲应该如何测量？

## 使用本知识库提问的推荐方式

- 请使用我的 PrivateKnowledgeBase 知识库回答：脉冲功率是什么？回答必须给出原文页码引用。
- 请按索引定位后回答：Marx 发生器如何实现电压叠加？请引用对应 pages。
- 请先检索 chunks，再查相关 pages：PFL 和 Blumlein PFL 的作用有什么区别？
- 请使用章节摘要定位，再查原文：闭合开关和断路开关分别解决什么问题？
- 请回答并标注证据页：为什么脉冲功率系统需要重视击穿、测量和电磁干扰？

提醒：最终引用需要回到 `chunks.jsonl` 或 `pages/page_xxxx.md`，不要只引用本导读。
"""


def render_qa_seed() -> str:
    return """# 脉冲功率技术基础 - QA Seed

## 基础概念问题

1. 脉冲功率是什么？
2. 脉冲功率系统为什么要先储能再快速释放？
3. 峰值功率和平均功率有什么区别？
4. 脉冲宽度为什么会影响系统设计？
5. 负载需求如何影响脉冲功率源设计？

## 储能相关问题

1. 电容储能在脉冲功率系统中起什么作用？
2. 电感储能和电容储能有什么区别？
3. 储能密度为什么重要？
4. 电容器组拓扑会影响哪些系统性能？
5. 电容器组安全设计需要关注哪些问题？

## 开关相关问题

1. 快速开关在脉冲功率系统中起什么作用？
2. 开关速度如何影响输出脉冲？
3. 高压开关面临哪些工程问题？
4. 闭合开关和断路开关有什么区别？
5. 火花间隙开关、磁开关和固态开关各自适合什么场景？

## 脉冲形成相关问题

1. PFN/PFL 是什么？
2. Marx 发生器解决什么问题？
3. 传输线在脉冲形成中有什么作用？
4. Blumlein PFL 的主要用途是什么？
5. 脉冲压缩为什么能提高瞬时功率？

## 绝缘、击穿与测量问题

1. 气体击穿为什么是火花开关和绝缘设计的基础？
2. 固体、液体和真空击穿各有什么工程影响？
3. 测量高压短脉冲时要注意什么？
4. 脉冲电压测量和脉冲电流测量分别关注什么？
5. 公式抽取异常页中的公式如何人工核验？

## 工程应用问题

1. 脉冲功率系统有哪些典型应用？
2. 吉瓦级至太瓦级脉冲功率装置由哪些关键单元组成？
3. 感应电压叠加器和直线感应加速器与脉冲功率有什么关系？
4. 电磁干扰为什么在脉冲功率系统中重要？
5. 屏蔽体端口和孔缝为什么会影响 EMI 抑制效果？

## 推荐提问模板

```text
请使用我的 PrivateKnowledgeBase 知识库回答：

【问题】

规则：
1. 先查 99_Index。
2. 再查相关 book_summary / chapter_summaries。
3. 再查 chunks.jsonl。
4. 最后只读相关 pages/page_xxxx.md。
5. 不要直接读 PDF，不要读整本 pages.md。
6. 回答必须给出原文页码引用。
```
"""


def update_indexes() -> None:
    extracted = f"90_ExtractedText/Books/{DOC_ID}"
    book_index = f"""# Book Index

## {TITLE}

- doc_id: {DOC_ID}
- type: book
- category: PulsedPower
- language: zh
- source_pdf: `01_Books/PulsedPower/pulsed_power_technology_foundations.pdf`
- extracted_dir: `{extracted}/`
- book_summary: `{extracted}/book_summary.md`
- chapter_summaries: `{extracted}/chapter_summaries.md`
- key_concepts: `{extracted}/key_concepts.md`
- study_guide: `{extracted}/study_guide.md`
- qa_seed: `{extracted}/qa_seed.md`
- chunks: `{extracted}/chunks.jsonl`
- pages: `{extracted}/pages/`

## 说明

这些摘要和索引用于定位知识，不作为最终原文证据。最终回答必须回到 `chunks.jsonl` 或 `pages/page_xxxx.md`。
"""
    topic_index = f"""# Topic Index

## PulsedPower / 脉冲功率

- topic_file: `topics/pulsed_power.md`
- 相关书籍：
  - {TITLE}
- 推荐检索顺序：
  1. `topics/pulsed_power.md`
  2. `{extracted}/book_summary.md`
  3. `{extracted}/chapter_summaries.md`
  4. `{extracted}/key_concepts.md`
  5. `{extracted}/study_guide.md`
  6. `{extracted}/qa_seed.md`
  7. `{extracted}/chunks.jsonl`
  8. `{extracted}/pages/`

## 说明

这些摘要和索引用于定位知识，不作为最终原文证据。最终回答必须回到 `chunks.jsonl` 或 `pages/page_xxxx.md`。
"""
    topic = f"""# Pulsed Power Topic Index

## {TITLE}

- doc_id: {DOC_ID}
- 适用范围：
  - 脉冲功率基本概念
  - 储能与快速释放
  - 高压开关
  - 脉冲形成线 / 脉冲形成网络
  - Marx 发生器
  - 传输线与脉冲形成
  - 高压绝缘与击穿
  - 脉冲电压和电流测量
  - 电磁干扰抑制
- 推荐入口：
  - `{extracted}/book_summary.md`
  - `{extracted}/chapter_summaries.md`
  - `{extracted}/key_concepts.md`
  - `{extracted}/study_guide.md`
  - `{extracted}/qa_seed.md`
  - `{extracted}/chunks.jsonl`
  - `{extracted}/pages/`
- 注意：
  - 这些摘要和索引用于定位知识，不作为最终原文证据。
  - 最终回答必须回到 `chunks.jsonl` 或 `pages/page_xxxx.md` 查找原文依据。
"""
    write_text(INDEX / "book_index.md", book_index)
    write_text(INDEX / "topic_index.md", topic_index)
    write_text(INDEX / "topics" / "pulsed_power.md", topic)


def render_report(chapters: list[dict], backed_up: list[str], formula_pages: set[int], no_text_pages: set[int]) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return f"""# Summary Generation Report

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

- generated_at: {generated_at}
- 使用了 TOC: 是，`toc.json` 包含 271 个条目。
- 是否按章节生成: 是，按 PDF 内置目录识别出 {len(chapters)} 个章级/前置范围。
- 是否存在无文本页: {'是，需人工确认。' if no_text_pages else '否。'}
- 是否存在公式抽取异常页: 是，`extraction_report.md` 标记 {len(formula_pages)} 页疑似公式抽取异常。
- 是否备份旧文件: {'是，生成 ' + ', '.join(backed_up) if backed_up else '未发现需备份的旧摘要文件。'}
- 摘要依据: 以 `toc.json` 章节结构为骨架，结合 `chunks.jsonl` 页码范围、关键词命中、`extraction_report.md` 的无文本页和公式异常页信息生成。

## 需要人工确认的内容

- 章节边界：当前边界来自 PDF 内置目录自动推断，仍需人工确认。
- 公式：公式页较多，涉及公式、方程、符号推导时必须回到原文页面或 PDF 校验。
- 无文本页：当前报告显示无文本页为 0。
- 自动归纳的主题：`book_summary.md`、`key_concepts.md` 和 `study_guide.md` 中的综合性表述均需按具体问题回查原文。
- 关键概念定义：概念定义为导航摘要，不能替代原文证据。

## 注意事项

本次生成的摘要是导航层，不是最终证据层。最终回答必须回到 `chunks.jsonl` 或 `pages/page_xxxx.md`。
"""


def main() -> int:
    print("[1/6] Loading metadata and TOC...")
    toc = load_json(BASE / "toc.json")
    _metadata = read_text(BASE / "metadata.yml")
    _manifest = read_text(BASE / "pages_manifest.jsonl")
    report = read_text(BASE / "extraction_report.md")
    formula_pages = page_set_from_report(report, "疑似公式页")
    no_text_pages = page_set_from_report(report, "无文本页")

    print("[2/6] Reading chunk index...")
    chunks = load_jsonl(BASE / "chunks.jsonl")
    chapters = derive_chapters(toc)

    print("[3/6] Building chapter summaries...")
    backed_up = backup_targets()
    chapter_summary_text = render_chapter_summaries(chapters, chunks, formula_pages, no_text_pages)
    write_text(BASE / "chapter_summaries.md", chapter_summary_text)

    print("[4/6] Building book summary...")
    write_text(BASE / "book_summary.md", render_book_summary(chapters))

    print("[5/6] Building concept and study guide files...")
    write_text(BASE / "key_concepts.md", render_key_concepts(chunks))
    write_text(BASE / "study_guide.md", render_study_guide(chapters))
    write_text(BASE / "qa_seed.md", render_qa_seed())
    write_text(BASE / "summary_generation_report.md", render_report(chapters, backed_up, formula_pages, no_text_pages))

    print("[6/6] Updating global indexes...")
    update_indexes()
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
