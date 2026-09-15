# AGENTS.md —— 工程约定

面向在本仓库里干活的人与 AI 助手。收录了什么看 [README.md](README.md)，这里只讲怎么改。
三条底线：`sources/` 只进不改；一纸一份 tex，可读可 diff 可单独编译；改完必须重新出书并逐页看过。

## 1. 目录

```
sources/            原始 PDF，只进不改：<学年>-<学期>-<考试>-<课程>[-后缀].pdf
papers/             一纸一份转录源：<学年>-<学期>-<考试>-<课程>.tex
solutions/          一纸一份解析体，与 papers/ 同名对应：<学年>-<学期>-<考试>-<课程>.tex
book-<课程>-<考试>-<学期>.yaml   合集定义（书名以“题目卷”结尾）
book-<课程>-<考试>-<学期>-解析.yaml  解析版合集定义（同上，多一行 `解答: true`）
out/                成品：<书名>.pdf 合订本 + 每套卷一份 <学年>-<学期>-<考试>-<课程>[-解析].pdf
tools/build.py      出书；tools/render.py 渲染扫描页
tools/preamble.tex  共享版式（题目环境、留白、解析环境、卷头、页眉页脚）
tools/book-template.tex  main.tex 模板（<<占位符>>）
tools/requirements.txt   PyMuPDF、PyYAML
```

没有中间产物目录：渲染的页图写到系统临时目录，构建目录编译完即删（`build.py --keep` 可保留）。

## 2. 命名与元数据

文件名即元数据，`<学年>-<学期>-<考试>-<课程>.tex`：学年写全（`2024-2025`），学期 `秋冬|春夏`，
考试 `期中|期末`，课程 `甲|乙`（课程 = 《线性代数（甲）》取“甲”，《线性代数（乙）》取“乙”）。
`build.py` 用 `^(\d{4}-\d{4})-(秋冬|春夏)-(.+)-([甲乙丙丁])\.tex$` 解析，不符合的文件跳过并告警；
**加新考试类型或课程代号要同步改正则和 README**。来源 PDF 同规则命名。

每份 tex 第一行必须是来源注释：

```latex
% 来源：sources/2016-2025-期中-甲-历年真题汇编.pdf 第 3 页
```

一份汇编含多套卷时（如汇编一页一套），拆成多份 tex，各自用 `第 N 页` 指向同一底本。

`solutions/` 里的文件与 `papers/` **逐字同名**，一一对应，缺一份 `build.py` 就报错拒绝出书。
解析体**只写解析**，不抄题干、不写题号——题干以 `papers/` 为唯一来源，构建时才按题序拼到一起。

## 3. LaTeX 规范

试卷文件**只写题目**：卷头（校名／课程名／学年学期考试）、页眉、页码、题号计数器都由 `preamble.tex` 和 `build.py` 负责，
tex 里不写 `\documentclass`、`\paperhead`、`\section`。

```latex
% 来源：sources/2016-2025-期中-历年真题汇编.pdf 第 1 页

\blockhead{填空题（85 分）}      % 卷内分块标题，不分块就不写

\begin{problem}{15 分}{9cm}      % {分值}{题后留白高度}
设 $A=\begin{pmatrix}1&2\\3&4\end{pmatrix}$，求 $A^{-1}$。
\end{problem}
```

| 写法 | 效果 |
| --- | --- |
| `\begin{problem}{15 分}{9cm}` | 显示 `3.（15 分）`，题后留白 9 cm |
| `\begin{problem}{}{4cm}` | 只显示 `3.`（原卷未标每题分值时用） |
| `\blockhead{填空题（85 分）}` | 卷内分块标题，不参与题号 |
| `\blank` / `\blank[5cm]` | 填空横线，默认 2.4 cm |

