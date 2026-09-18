# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A set of dense, two-column LaTeX lecture notes on computer vision. There is no
application code — the deliverable is a set of PDFs. Planned future material:
video and neural networks, which will be added as new parts.

## Build

```bash
scripts/build.sh                 # rebuild every part that is out of date
scripts/build.sh part3 part5     # rebuild only matching parts (substring match)
scripts/build.sh -f              # force full rebuild
scripts/build.sh -c              # clean aux files, keep PDFs   (-C also deletes PDFs)
scripts/build.sh -v              # stream latexmk output instead of summarising
```

Or directly: `latexmk part3-features.tex`. **Always build from the repository
root** — `\includegraphics` paths are relative to the working directory, not to
the `.tex` file.

`.latexmkrc` sets `$aux_dir = 'build'` and `$out_dir = '.'`, so aux files land in
`build/` and the PDFs sit next to their sources. Read errors from
`build/<part>.log`.

Typical times: part1 0.9s, part2 1.7s, part3 2.3s, part4 1.2s, part5 0.9s.

## Architecture

**Five independent documents, one shared package.** Each `partN-*.tex` is a
standalone document producing its own PDF. They share everything through
`settings.sty` (`\usepackage{settings}`, resolved because `TEXINPUTS` starts with
`.`). There is deliberately no master document that includes all parts.

Each part is a thin shell around its content:

```latex
\documentclass[letterpaper]{article}
\usepackage{settings}
\begin{document}
\begin{notes}{Part 3: Features}
...chapters inline...
\end{notes}
\end{document}
```

The `notes` environment (defined in `settings.sty`) supplies the title block,
`multicols*{2}`, `footnotesize`, and the table of contents.

**Chapters live inline.** Chapters are *not* separate files — all of a part's
chapters sit directly in its `.tex`. This is a deliberate choice; do not split
them out without being asked.

### Sectioning is custom, and auto-numbered

`\NoteChapter`, `\NoteSection`, `\NoteSubsection` replace the standard
sectioning commands. They drive three counters (`notechapter`, `notesection`,
`notesubsection`, each resetting the next) and emit both the TOC entry and the
PDF bookmark.

Consequences worth internalising:

- **Numbers come from document order.** Never write a chapter or section number
  literally — moving content renumbers it automatically.
- **Numbering restarts at 1 in every part**, because each part is its own
  document. Part 3's first chapter is "Chapter 1".
- **Cross-part references are impossible.** `\label`/`\ref` work only within a
  single part. Keep any labelled equation and its references in the same part.

### The `[plots]` option

`settings.sty` loads `pgfplots` only when passed the `plots` option, because it
costs ~0.25s on every compile. Part 2 uses `\usepackage[plots]{settings}`; the
rest do not. If you add a `tikzpicture`/`axis` to a part, add the option to that
part's `\usepackage` line. Use the shared `notesplot` style for plots so they
match:

```latex
\begin{axis}[notesplot, xlabel={...}, ylabel={...}]
```

### Images

Images live in `images/partN/` matching the part that uses them, and are
referenced as `images/partN/foo.png`. No image is shared between parts; if two
parts need the same figure, copy it rather than reaching across.

**Size images for the column.** The text column is ~3.98in wide, so a full-width
figure needs ~1200px for 300dpi. Oversized images are the single largest
contributor to compile time — image embedding once accounted for ~65% of the
build. Check effective DPI (`pixel_width / (width_fraction × 3.98)`) before
adding a figure.

`scripts/gen-noise-figures.py` (numpy + Pillow, fixed seed) regenerates the
Part 2 noise figures. Prefer generating figures over sourcing them externally —
it keeps licensing clean and sizes them correctly.

## Pagination is hand-tuned

`\columnbreaknofill` (`\vfill\null\columnbreak`) and `\newpage` are placed
manually throughout, mostly just before each `\NoteChapter`, to control where
columns and pages break. These were tuned against specific content, so **adding
or removing more than a few lines will push them out of place**. After a
substantive edit, rebuild and check the affected pages, and expect to move a
break or two. This is cosmetic, but it is the usual source of ugly output.

## House style

Match the surrounding prose — it is terse, notes-style, and dense:

- `\textbf{Term.}` lead-ins to start a paragraph-sized idea.
- `$$...$$` for display math; `\R`, `\Z`, `\Q`, `\C` are defined for blackboard bold.
- British `-ise`/`-isation` spellings (quantisation, normalised, modelled).
- A spaced hyphen ` - ` is used as the dash, not `---`.
- LaTeX quotes (two backticks to open, two apostrophes to close), never a
  straight `"` — which TeX renders as a closing quote at both ends.

## Adding a new part

1. Copy an existing part's four-line shell, change the `notes` title.
2. Create `images/part6/`.
3. Nothing else — no registration step, no master file to update. `scripts/build.sh`
   discovers `part*.tex` by glob.
