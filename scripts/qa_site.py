from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from lxml import html

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"
EXPECTED_NAV = ["Home", "PopGenLM", "Genomes to AI", "Projects", "Publications", "Résumé", "Teaching", "Workshops", "GitHub"]
EXPECTED_TUTORIALS = {
    "practical_day1.html", "practical_day2.html", "practical_day3.html",
    "practical_day4.html", "Practical_Day_6.html", "stacks_tutorial.html", "awk_sed_reference.html",
}
READING_POSTS = {
    "posts/2026-01-10-inheritance-becomes-information/index.html": ("When Life Became Legible", "January 10, 2026"),
    "posts/2026-01-24-the-model-is-a-choice/index.html": ("The Model Is Not the World", "January 24, 2026"),
    "posts/2026-02-07-meaning-lives-in-relationships/index.html": ("Meaning Lives Between Things", "February 7, 2026"),
    "posts/2026-02-21-uncertainty-reveals-structure/index.html": ("When Uncertainty Reveals Structure", "February 21, 2026"),
    "posts/2026-03-07-what-does-a-gene-know/index.html": ("What Does a Gene Know?", "March 7, 2026"),
}
PRACTICAL_IMAGE_MINIMUMS = {"practical_day1.html": 6, "practical_day2.html": 6, "practical_day3.html": 29}
LEGACY_TUTORIAL_IMAGE_COUNTS = {"practical_day4.html": 17, "Practical_Day_6.html": 7}
PRACTICAL_OUTPUT_GROUPS = {
    "practical_day1.html": [2],
    "practical_day2.html": [6],
    "practical_day3.html": [2, 25, 2],
}
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF\uFE0F\u20E3]|[✅❌⚠🔗🧬]")


def local_target(page: Path, reference: str) -> Path | None:
    if not reference or reference.startswith(("#", "http:", "https:", "mailto:", "tel:", "data:", "javascript:", "//")):
        return None
    parsed = urlparse(reference)
    local = unquote(parsed.path)
    if not local:
        return None
    return ((SITE / local.lstrip("/")) if local.startswith("/") else (page.parent / local)).resolve()


def classes(node) -> set[str]:
    return set((node.get("class") or "").split())