- 题号在每个 `\paperhead` 后自动从 1 重新计数。
- 留白按分值：≥20 分 11 cm、15 分约 9 cm、10 分约 7 cm、填空约 4 cm；同一份卷内保持一致。
- 留白参数兼作 `\needspace`，保证“题干＋留白”不被分页切断；题干长而留白小会把整块挤到下一页，留半页空白。
- 公式：`amsmath`，矩阵 `pmatrix/bmatrix`、行列式 `vmatrix`，行内 `$...$`、独立 `\[...\]`，不用 `$$`；小问用
  `enumerate[label=(\arabic*)]` 放在同一 `problem` 环境内共享留白。
- 出现 `Overfull \hbox` 必须处理：常见做法是 `\setlength{\arraycolsep}{4.5pt}` 收窄矩阵列距，或把过长的表达式单独提行。
- **忠实转录，不订正原卷笔误**（例如 2020–2021 第一题行列式末行的 `3`、2016–2017 第二题误写“齐次”）：订正后
  反而与流传的其他版本对不上。仅当缺字导致题目无法理解时做最小补全，并注释写明原文。
  但**转录误读要改**：若底本写的是 $A^{*}$（伴随）而被抄成 $A'$，那是抄错而不是原卷笔误，必须按底本订正。
- 年份在 LaTeX 里写 `2024--2025`（en dash）；`build.py` 会把文件名里的连字符自动转成 `--`，手写 tex 时自己注意。

### 3.1 解析体（solutions/）

每题一个 `solution` 环境，块数与题数必须相等，顺序即题序。写法细则见 [solutions/README.md](solutions/README.md)，
一份完整示范见 `solutions/2019-2020-秋冬-期中-甲.tex`。

```latex
\begin{solution}
由 $|A|=-2$ 得 $A^{*}=-2A^{-1}$，原方程化为 $(A^{-1}+E)BA=6E$，……
\ans{$B=\begin{pmatrix}2&0&0\\0&-12&6\\0&-6&6\end{pmatrix}$。}
\rem{伴随矩阵与转置容易混淆……}
\end{solution}
```

| 写法 | 效果 |
| --- | --- |
| `\begin{solution} … \end{solution}` | 渲染成粗体「解」起头，块内不要再写“解”字 |
| `\ans{…}` | 粗体「答案」行；凡要求具体结果的都在末尾给，纯证明题不用 |
| `\rem{…}` | 粗体「注」行，点明关键思想或常见错处；**每卷不超过 3 处** |
| `\qed` | 证明收尾的方框（`amsthm` 提供），证明题用它结尾 |

- 解析模式（`\ifsolutionsmode`）下题目不留作答空白、卷头改称“试题解析”、行距由 1.28 收到 1.22
  （解析卷没有作答留白，可以更密；实测比沿用 1.28 少两页，且各卷末页不再只余一两行）。
- 解析里引用的定理要指名，分情形要分全（参数退化、分母为零、$n$ 的奇偶、矩阵不可逆、秩退化）；
  题干问“无解／唯一解／无穷多解”的要逐项回答，不能只答其中一支。

## 4. 合集定义 book-<课程>-<考试>-<学期>.yaml

```yaml
课程名: 《线性代数（甲）》        # 封面、卷头
学校: 浙江大学
书名: 线性代数甲-期中-秋冬-题目卷  # 决定 out/<书名>.pdf
页眉: 《线性代数（甲）》历年秋冬学期期中试题合集
大标题: 历年秋冬学期期中试题合集   # 封面
副标题: 题　目　卷
筛选:                            # 按文件名挑选，三项都可省
  课程: 甲
  考试: 期中
  学期: 秋冬
```

卷序固定为学年由近及远；完成品不含使用说明页，只有封面、目录、正文。封面与卷头突出校名（浙江大学），
页眉左侧也是校名开头，改法集中在 `tools/preamble.tex` 的 `\paperhead` 与 `tools/book-template.tex` 的封面。封面上的“共 N 套 · M 题”由构建脚本按实际统计写入；
封面底部的整理者与联系方式（email、GitHub 仓库）写死在 `tools/book-template.tex`。
每次构建除合订本外，还会为每套卷单独输出一份 PDF（`out/<学年>-<学期>-<考试>-<课程>.pdf`，无封面目录，页眉左侧为课程名），
供 README 表格逐行链接。新增合集＝在根目录加一个 `book-*.yaml` 改 `书名` 与 `筛选`。

