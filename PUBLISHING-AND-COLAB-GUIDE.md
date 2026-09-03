# Test, preserve and publish the website

This package contains both the editable Quarto sources and a complete static preview in `_site/`. The static pages preserve the supplied tutorial and workshop outputs, so publishing does not require access to the original HPC paths, local R data or workshop datasets.

## 1. Keep the current website recoverable

Do this before replacing anything online.

1. On GitHub, open `tahirali-biomics/tahirali-biomics.github.io`.
2. Choose **Code → Download ZIP** and save it as `website-before-redesign-2026-09-03.zip`.
3. If you use Git locally, also preserve a named branch and tag:

   ```bash
   git clone https://github.com/tahirali-biomics/tahirali-biomics.github.io.git
   cd tahirali-biomics.github.io
   git switch -c archive/pre-redesign-2026-09-03
   git push -u origin archive/pre-redesign-2026-09-03
   git tag website-before-redesign-2026-09-03
   git push origin website-before-redesign-2026-09-03
   ```

The downloaded ZIP is the simplest emergency copy. The archive branch preserves the complete Git history and makes restoration straightforward.

## 2. Test this version locally

1. Extract the delivered website ZIP into a new folder. Do not merge it into the old site yet.
2. Open Terminal in the extracted `tahirali-biomics.github.io` folder.
3. Run the included automated check:

   ```bash
   python3 -m pip install lxml
   python3 scripts/qa_site.py
   ```

4. Start a local web server:

   ```bash
   python3 -m http.server 8000 --directory _site
   ```

5. Open `http://localhost:8000/` in Chrome, Firefox and Safari if available.
6. Test at desktop width and with the browser's responsive device toolbar at approximately 390 × 844 pixels.
7. Check Home, PopGenLM, Genomes to AI, Projects, all seven tutorial cards, at least one workshop and the Colab button.

Use the local server rather than double-clicking `_site/index.html`; browsers impose extra restrictions on pages opened with a `file://` address.

## 3. Optional online staging site

If you want a public preview before changing the main address, create a temporary repository named `website-preview`. Its Pages address will be `https://tahirali-biomics.github.io/website-preview/`.

1. Create the repository on GitHub without adding starter files.
2. In a copy of this website folder, initialise Git and connect the preview repository.
3. Install Quarto from `https://quarto.org/docs/get-started/`.
4. Run:

   ```bash
   git init
   git add .
   git commit -m "Add website redesign for review"
   git branch -M main
   git remote add origin https://github.com/tahirali-biomics/website-preview.git
   git push -u origin main
   quarto publish gh-pages
   ```

5. Open **Settings → Pages** in the preview repository and confirm that the publishing source is the `gh-pages` branch.

Delete the temporary repository only after the main site has been verified.

## 4. Publish to the main website

The safest route is a review branch followed by a Quarto `gh-pages` publication.

1. Clone the current repository and enter it:

   ```bash
   git clone https://github.com/tahirali-biomics/tahirali-biomics.github.io.git
   cd tahirali-biomics.github.io
   ```

2. Create a working branch:

   ```bash
   git switch -c redesign-2026
   ```

3. Copy the contents of this delivered folder into the cloned repository. Keep `.git/` from the clone; do not copy an outer parent folder into the repository.
4. Rebuild and test:

   ```bash
   python3 -m pip install lxml
   python3 scripts/build_static_preview.py
   python3 scripts/qa_site.py
   python3 -m http.server 8000 --directory _site
   ```

5. Commit the reviewed source:

   ```bash
   git add .
   git commit -m "Redesign portfolio and add Genomes to AI journal"
   git push -u origin redesign-2026
   ```

6. Open a pull request from `redesign-2026` to `main`. Review the changed files, then merge it.
7. From the updated `main` branch, publish:

   ```bash
   git switch main
   git pull
   quarto publish gh-pages
   ```

8. For this username site, open **Settings → Pages** and ensure the source is `gh-pages` / root after the first Quarto publication.
9. Test `https://tahirali-biomics.github.io/` in a private browser window and on a phone.

Quarto documents three supported GitHub Pages approaches—committed rendered output, `quarto publish`, and GitHub Actions—at `https://quarto.org/docs/publishing/github-pages.html`. This site uses preserved static HTML for data-dependent tutorials, so do not delete those HTML files or their matching `*_files` folders.

## 5. Restore the old site if needed

If you need to reverse the publication, do not rewrite history. Restore from the archive through a new branch:

```bash
git switch -c restore-old-site archive/pre-redesign-2026-09-03
git push -u origin restore-old-site
```

Open a pull request from `restore-old-site` to `main`, merge it, and run `quarto publish gh-pages` again. The locally saved pre-redesign ZIP is the second recovery route.

# Make the Colab analysis work

## Is a new repository required?

No. The current button deliberately opens:

`https://colab.research.google.com/github/tahirali-biomics/tahirali-biomics.github.io/blob/main/notebooks/popgenlm-bench-demo.ipynb`

It will work when these files exist on the `main` branch of the website repository:

- `notebooks/popgenlm-bench-demo.ipynb`
- `assets/popgenlm/gpn-scores-100.tsv`
- `assets/popgenlm/summary.json`
- `assets/popgenlm/run-metadata.json`
- `assets/popgenlm/benchmark-overview.png`

All five are included here. The notebook also contains a compressed copy of the 100-variant fixture, so the verified analysis still runs if the raw GitHub download is temporarily unavailable.

## First Colab test

1. Publish or push the files above to the website repository's `main` branch.
2. Open the **PopGenLM** page and choose **Run verified analysis in Colab**.
3. In Colab choose **Runtime → Run all**.
4. Confirm these messages appear:
   - `Loaded 100 rows ...`
   - `Schema, coordinates, alleles, scores, and uniqueness checks passed`
   - `Created popgenlm_verified_outputs.zip`
5. Confirm that the four-panel benchmark figure is displayed.
6. To analyse your own compatible score table, set `ANALYSE_UPLOAD = True`, run that cell, and upload one TSV or CSV containing `chrom`, `pos`, `ref`, `alt`, and `score`.

The notebook performs a complete, CPU-friendly validation and reporting analysis. It intentionally does not download GPN model weights or infer new scores; that is a larger, version-pinned workflow.

## When to create the separate `popgenlm-bench` repository

Create `tahirali-biomics/popgenlm-bench` for the open-source Python package and full model-inference workflow. Keep the lightweight public Colab notebook in the website repository because the existing button then remains stable.

Recommended contents of the separate repository:

- `README.md` with scientific purpose, inputs, outputs and interpretation limits;
- `LICENSE`, `CITATION.cff`, `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md`;
- `pyproject.toml` and a locked dependency file;
- `src/popgenlm_bench/` for validation, model adapters, evaluation and reporting;
- `tests/` with small fixtures and reference/allele checks;
- `examples/` using only public data;
- `notebooks/` for optional full-inference demonstrations;
- `.github/workflows/` for tests and package checks;
- model/revision metadata, checksums and a reproducibility statement.

Do not commit private API keys, unpublished datasets, restricted teaching material, large model weights or institution-owned code whose licence is unclear.

## GPU use in Colab

GitHub stores code and data; it does not supply a GPU for ordinary repository execution. Google Colab can provide a GPU runtime, subject to availability and Colab's usage limits. In Colab choose **Runtime → Change runtime type → Hardware accelerator → GPU**, then verify it with:

```python
import torch
print(torch.cuda.is_available())
print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU runtime")
```

Use a GPU for full GPN inference only after pinning the package, model revision, reference assembly and input checks. The included 100-variant validation notebook is intentionally CPU-compatible and does not need a GPU.