def main() -> None:
    problems: list[str] = []
    pages = sorted(SITE.rglob("*.html"))
    if len(pages) != 43:
        problems.append(f"expected 43 HTML pages; found {len(pages)}")

    for page in pages:
        relative = page.relative_to(SITE).as_posix()
        document = html.document_fromstring(page.read_text(encoding="utf-8", errors="replace"))
        ids = {element.get("id") for element in document.xpath('//*[@id]')}
        for element in document.xpath('//*[@href] | //*[@src]'):
            reference = element.get("href") or element.get("src") or ""
            target = local_target(page, reference)
            if target is not None and not target.exists():
                problems.append(f"{relative}: missing local reference {reference}")
        for anchor in document.xpath('//a[starts-with(@href, "#")]'):
            fragment = unquote((anchor.get("href") or "")[1:])
            if fragment and fragment not in ids:
                problems.append(f"{relative}: missing anchor #{fragment}")

        navigation = document.xpath('//*[@id="quarto-sidebar"] | //*[@id="legacy-site-nav"]')
        if not navigation:
            problems.append(f"{relative}: site navigation missing")
        else:
            labels = {" ".join(link.text_content().split()) for link in navigation[0].xpath('.//a')}
            for expected in EXPECTED_NAV:
                if expected not in labels:
                    problems.append(f"{relative}: navigation label missing: {expected}")
        if not document.xpath('//link[contains(@href, "styles.css")]'):
            problems.append(f"{relative}: shared stylesheet missing")
        if document.xpath('//button[contains(concat(" ", normalize-space(@class), " "), " code-tools-button ")] | //*[@id="quarto-embedded-source-code-modal"]'):
            problems.append(f"{relative}: page-level raw Code control remains")

        technical = ((relative.startswith("teaching/tutorials/") and page.name != "Hands-on Genomics Tutorials.html") or (relative.startswith("workshops/") and page.name != "workshops.html"))
        if technical:
            toc_links = document.xpath('//nav[@role="doc-toc"]//a[starts-with(@href,"#")] | //aside[contains(concat(" ", normalize-space(@class), " "), " legacy-toc-nav ")]//a[starts-with(@href,"#")]')
            if not toc_links:
                problems.append(f"{relative}: linked Contents list missing")
            elif len(toc_links) > 12:
                problems.append(f"{relative}: Contents list has {len(toc_links)} entries; expected at most 12")
            if document.xpath('//nav[@role="doc-toc"]//ul//ul | //aside[contains(@class,"legacy-toc-nav")]//ul//ul'):
                problems.append(f"{relative}: Contents list is nested instead of flat")
            code_outside_details = document.xpath(
                '//div[contains(concat(" ", normalize-space(@class), " "), " code-copy-outer-scaffold ")][not(ancestor::details[contains(@class,"code-details")])] | '
                '//div[contains(concat(" ", normalize-space(@class), " "), " sourceCode ")][not(ancestor::div[contains(@class,"code-copy-outer-scaffold")])][not(ancestor::details[contains(@class,"code-details")])] | '
                '//div[contains(concat(" ", normalize-space(@class), " "), " jp-Cell-inputWrapper ")][ancestor::div[contains(@class,"jp-CodeCell")]][not(ancestor::details[contains(@class,"code-details")])]'
            )
            if code_outside_details:
                problems.append(f"{relative}: {len(code_outside_details)} code input(s) remain outside collapsible panels")
            details = document.xpath('//details[contains(concat(" ", normalize-space(@class), " "), " code-details ")]')
            for detail in details:
                if not detail.xpath('.//button[contains(@class,"code-copy") or contains(@class,"technical-copy-button")]'):
                    problems.append(f"{relative}: collapsible code panel has no copy control")
                    break
            for heading in document.xpath('//h1 | //h2 | //h3'):
                if EMOJI_RE.search(heading.text_content()):
                    problems.append(f"{relative}: decorative emoji remains in a heading")
                    break

    home = html.document_fromstring((SITE / "index.html").read_text(encoding="utf-8"))
    if len(home.xpath('//*[contains(concat(" ", normalize-space(@class), " "), " story-section ")]')) != 1:
        problems.append("index.html: journey layout missing or duplicated")
    if home.xpath('//*[contains(concat(" ", normalize-space(@class), " "), " story-section ")]/aside'):
        problems.append("index.html: quote-style aside still occupies the journey grid")
    story_paragraphs = home.xpath('//*[contains(concat(" ", normalize-space(@class), " "), " story-copy ")]/p')
    if len(story_paragraphs) != 4:
        problems.append(f"index.html: expected four journey paragraphs; found {len(story_paragraphs)}")
    elif not story_paragraphs[0].text_content().strip().startswith("I am an evolutionary and computational biologist"):
        problems.append("index.html: original journey opening was not restored")
    if home.xpath('//*[contains(concat(" ", normalize-space(@class), " "), " story-aside ")]'):
        problems.append("index.html: removed journey sidebar is still present")
    quotes = home.xpath('//*[contains(concat(" ", normalize-space(@class), " "), " journey-quote ")]')
    if len(quotes) != 1 or "Dostoevsky" not in quotes[0].text_content():
        problems.append("index.html: unboxed Dostoevsky pull quote missing")
    if not home.xpath('//*[contains(concat(" ", normalize-space(@class), " "), " social-monogram ")][normalize-space()="RG"]'):
        problems.append("index.html: ResearchGate RG monogram missing")

    tutorial_index = html.document_fromstring((SITE / "teaching/tutorials/Hands-on Genomics Tutorials.html").read_text(encoding="utf-8"))
    tutorial_links = {Path(link.get("href") or "").name for link in tutorial_index.xpath('//a[contains(concat(" ", normalize-space(@class), " "), " card-link ")]')}
    if tutorial_links != EXPECTED_TUTORIALS:
        problems.append(f"tutorial index: expected seven tutorials; found {sorted(tutorial_links)}")
    for filename, minimum in PRACTICAL_IMAGE_MINIMUMS.items():
        document = html.document_fromstring((SITE / "teaching/tutorials" / filename).read_text(encoding="utf-8"))
        if len(document.xpath("//img")) < minimum:
            problems.append(f"{filename}: expected at least {minimum} rendered figures")
        groups = document.xpath('//*[contains(concat(" ", normalize-space(@class), " "), " preserved-output-group ")]')
        expected_groups = PRACTICAL_OUTPUT_GROUPS[filename]
        if [len(group.xpath('.//img')) for group in groups] != expected_groups:
            problems.append(f"{filename}: restored figure groups are incomplete or misplaced")
        for group in groups:
            if group.xpath('ancestor::details'):
                problems.append(f"{filename}: rendered output is hidden inside a code panel")
            previous = group.getprevious()
            if previous is None or previous.tag != "details" or "code-details" not in classes(previous):
                problems.append(f"{filename}: rendered output does not immediately follow its code")
    for filename, expected in LEGACY_TUTORIAL_IMAGE_COUNTS.items():
        document = html.document_fromstring((SITE / "teaching/tutorials" / filename).read_text(encoding="utf-8"))
        if len(document.xpath("//img")) != expected:
            problems.append(f"{filename}: expected {expected} embedded figures")
        if len(document.xpath('//aside[contains(@class,"legacy-toc-nav")]//a')) < 10:
            problems.append(f"{filename}: legacy linked Contents list is incomplete")

    journal = html.document_fromstring((SITE / "genomes-to-ai.html").read_text(encoding="utf-8"))
    cards = journal.xpath('//*[contains(concat(" ", normalize-space(@class), " "), " quarto-grid-item ")]')
    if len(cards) != 6:
        problems.append(f"genomes-to-ai.html: expected six journal cards; found {len(cards)}")
    for image in journal.xpath('//*[@id="listing-listing"]//img'):
        if image.get("style") or image.get("height") or image.get("width"):
            problems.append("genomes-to-ai.html: listing image still has a fixed/cropping dimension")

    for relative, (title, published) in READING_POSTS.items():
        page = SITE / relative
        if not page.exists():
            problems.append(f"missing reading post {relative}")
            continue
        document = html.document_fromstring(page.read_text(encoding="utf-8"))
        found_title = " ".join((document.xpath('//h1[contains(@class,"title")]')[0].text_content() if document.xpath('//h1[contains(@class,"title")]') else "").split())
        found_date = " ".join((document.xpath('//p[contains(@class,"date")]')[0].text_content() if document.xpath('//p[contains(@class,"date")]') else "").split())
        if found_title != title or found_date != published:
            problems.append(f"{relative}: title/date metadata mismatch")
        if len(document.xpath('//img[contains(concat(" ", normalize-space(@class), " "), " reading-sketch ")]')) != 1:
            problems.append(f"{relative}: concept sketch missing")
        if not document.xpath('//*[contains(concat(" ", normalize-space(@class), " "), " pencil-margin-note ")]'):
            problems.append(f"{relative}: margin-note section missing")

    popgen = html.document_fromstring((SITE / "popgenlm.html").read_text(encoding="utf-8"))
    if not popgen.xpath('//img[contains(@src,"benchmark-overview.png")]'):
        problems.append("popgenlm.html: four-panel benchmark overview missing")
    colab = popgen.xpath('//a[contains(@href,"colab.research.google.com/github/")]')
    if not colab or not (ROOT / "notebooks/popgenlm-bench-demo.ipynb").exists():
        problems.append("popgenlm.html: Colab link or notebook missing")

    teaching = html.document_fromstring((SITE / "teaching/teaching.html").read_text(encoding="utf-8"))
    teaching_labels = {" ".join(anchor.text_content().split()) for anchor in teaching.xpath('//nav[contains(@class,"page-section-nav")]//a')}
    expected_teaching = {"How I teach biology", "Interactive learning tools", "Principles behind the tools", "From concepts to independent analysis"}
    if teaching_labels != expected_teaching:
        problems.append("teaching.html: intuitive teaching section navigation is incomplete")

    projects = html.document_fromstring((SITE / "projects.html").read_text(encoding="utf-8"))
    project_sources = {image.get("src") for image in projects.xpath('//div[contains(@class,"project-media")]//img')}
    expected_projects = {f"assets/projects/project{number}.webp" for number in range(1, 9)}
    if project_sources != expected_projects:
        problems.append("projects.html: optimised project figures are not all in use")

    css = (ROOT / "styles.css").read_text(encoding="utf-8")
    if css.count("{") != css.count("}"):
        problems.append("styles.css: unbalanced braces")
    for required in ("width: 252px", "font-size: 20px !important", "font-size: 16px !important", "width: 270px", "font-size: 13px !important"):
        if required not in css:
            problems.append(f"styles.css: readable standalone-page sizing missing: {required}")
    if problems:
        print(f"Site QA failed with {len(problems)} problem(s):")
        for problem in problems:
            print(f"- {problem}")
        raise SystemExit(1)
    print("Site QA passed: 43 HTML pages; seven tutorials; six journal entries; flat linked Contents lists; collapsible, copyable code; outputs immediately after generating code; complete local references; consistent responsive navigation; and optimised figures.")


if __name__ == "__main__":
    main()
