# Website quality-assurance report

Date: 3 September 2026

## Verified build

- 43 HTML pages in the complete static site.
- 14 key QMD pages refreshed through the deterministic static-preview builder.
- Six `Genomes to AI` entries: five fortnightly Adami reading notes and the PopGenLM Bench build note.
- Seven working tutorial cards, including both restored research-project tutorials.
- Flat, linked Contents navigation on every technical tutorial and workshop page, limited to no more than 12 main sections.
- Page-level raw-source **Code** controls removed; each source block now opens and closes independently and retains a working copy control.
- Rendered Practical Day 1–3 outputs are placed immediately after the code that generates them; restored output groups contain 2, 6, and 2 + 25 + 2 figures respectively.
- 17 and 7 original embedded figures preserved on Research Project Parts 1 and 2.
- All supplied Hands-on Session figure folders restored; the one absent exported Z-score screenshot is represented transparently by a native explanatory formula panel.
- Four-panel PopGenLM benchmark overview displayed without fixed dimensions or cropping.
- Colab notebook executed successfully from a clean temporary directory using its embedded verified fallback fixture.
- Relative links, image sources, section anchors, primary navigation and shared stylesheet checked on every HTML page.
- Desktop/sidebar and responsive/mobile rules are shared across the website, archived notebooks and legacy tutorials; legacy menu text is fixed at readable pixel sizes.
- The home journey contains the retained four-paragraph personal narrative, the unboxed Dostoevsky quotation, and the ResearchGate `RG` mark.
- All eight research figures use whitespace-trimmed display copies with their complete borders preserved.
- The five Adami reading notes use the revised, thicker graphite notebook illustrations.

## Repeat the checks

```bash
python3 scripts/build_static_preview.py
python3 scripts/qa_site.py
```

Expected final line:

`Site QA passed: 43 HTML pages; seven tutorials; six journal entries; flat linked Contents lists; collapsible, copyable code; outputs immediately after generating code; complete local references; consistent responsive navigation; and optimised figures.`
