"""Build manuscript_highlight.tex, the source of the "Highlighted PDF" for the resubmission.

usage (from docs/):  python3 make_highlighted.py

New and changed text is highlighted in yellow, changed equations are shown in blue, and text that
was removed is not shown. Compile the result with the same class and fonts as manuscript.tex (three
pdflatex passes). It needs ulem, which Overleaf and a full TeX Live have.

Steps:
1. latexdiff of manuscript_submitted.tex against manuscript.tex, without deleted text, leaving
   section titles, TikZ figures and the algorithm unmarked.
2. Redefine the added-text macros: a yellow ulem highlighter in text, blue in math.
3. Move bold outside the highlight (the class defines \\bf with an argument, so
   \\textbf{\\DIFadd{..}} does not compile).
4. Take long inline formulas out of the highlight, because ulem boxes them and they can no longer
   break across lines.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD, NEW, OUT = "manuscript_submitted.tex", "manuscript.tex", "manuscript_highlight.tex"
HIGHLIGHT = r"\bgroup\markoverwith{\textcolor{yellow}{\rule[-.6ex]{2pt}{2.6ex}}}\ULon{#1}"
SWITCH = r"\ifmmode\expandafter\DIFaddmath\else\expandafter\DIFaddhl\fi{#1}"
LONG_FORMULA = 45  # characters of source


def split_long_math(body: str) -> tuple[str, int]:
    out, i, count = [], 0, 0
    pattern = re.compile(r"\\DIFadd(FL)?\{")
    while True:
        m = pattern.search(body, i)
        if not m:
            out.append(body[i:])
            return "".join(out), count
        out.append(body[i : m.start()])
        j, depth = m.end(), 1
        while depth and j < len(body):
            if body[j] == "\\":
                j += 2
                continue
            depth += {"{": 1, "}": -1}.get(body[j], 0)
            j += 1
        arg, name = body[m.end() : j - 1], "\\DIFadd" + (m.group(1) or "")
        parts, k, depth, start = [], 0, 0, 0
        while k < len(arg):
            c = arg[k]
            if c == "\\":
                k += 2
                continue
            if c in "{}":
                depth += 1 if c == "{" else -1
            elif c == "$" and depth == 0:
                e = k + 1
                while e < len(arg) and arg[e] != "$":
                    e += 2 if arg[e] == "\\" else 1
                if e < len(arg) and e - k > LONG_FORMULA:
                    parts += [("text", arg[start:k]), ("math", arg[k : e + 1])]
                    start = e + 1
                k = e
            k += 1
        if parts:
            parts.append(("text", arg[start:]))
            count += 1
            out.append("".join(
                (f"{name}{{{t}}}" if t.strip() else t) if kind == "text" else f"{{\\color{{blue}}{t}}}"
                for kind, t in parts
            ))
        else:
            out.append(f"{name}{{{arg}}}")
        i = j


def main() -> int:
    raw = subprocess.run(
        ["latexdiff", "--no-del", "--type=UNDERLINE", "--math-markup=whole", "--graphics-markup=none",
         "--exclude-textcmd=section,subsection,subsubsection",
         r"--config=PICTUREENV=(?:picture|DIFnomarkup|tikzpicture|axis|algorithmic)[\w\d*@]*", OLD, NEW],
        cwd=HERE, capture_output=True, text=True, check=True,
    ).stdout
    anchor = r"\RequirePackage{color}\definecolor{RED}{rgb}{1,0,0}\definecolor{BLUE}{rgb}{0,0,1} %DIF PREAMBLE" + "\n"
    assert raw.count(anchor) == 1, "latexdiff preamble changed; check the macro definitions"
    raw = raw.replace(anchor, anchor
                      + r"\newcommand{\DIFaddhl}[1]{" + HIGHLIGHT + "} %DIF PREAMBLE\n"
                      + r"\newcommand{\DIFaddmath}[1]{{\color{blue}#1}} %DIF PREAMBLE" + "\n")
    for name in ("DIFadd", "DIFaddFL"):
        raw, n = re.subn(r"\\providecommand\{\\" + name + r"\}\[1\]\{.*?\} %DIF PREAMBLE",
                         lambda _m, name=name: r"\DeclareRobustCommand{" + "\\" + name + "}[1]{" + SWITCH + "} %DIF PREAMBLE",
                         raw, count=1)
        assert n == 1, f"definition of {name} not found"
    raw, bold = re.subn(r"\\textbf\{\\DIFadd(FL)?\{([^{}]*)\}\}",
                        lambda m: "\\DIFadd" + (m.group(1) or "") + "{\\textbf{" + m.group(2) + "}}", raw)
    assert not re.search(r"\\textbf\{\s*\\DIFadd", raw), "a bold wrapper still encloses a highlight"
    cut = raw.index("\\begin{document}")
    body, formulas = split_long_math(raw[cut:])
    (HERE / OUT).write_text(raw[:cut] + body, encoding="utf-8")
    print(f"{OUT}: {len(re.findall(r'DIFaddbegin', body))} added blocks, "
          f"{bold} bold wrappers moved, {formulas} highlights split around long formulas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
