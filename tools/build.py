#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 papers/ 里的试卷合成一本书并编译成 PDF。

用法：
    python3 tools/build.py                   # 用根目录唯一的 book*.yaml
    python3 tools/build.py book-期末.yaml     # 用指定的合集定义
    python3 tools/build.py --all             # 根目录所有 book*.yaml
    python3 tools/build.py --keep            # 保留中间目录（默认建在系统临时目录，编完即删）

流程：读 yaml → 挑 papers/*.tex（文件名 = <学年>-<学期>-<考试>-<课程>）→ 学年倒序 → 建临时目录并拷入
tools/preamble.tex 与用到的试卷 → 生成 main.tex → tectonic 编译 → 成品到 out/<书名>.pdf。

合集 yaml 里写 `解答: true` 即出解析版：每题正文之后插入 solutions/<同名>.tex 中对应的
\\begin{solution} 块（按题序一一对应，条数不匹配即报错），题目原文仍以 papers/ 为唯一来源。
"""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PAPERS, SOLUTIONS, TOOLS, OUT = ROOT / "papers", ROOT / "solutions", ROOT / "tools", ROOT / "out"
NAME_RE = re.compile(r"^(\d{4}-\d{4})-(秋冬|春夏)-(.+)-([甲乙丙丁])\.tex$")
PROBLEM_RE = re.compile(r"\\begin\{problem\}")
END_PROBLEM = r"\end{problem}"
SOLUTION_RE = re.compile(r"\\begin\{solution\}(.*?)\\end\{solution\}", re.S)


def die(msg: str) -> None:
    print(f"错误：{msg}", file=sys.stderr)
    raise SystemExit(1)


def collect(flt: dict) -> list[dict]:
    items = []
    for tex in sorted(PAPERS.glob("*.tex")):
        m = NAME_RE.match(tex.name)
        if not m:
            print(f"  ! 文件名不符合约定的文件已跳过：{tex.name}", file=sys.stderr)
            continue
        year, term, exam, course = m.groups()
        if flt.get("考试") and flt["考试"] != exam:
            continue
        if flt.get("学期") and flt["学期"] != term:
            continue
        if flt.get("课程") and flt["课程"] != course:
            continue
        items.append({"year": year, "term": term, "exam": exam, "course": course, "tex": tex})
    items.sort(key=lambda x: -int(x["year"][:4]))
    return items


def body_with_solutions(item: dict) -> str:
    """把一套卷的题目与 solutions/ 里的解析按题序交织成一段可直接 \\input 的正文。"""
    src = SOLUTIONS / item["tex"].name
    if not src.exists():
        die(f"解析版缺少 {src.relative_to(ROOT)}（解析与试卷必须同名一一对应）")
    blocks = SOLUTION_RE.findall(src.read_text(encoding="utf-8"))
    text = item["tex"].read_text(encoding="utf-8")
    n_problem = len(PROBLEM_RE.findall(text))
    if not blocks:
        die(f"{src.name} 里没有 \\begin{{solution}} 块")
    if len(blocks) != n_problem:
        die(f"{src.name}：题目 {n_problem} 道，解析 {len(blocks)} 条，数量不一致")

    out, used = [], 0
    for seg in re.split(r"(\\end\{problem\})", text):
        out.append(seg)
        if seg == END_PROBLEM:
            out.append(f"\n\\begin{{solution}}{blocks[used].rstrip()}\n\\end{{solution}}\n")
            used += 1
    return "".join(out)


def paper_entry(it: dict, solutions: bool) -> str:
    """一套卷的 \\paperhead 头 + \\input 正文，目录条目与页眉随解析版加“解析”二字。"""
    year = it["year"].replace("-", "--")
    label = f"{year} 学年{it['term']}学期（{it['course']}）{it['exam']}" + ("解析" if solutions else "")
    return (f"\\paperhead{{{year}}}{{{it['term']}学期}}{{{it['exam']}}}{{{label}}}\n"
            f"\\input{{papers/{it['tex'].name}}}")


PAPER_TEMPLATE = r"""\documentclass[UTF8,a4paper,11pt]{ctexart}
\input{preamble.tex}
%(solutions)s\renewcommand{\schoolname}{%(school)s}
\renewcommand{\coursename}{%(course)s}
\renewcommand{\booktitle}{%(course)s}
\begin{document}
\paperhead{%(year)s}{%(term)s学期}{%(exam)s}{%(label)s}
\input{papers/%(file)s}
\end{document}
"""


def build_one(work: Path, it: dict, school: str, course_title: str, solutions: bool) -> Path:
    """把单套试卷编成一份 PDF（无封面目录，页眉左侧为校名+课程名）。"""
    year = it["year"].replace("-", "--")
    course_title = course_title.replace("甲", it["course"]) if it["course"] != "甲" else course_title
    label = f"{year} 学年{it['term']}学期（{it['course']}）{it['exam']}" + ("解析" if solutions else "")
    (work / "main.tex").write_text(PAPER_TEMPLATE % {
        "school": school, "course": course_title, "year": year, "term": it["term"],
        "exam": it["exam"], "label": label, "file": it["tex"].name,
        "solutions": "\\solutionsmodetrue\n" if solutions else "",
    }, encoding="utf-8")
    proc = subprocess.run(["tectonic", "-X", "compile", "main.tex", "--outdir", "."],
                          cwd=work, capture_output=True, text=True)
    if proc.returncode != 0:
        print((proc.stdout + proc.stderr)[-2000:])
        die(f"{it['tex'].name} 单卷编译失败")
    suffix = "-解析" if solutions else ""
    target = OUT / (it["tex"].stem + suffix + ".pdf")
    shutil.copy(work / "main.pdf", target)
    return target


def build(book: Path, keep: bool) -> None:
    cfg = yaml.safe_load(book.read_text(encoding="utf-8")) or {}
    solutions = bool(cfg.get("解答"))
    items = collect(cfg.get("筛选") or {})
    if not items:
        die(f"{book.name} 没有匹配到任何试卷")

    title = cfg.get("书名") or book.stem
    courses = sorted({it["course"] for it in items})
    course = cfg.get("课程名", "《线性代数（" + courses[0] + "）》")

    bodies = {it["tex"].name: body_with_solutions(it) if solutions
              else it["tex"].read_text(encoding="utf-8") for it in items}
    counts = [len(PROBLEM_RE.findall(b)) for b in bodies.values()]

    work = Path(tempfile.mkdtemp(prefix="laps-build-"))
    (work / "papers").mkdir()
    shutil.copy(TOOLS / "preamble.tex", work / "preamble.tex")
    for name, body in bodies.items():
        (work / "papers" / name).write_text(body, encoding="utf-8")

    papers_tex = "\n\n".join(paper_entry(it, solutions) for it in items)
    main = (TOOLS / "book-template.tex").read_text(encoding="utf-8")
    for key, val in {
        "SCHOOL": cfg.get("学校", "浙江大学"),
        "COURSE_TITLE": course,
        "HEADER": cfg.get("页眉", title),
        "BOOK_TITLE": cfg.get("大标题", "历年试题合集"),
        "SUBTITLE": cfg.get("副标题", "题目卷"),
        "COUNT_LINE": f"共 {len(items)} 套 · {sum(counts)} 题" + ("　全解" if solutions else ""),
        "PAPERS": papers_tex,
        "SOLUTIONS": "\\solutionsmodetrue" if solutions else "",
    }.items():
        main = main.replace(f"<<{key}>>", str(val))
    if "<<" in main:
        die(f"模板里有未替换的占位符：{[l for l in main.splitlines() if '<<' in l]}")
    (work / "main.tex").write_text(main, encoding="utf-8")

    print(f"编译 {title}（{len(items)} 套 / {sum(counts)} 题{'，含解析' if solutions else ''}）")
    proc = subprocess.run(["tectonic", "-X", "compile", "main.tex", "--outdir", "."],
                          cwd=work, capture_output=True, text=True)
    log = proc.stdout + proc.stderr
    if proc.returncode != 0:
        print(log[-3000:])
        die(f"{title} 编译失败")
    for line in sorted({l.strip() for l in log.splitlines() if "Overfull" in l or "Underfull" in l}):
        print(f"  ! {line}")

    OUT.mkdir(exist_ok=True)
    target = OUT / f"{title}.pdf"
    shutil.copy(work / "main.pdf", target)
    print(f"  → {target.relative_to(ROOT)}")

    # 单套卷 PDF：让 README 表格每一行都有可点的下载
    singles = [build_one(work, it, cfg.get("学校", "浙江大学"), course, solutions) for it in items]
    print(f"  → 单套 {len(singles)} 份：{'、'.join(p.stem for p in singles[:3])} …")

    if keep:
        print(f"  中间目录：{work}")
    else:
        shutil.rmtree(work, ignore_errors=True)


def check() -> int:
    """逐卷核对 solutions/ 与 papers/ 的题数、块数与括号配平，供撰写解析时快速自检。"""
    ok = True
    for tex in sorted(PAPERS.glob("*.tex")):
        src = SOLUTIONS / tex.name
        n_problem = len(PROBLEM_RE.findall(tex.read_text(encoding="utf-8")))
        if not src.exists():
            print(f"✗ {tex.name}：缺 solutions/{tex.name}")
            ok = False
            continue
        text = src.read_text(encoding="utf-8")
        n_solution = len(SOLUTION_RE.findall(text))
        opens, closes = text.count(r"\begin{solution}"), text.count(r"\end{solution}")
        note = ""
        if opens != closes:
            note += f" \\begin/\\end 不配对（{opens}/{closes}）"
        if "$" in text and text.count("$") % 2:
            note += " 行内公式 $ 个数为奇数"
        flag = "✓" if n_solution == n_problem and not note else "✗"
        if flag == "✗":
            ok = False
        print(f"{flag} {tex.name}：题目 {n_problem} 道，解析 {n_solution} 条{note}")
    print("全部一致" if ok else "存在问题，见上")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="编译试题合集")
    ap.add_argument("book", nargs="?", help="合集定义 yaml（缺省时用根目录唯一的 book*.yaml）")
    ap.add_argument("--all", action="store_true", help="编译根目录所有 book*.yaml")
    ap.add_argument("--keep", action="store_true", help="保留中间目录")
    ap.add_argument("--check", action="store_true", help="只校验题目与解析是否一一对应，不编译")
    args = ap.parse_args()

    if args.check:
        return check()

    if args.all:
        books = sorted(ROOT.glob("book*.yaml"))
    elif args.book:
        books = [ROOT / args.book]
    else:
        books = sorted(ROOT.glob("book*.yaml"))
        if len(books) != 1:
            die("根目录有多个 book*.yaml，请指定其中之一或用 --all")
    if not books:
        die("没有找到 book*.yaml")
    for b in books:
        if not b.exists():
            die(f"找不到 {b}")
        build(b, args.keep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
