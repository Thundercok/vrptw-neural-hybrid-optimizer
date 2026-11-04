#!/bin/sh
# Build the highlighted PDF for the resubmission: docs/manuscript_submitted.tex against docs/manuscript.tex.
# Additions are blue, deletions small and red. Tables and figures are not marked inside, so say in the
# response letter that they were replaced. CFONT is used because local TinyTeX has no ulem.
# usage: scripts/build_highlighted_pdf.sh OUTPUT_DIR
set -eu
root=$(cd "$(dirname "$0")/.." && pwd)
out=${1:?output directory}
mkdir -p "$out"
cd "$out"
latexdiff --type=CFONT --graphics-markup=none --encoding=utf8 --math-markup=off \
  --exclude-textcmd="section,subsection,subsubsection,caption,author,title" \
  --config="PICTUREENV=(?:picture|tikzpicture|DIFnomarkup|algorithm|tabular|table)[\w\d*@]*" \
  "$root/docs/manuscript_submitted.tex" "$root/docs/manuscript.tex" > highlighted.tex 2> latexdiff.err
# The current directory comes first, or LaTeX reads the stale docs/*.aux instead of its own.
for pass in 1 2 3; do
  TEXINPUTS=".:$root/docs::" TFMFONTS=".:$root/docs::" T1FONTS=".:$root/docs::" \
    pdflatex -interaction=nonstopmode highlighted.tex > /dev/null 2>&1 || true
done
grep -a 'Output written' highlighted.log
grep -a -E '^!|undefined references' highlighted.log || true