**解析版**＝同一批卷、多写一行 `解答: true`（另存为 `book-*-解析.yaml`，`书名` 与 `副标题` 相应用“解析卷”“解　析　卷”）。
打开后 `build.py` 去 `solutions/` 取同名解析，按题序插到每题 `\end{problem}` 之后；题数与解析条数不等、或缺同名文件，
直接报错拒绝出书。解析版的单套成品在文件名末尾加 `-解析`（`out/<学年>-<学期>-<考试>-<课程>-解析.pdf`），
目录条目与页眉也随之加“解析”二字，与题目卷不会互相覆盖。

## 5. 工具

```bash
# 转录时看底本（整页 → 系统临时目录，路径会打印出来）
python3 tools/render.py sources/2016-2025-期中-历年真题汇编.pdf 3,5,8-10
# 公式细节局部放大（--box 为 PDF 点坐标 x0,y0,x1,y1，左上为原点；A4=595×842，汇编=793×1122）
python3 tools/render.py sources/2016-2025-期中-历年真题汇编.pdf 11 --box 40,140,600,240 --zoom 5

# 出书
python3 tools/build.py              # 根目录唯一的 book*.yaml
python3 tools/build.py book-甲-期中-秋冬.yaml
python3 tools/build.py --all        # 根目录所有 book*.yaml（题目卷与解析卷一起出）
python3 tools/build.py --keep       # 保留中间目录，便于查生成的 main.tex

# 只校验题目与解析是否一一对应，不编译（写解析时用这个快速自查）
python3 tools/build.py --check
```

`build.py` 流程：读 yaml → 解析文件名 → 筛选、学年倒序 → 临时目录内生成 main.tex（拷入 preamble 与用到的试卷；
解析版则先把 `solutions/` 的同名解析按题序交织进正文）→ `tectonic -X compile` → 成品到 `out/<书名>.pdf`，
并打印 Overfull/Underfull 警告。

`--check` 逐卷核对 `solutions/` 与 `papers/`：题数与解析块数是否相等、`\begin/\end{solution}` 是否配对、
行内 `$` 是否为偶数个，有问题的那一行前面打 ✗ 并以非零码退出。**加了解析就先用它自查，再出书。**

## 6. 下载链接

README 只放 GitHub raw 链接，不解释 CDN（jsDelivr 与 raw 路径相同，把
`raw.githubusercontent.com/macanine/zju-linear-algebra-papers/main` 换成
`cdn.jsdelivr.net/gh/macanine/zju-linear-algebra-papers@main` 即得，写在这里备查，不要写进 README）。
文件名含中文，必须用 `quote(path, safe='/')` 做百分号编码，不要直接写中文进 URL：

```
https://raw.githubusercontent.com/macanine/zju-linear-algebra-papers/main/out/<文件名>.pdf

文件名形如 `<书名>.pdf`（合订本：`…-题目卷` / `…-解析卷`）或
`<学年>-<学期>-<考试>-<课程>[-解析].pdf`（单套，`-解析` 为解析版）。
```

新增/删除成品 PDF 后，README 必须同步：合订本链接并进标题、单套表一行两列（题目卷 / 解析卷），
表内题数由 `papers/*.tex` 统计。写完自查一遍表里每个链接是否都对应 `out/` 里实际存在的文件。

## 7. 质量流程

新增或改动试卷后：渲染底本 → 逐题转录（公式靠 `--zoom 5` 放大确认，别猜）→ 出书并清掉所有 Overfull 警告 →
**逐页视觉验收**（成品渲染成 PNG 交视觉验收环节判定：内容与底本一致、无裁切重叠、中文字形完整、版式统一、留白充足、无答案泄漏）→
**与上一版逐页像素回归比对**（同倍率渲染逐页比较 `pixmap.samples`，差异必须能解释）→ 同步 README 收录表。

