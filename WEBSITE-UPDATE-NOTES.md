# Tahir Ali portfolio — update and deployment notes

This package contains the complete Quarto source and the checked static `_site/`
preview for `https://tahirali-biomics.github.io`.

## What was updated

- The home page retains the original four-paragraph personal narrative, with
  scientific AI integrated naturally into the account of genomic research.
  Contact details, the unboxed Dostoevsky quotation, and all public-profile
  links remain; ResearchGate uses the familiar `RG` mark.
- `popgenlm.qmd` now presents PopGenLM Bench as a scientific validation
  framework rather than a generic model demonstration. It includes a verified
  100-variant result, provenance, interpretation boundaries, roadmap, and a
  working analysis notebook.
- `genomes-to-ai.qmd` now grounds the journal in the development of biological
  information, sequencing, bioinformatics, data science, large-scale data, and
  scientific AI, with a clear future-facing perspective. Five fortnightly
  reading notes interpret the supplied Chapter 2 excerpt from Christoph Adami's
  *The Evolution of Biological Information* in accessible, personal language.
- The five reading notes use deliberately simple, imperfect notebook sketches
  with thick, repeatedly traced graphite lines, explanatory side notes and
  chapter references.
- `projects.qmd` retains substantive project summaries while displaying
  whitespace-trimmed copies of all eight project figures with `object-fit:
  contain`; the graphics use more of each panel without cutting their borders.
- Teaching and workshop landing pages retain their original scope and detail,
  with clearer hierarchy, compact technical headings, and consistent links.
- The left navigation is normalised across every Quarto and preserved technical
  page. Standalone workshop exports and legacy tutorials receive an equivalent
  responsive menu and a flat, linked right-side Contents list containing only
  the main 8–12 sections where possible.
- Technical source blocks open and close independently, remain directly
  copyable, and are followed immediately by the corresponding rendered output.
- Shared CSS covers desktop, tablet, and phone layouts, including compact
  navigation, cards, tables, code blocks, plots, and one-line home-page naming.

## Final navigation

1. Home
2. PopGenLM
3. Genomes to AI
4. Projects
5. Publications
6. Résumé
7. Teaching
8. Workshops
9. GitHub

Teaching applications and course companions remain under Teaching; they are
not described as PopGenLM Bench outputs.

## PopGenLM Bench notebook

The website includes:

- `notebooks/popgenlm-bench-demo.ipynb`
- `assets/popgenlm/gpn-scores-100.tsv`
- `assets/popgenlm/run-metadata.json`
- `assets/popgenlm/summary.json`
- `assets/popgenlm/benchmark-overview.png`

The notebook loads the public score table, validates its schema and alleles,
recalculates summary statistics and bootstrap uncertainty, builds the four-panel
benchmark figure, accepts an optional compatible user table, and exports checked
outputs. A compressed embedded fixture makes the analysis runnable even before
the website's raw-data URL is available.

The Colab URL becomes public as soon as these files are pushed to the `main`
branch of `tahirali-biomics.github.io`:

`https://colab.research.google.com/github/tahirali-biomics/tahirali-biomics.github.io/blob/main/notebooks/popgenlm-bench-demo.ipynb`

This stable notebook performs validation and statistical analysis on CPU. Full
GPN inference is deliberately kept in the versioned `popgenlm-bench` software
repository because it requires a pinned model, reference sequence, input
variants, and substantially more compute. Google Colab GPU runtimes can be used
for that inference workflow after the repository is published.

## Rendering policy

The project-level `_quarto.yml` renders only pages that do not require private
data or a local scientific-computing environment. `execute.enabled: false`
prevents accidental execution during website deployment. Existing computational
tutorials and workshops are retained as static HTML resources, preserving their
code and already-rendered outputs without requiring local HPC paths, R packages,
Python environments, model weights, or a GPU.

Run a normal website build from the repository root:

```bash
quarto render
```

The finished website is written to `_site/`.

The supplied environment did not contain Quarto, so the included static preview
was refreshed with:

```bash
python scripts/build_popgenlm_figure.py
python scripts/rebuild_multivariate_figures.py
python scripts/build_static_preview.py
python scripts/qa_site.py
```

## Preserved legacy pages

The reconstructed multivariate workshop plots are based on the simulation and
analysis design embedded in its archived HTML. The five supplied
`Hands-on-Session_*_files` folders are restored alongside their HTML pages. One
Z-score screenshot referenced by Session 2 was absent from the supplied export;
it is represented transparently by a native formula-and-interpretation panel.

The tutorial landing page now links all seven original learning resources.
Practical Days 1–3 retain their full text and preserved rendered outputs;
Research Project Parts 1 and 2 are restored as self-contained HTML with their
17 and 7 embedded figures.

The biomod2 page retains its static figures, code, and interpretation. Its one
Leaflet output is represented by a clear fallback notice because the archived
page did not contain the corresponding JavaScript dependencies.

## Quality checks completed

- 43 rendered HTML pages parsed successfully.
- Exactly seven tutorial cards and six journal entries are present.
- All rendered pages include the same navigation labels and shared stylesheet.
- No missing local links, images, scripts, stylesheets, or same-page anchors
  remain in `_site/`.
- Every technical page has a flat linked Contents list of no more than 12
  entries; all links resolve to a section on that page.
- Every identified source block is collapsible and copyable, while rendered
  Practical Day 1–3 plots appear immediately after their generating code.
- The PopGenLM notebook was executed sequentially in a clean Python process;
  all validation, statistics, plotting, and export cells completed.
- Shared CSS braces are balanced and include explicit responsive breakpoints at
  1100, 992, 720, 480, and 400 pixels.
