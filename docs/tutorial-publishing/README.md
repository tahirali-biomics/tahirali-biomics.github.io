# Publishing one Quarto tutorial safely

This workflow renders one tutorial in a temporary website project, keeps the website's existing `_quarto.yml` navigation and `styles.css`, and links reusable code-block CSS and copy controls only on that rendered page. It never changes the original QMD. Quarto's project setting `execute.enabled: false` and each tutorial's `execute: eval: false` are retained, so analyses are not rerun.

## Prepare a QBio305 tutorial

Keep the tutorial source and its supplied materials together under `teaching/tutorials/qbio305/<tutorial>/`. Put pre-existing figures, result tables and session information in a clear subdirectory such as `Results/Day4/`. Keep source analysis commands in the QMD as supplied. For tutorials with existing figures that are absent from the QMD's prose, create a JSON figure map with exact unique text anchors, relative image paths and captions; the builder inserts ordinary Markdown image references into its temporary QMD copy only.

Example `figures.json`:

```json
[
  {
    "after": "The exact unchanged sentence immediately before the figure.",
    "image": "Results/Day4/01_genome_PCA_PC1_PC2.png",
    "caption": "Genome-wide PCA of the accessions."
  }
]
```

The anchor must occur exactly once, and the image must be inside the tutorial directory. The helper stops if either condition fails rather than guessing a figure position.

## Render one page

From the repository root (or an isolated source worktree):

```bash
python3 scripts/tutorials/build_tutorial.py \
  teaching/tutorials/qbio305/qbio305_project_part1/QBio305_Practical_Day_4_Final.qmd \
  --legacy-html teaching/tutorials/qbio305/qbio305_project_part1/QBio305_Practical_Day_4_Final.html \
  --base-css /path/to/current/gh-pages-worktree/styles.css \
  --output-dir /tmp/qbio305-day4-preview
```

`--legacy-html` retains an existing RStudio/Pandoc rendered body, including its embedded figures and printed R results, inside the newly rendered Quarto website shell. This is useful when the QMD has `eval: false` and the existing output is authoritative. For source-provided images not present in that legacy output, use `--figure-map figures.json`. Without either option, the page is rendered from the QMD as written. The output directory must be absent or empty. Build artifacts are confined to that output directory and Quarto's temporary workspace.

When preparing a targeted page deployment, pass `--base-css` with the stylesheet from the current `gh-pages` worktree. The builder uses the current source branch's Quarto navigation and page metadata while retaining the stylesheet already served by the published site; it will not silently replace that shared CSS.

## Validate generated HTML

```bash
python3 scripts/tutorials/validate_tutorial.py \
  /tmp/qbio305-day4-preview/teaching/tutorials/qbio305/qbio305_project_part1/QBio305_Practical_Day_4_Final.html \
  --expected-images 11 \
  --source-root . \
  --site-root /path/to/current/gh-pages-worktree \
  --site-page teaching/tutorials/qbio305/qbio305_project_part1/QBio305_Practical_Day_4_Final.html
```

The validator checks the Quarto sidebar and content shell, page-scoped CSS and copy-control script, code blocks, expected image count, local image files and relative HTML links. Quarto's own buttons are left intact; the fallback adds a button to a legacy code block only when neither Quarto nor an existing legacy wrapper already supplies one. It reports whether Quarto generated a right-side TOC. Also review the HTML diff/text against the original rendered output and inspect the page at desktop and mobile widths before publishing.

Unit checks:

```bash
python3 -m unittest discover -s tests/tutorials -v
```

## Publish selected pages safely

First create a new detached publishing worktree from the latest published branch; use a unique path that does not already exist:

```bash
git fetch origin gh-pages
git worktree add --detach /tmp/tutorial-publish-YYYYMMDD origin/gh-pages
```

For a small set, render each QMD to its own output directory and give the publisher one `--build-dir` per output, paired with each approved `--page`:

```bash
python3 scripts/tutorials/publish_tutorials.py \
  --build-dir /tmp/qbio305-day4-preview \
  --build-dir /tmp/day1-preview \
  --worktree /tmp/tutorial-publish-YYYYMMDD \
  --page teaching/tutorials/qbio305/qbio305_project_part1/QBio305_Practical_Day_4_Final.html \
  --page teaching/tutorials/practical_day1.html
```

The publisher requires a clean detached worktree exactly at the latest fetched `origin/gh-pages` and refuses to overwrite an existing referenced asset if its contents differ. Linked HTML pages must already exist on `gh-pages`; they are checked, never copied or staged unless explicitly selected with `--page`. It displays the staged paths and diff summary, then stops. Review `git -C /tmp/tutorial-publish-YYYYMMDD diff --cached` before committing. It never commits or pushes automatically. To publish, commit only after review, verify `git -C /tmp/tutorial-publish-YYYYMMDD remote get-url origin` uses SSH, then push with the configured SSH remote:

```bash
git -C /tmp/tutorial-publish-YYYYMMDD commit -m "Publish selected tutorial page"
git -C /tmp/tutorial-publish-YYYYMMDD push origin HEAD:gh-pages
```

On RAMSES, use the interactive terminal where your SSH agent/key is available. Do not copy a private key, passphrase or token into the repository or command history. If Codex's environment cannot use that SSH key, perform the final push from that terminal after reviewing the exact commit.

## Inspect branch divergence and worktrees

```bash
git status --short --branch
git fetch origin
git rev-list --left-right --count HEAD...origin/redesign-2026-09-03
git log --oneline --left-right HEAD...origin/redesign-2026-09-03
git worktree list --porcelain
git -C /path/to/worktree status --short --branch
```

Use a new named source worktree based on the current remote source branch for new edits. Do not reconcile a dirty checkout by resetting, checking out over it, or stashing automatically. Compare local and remote commits by patch ID and file-level diffs; merge or cherry-pick only after confirming the working-tree conflicts and making a separate recovery copy when needed. Keep source worktrees and detached publishing worktrees distinct.