写解析额外三步：**逐题独立重算**（sympy 或纯 Python 精确算术，把 `\ans` 的结论重新算一遍，不要只读一遍觉得有道理）→
**换人复核**（复核者独立重算并逐条检查论证完备性：分情形是否漏项、引用的定理是否指名、有没有“显然”掩盖的跳步）→
解析卷同样逐页视觉验收（重点看题目与解答有没有被拆得七零八落、填空题的每个空是否都给了答案）。

验收范围按改动定：只改封面/目录 → 正文应与上一版逐页一致，只验收封面与目录；改 `tools/preamble.tex` → 整本重验收；
新增一套卷 → 验收新增页与受分页影响的相邻页，并核对目录页码（用 pymupdf 抽取每套卷标题所在页比对）；
改 `solutions/` → 重出解析卷，验收该卷全部页面。

题面改动要连带处理解析：改了 `papers/` 的题面或记号，必须回头核对 `solutions/` 里同名的那一份是否还对得上。

## 8. 环境

```bash
python3 -m venv .venv && .venv/bin/pip install -r tools/requirements.txt   # PyMuPDF、PyYAML
brew install tectonic                                                      # 或 TeX Live 的 xelatex/latexmk
```

引擎为 XeLaTeX（`ctexart`），字体走 ctex 的 `mac` fontset（Songti SC / STHeiti / Kaiti），换平台需改 fontset。
tectonic 首次编译需联网取 TeX bundle，之后可离线。`.venv/` 已 gitignore，`out/` 成品入库。

## 9. 已知坑

| 坑 | 说明 |
| --- | --- |
| 年份破折号 | LaTeX 里必须 `2024--2025`，单连字符会与既有版本排版不一致 |
| 环境第二参数 | `\newenvironment` 结束代码里不能用 `#2`，`problem` 用 `\problemspace` 中转 |
| 分页切断 | 靠 `\needspace` 保块；题干长留白小时整块后移，留半页空白 |
| 行尾孤字 | 句末“为 1。”可能把 `1。` 挤到下一行，用 `\mbox{~$1$}` |
| Overfull | 构建日志里的 Overfull/Underfull 清零再提交 |
| 大文件 | `sources/` 有 10 MB 级扫描件，上远端且继续膨胀时考虑 Git LFS |
| 伴随 vs 转置 | 汇编里伴随矩阵的上标印得很小，`A^{*}` 极易误抄成 `A'`。**遇到 `A'` 先放大底本核对**：2016–2017 第五题就是这种误读，按转置解方程无解，按伴随解才有唯一答案 |
| 汇编的原卷笔误 | 底本本身有多处笔误，解析里用 `\rem` 说明即可，**不要改 `papers/` 题面**：2020–2021 第一题末行的 `3`、第四题第三式的 `bx_2`、第六题“二阶零方阵”，2022–2023 第七题把 `D` 的阶数写重、第八题“$\forall n,\forall n$”（按字面 $m<n$ 时不成立） |
| 解析版行距 | 解析模式在 `\AtBeginDocument` 里改 `\linespread{1.22}`（`\solutionsmodetrue` 在 `\input{preamble}` 之后才置位，写在导言区直接判断会读到 false） |
| 解析版末页 | 每套卷各自 `\clearpage` 起页，末页不满是正常分页；但要避免“整页只剩一两行”。检测办法：pymupdf 取每页正文块的 `b[3]` 除以页高，**记得排除页眉页脚**（否则页脚总是把比例顶到 0.96，量了个寂寞） |

## 10. 提交前检查

- [ ] 文件名符合约定，首行来源注释与 `sources/` 底本页码一致
- [ ] `python3 tools/build.py --check` 全绿（题目与解析一一对应）
- [ ] `python3 tools/build.py --all` 通过，无 Overfull/Underfull
- [ ] 逐页视觉验收通过（含封面、目录页码、正文留白；解析卷另看题解是否配套、填空是否答全）
- [ ] 与上一版做过像素回归，差异可解释
- [ ] 解析的结论逐题独立重算过，且换人复核过论证完备性
- [ ] README 下载表与下载链接已同步（新增/改动卷、题数、文件名时，题目卷与解析卷两列都要）
