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
PAPERS, TOOLS, OUT = ROOT / "papers", ROOT / "tools", ROOT / "out"
NAME_RE = re.compile(r"^(\d{4}-\d{4})-(秋冬|春夏)-(.+)-([甲乙丙丁])\.tex$")


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


PAPER_TEMPLATE = r"""\documentclass[UTF8,a4paper,11pt]{ctexart}
\input{preamble.tex}
\renewcommand{\schoolname}{%(school)s}
\renewcommand{\coursename}{%(course)s}
\renewcommand{\booktitle}{%(course)s}
\begin{document}
\paperhead{%(year)s}{%(term)s学期}{%(exam)s}{%(label)s}
\input{papers/%(file)s}
\end{document}
"""


def build_one(work: Path, it: dict, school: str, course_title: str) -> Path:
    """把单套试卷编成一份 PDF（无封面目录，页眉左侧为校名+课程名）。"""
    year = it["year"].replace("-", "--")
    course_title = course_title.replace("甲", it["course"]) if it["course"] != "甲" else course_title
    label = f"{year} 学年{it['term']}学期（{it['course']}）{it['exam']}"
    shutil.copy(it["tex"], work / "papers" / it["tex"].name)
    (work / "main.tex").write_text(PAPER_TEMPLATE % {
        "school": school, "course": course_title, "year": year,
        "term": it["term"], "exam": it["exam"], "label": label, "file": it["tex"].name,
    }, encoding="utf-8")
    proc = subprocess.run(["tectonic", "-X", "compile", "main.tex", "--outdir", "."],
                          cwd=work, capture_output=True, text=True)
    if proc.returncode != 0:
        print((proc.stdout + proc.stderr)[-2000:])
        die(f"{it['tex'].name} 单卷编译失败")
    target = OUT / it["tex"].with_suffix(".pdf").name
    shutil.copy(work / "main.pdf", target)
    (work / "papers" / it["tex"].name).unlink()
    return target


def build(book: Path, keep: bool) -> None:
    cfg = yaml.safe_load(book.read_text(encoding="utf-8")) or {}
    items = collect(cfg.get("筛选") or {})
    if not items:
        die(f"{book.name} 没有匹配到任何试卷")

    title = cfg.get("书名") or book.stem
    courses = sorted({it["course"] for it in items})
    course = cfg.get("课程名", "《线性代数（" + courses[0] + "）》")

    counts = [len(re.findall(r"\\begin\{problem\}", it["tex"].read_text(encoding="utf-8"))) for it in items]

    work = Path(tempfile.mkdtemp(prefix="laps-build-"))
    (work / "papers").mkdir()
    shutil.copy(TOOLS / "preamble.tex", work / "preamble.tex")
    for it in items:
        shutil.copy(it["tex"], work / "papers" / it["tex"].name)

    papers_tex = "\n\n".join(
        f"\\paperhead{{{it['year'].replace('-', '--')}}}{{{it['term']}学期}}{{{it['exam']}}}"
        f"{{{it['year'].replace('-', '--')} 学年{it['term']}学期（{it['course']}）{it['exam']}}}\n"
        f"\\input{{papers/{it['tex'].name}}}"
        for it in items
    )
    main = (TOOLS / "book-template.tex").read_text(encoding="utf-8")
    for key, val in {
        "SCHOOL": cfg.get("学校", "浙江大学"),
        "COURSE_TITLE": course,
        "HEADER": cfg.get("页眉", title),
        "BOOK_TITLE": cfg.get("大标题", "历年试题合集"),
        "SUBTITLE": cfg.get("副标题", "题目卷"),
        "COUNT_LINE": f"共 {len(items)} 套 · {sum(counts)} 题",
        "PAPERS": papers_tex,
    }.items():
        main = main.replace(f"<<{key}>>", str(val))
    if "<<" in main:
        die(f"模板里有未替换的占位符：{[l for l in main.splitlines() if '<<' in l]}")
    (work / "main.tex").write_text(main, encoding="utf-8")

    print(f"编译 {title}（{len(items)} 套 / {sum(counts)} 题）")
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
    singles = [build_one(work, it, cfg.get("学校", "浙江大学"), course) for it in items]
    print(f"  → 单套 {len(singles)} 份：{'、'.join(p.stem for p in singles[:3])} …")

    if keep:
        print(f"  中间目录：{work}")
    else:
        shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="编译试题合集")
    ap.add_argument("book", nargs="?", help="合集定义 yaml（缺省时用根目录唯一的 book*.yaml）")
    ap.add_argument("--all", action="store_true", help="编译根目录所有 book*.yaml")
    ap.add_argument("--keep", action="store_true", help="保留中间目录")
    args = ap.parse_args()

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
