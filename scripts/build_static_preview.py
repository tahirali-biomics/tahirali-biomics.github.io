from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

from lxml import etree, html

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"

PAGES = [
    (ROOT / "index.qmd", SITE / "index.html", False, False, "home-page"),
    (ROOT / "popgenlm.qmd", SITE / "popgenlm.html", False, False, "popgenlm-page"),
    (ROOT / "genomes-to-ai.qmd", SITE / "genomes-to-ai.html", False, True, "genomes-ai-page"),
    (ROOT / "projects.qmd", SITE / "projects.html", True, False, "projects-page"),
    (ROOT / "teaching" / "teaching.qmd", SITE / "teaching" / "teaching.html", False, False, "teaching-page"),
    (ROOT / "workshops" / "workshops.qmd", SITE / "workshops" / "workshops.html", False, False, "workshops-page"),
    (ROOT / "teaching" / "tutorials" / "Hands-on Genomics Tutorials.qmd", SITE / "teaching" / "tutorials" / "Hands-on Genomics Tutorials.html", True, False, "tutorial-index-page"),
    (ROOT / "teaching" / "course-companions" / "interactive-course-companions.qmd", SITE / "teaching" / "course-companions" / "interactive-course-companions.html", True, False, "course-companions-page content-dense"),
]

POSTS = [
    ("2026-01-10-inheritance-becomes-information", "reading-note-page"),
    ("2026-01-24-the-model-is-a-choice", "reading-note-page"),
    ("2026-02-07-meaning-lives-in-relationships", "reading-note-page"),
    ("2026-02-21-uncertainty-reveals-structure", "reading-note-page"),
    ("2026-03-07-what-does-a-gene-know", "reading-note-page"),
    ("2026-08-31-popgenlm-bench", ""),
]
for slug, extra_class in POSTS:
    PAGES.append((ROOT / "posts" / slug / "index.qmd", SITE / "posts" / slug / "index.html", True, False, f"article-page content-dense {extra_class}".strip()))

POST_TEMPLATE = SITE / "posts" / "2026-08-31-popgenlm-bench" / "index.html"
LEGACY_TUTORIALS = {"practical_day4.html", "Practical_Day_6.html"}
GENERATED_RELATIVE = {target.relative_to(SITE).as_posix() for _, target, *_ in PAGES}

NAVIGATION = [
    ("Home", "index.html"), ("PopGenLM", "popgenlm.html"),
    ("Genomes to AI", "genomes-to-ai.html"), ("Projects", "projects.html"),
    ("Publications", "publications.html"), ("Résumé", "cv.html"),
    ("Teaching", "teaching/teaching.html"), ("Workshops", "workshops/workshops.html"),
]

PRACTICAL_OUTPUT_GROUPS: dict[str, list[tuple[str, list[tuple[str, str]]]]] = {
    "practical_day1.html": [
        ("ggplot(mapq_summary", [
            ("unnamed-chunk-1-1.png", "Density distribution of mapping-quality scores across BAM files."),
            ("unnamed-chunk-1-2.png", "Read counts across mapping-quality scores for each BAM file."),
        ]),
    ],
    "practical_day2.html": [
        ("saveWidget(pca_3d", [
            ("unnamed-chunk-1-1.png", "PCA eigenvalues for the first ten components."),
            ("unnamed-chunk-1-2.png", "Percentage of genetic variance explained by each principal component."),
            ("unnamed-chunk-1-3.png", "Population structure on PC1 and PC2."),
            ("unnamed-chunk-1-4.png", "Population structure on PC1 and PC3."),
            ("unnamed-chunk-1-5.png", "Population structure on PC2 and PC3."),
            ("unnamed-chunk-1-6.png", "Sample-labelled PC1–PC2 ordination for diagnostic review."),
        ]),
    ],
    "practical_day3.html": [
        ("print(p_ks)", [
            ("unnamed-chunk-3-1.png", "GO enrichment ranked by Fisher-test significance."),
            ("unnamed-chunk-3-2.png", "GO enrichment ranked by Kolmogorov–Smirnov significance."),
        ]),
        ("p <- ggplot(sub2", [
            *[(f"unnamed-chunk-7-{n}.png", f"Population-genomic analysis output {n}.") for n in range(1, 26)],
        ]),
        ("write.table(samples_bio", [
            ("unnamed-chunk-8-1.png", "Annual mean temperature across the sampled European region."),
            ("unnamed-chunk-8-2.png", "Annual precipitation across the sampled European region."),
        ]),
    ],
}

EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF\uFE0F\u20E3]")
DECORATIVE_MARKS = str.maketrans({"✅": "", "❌": "", "⚠": "", "🔗": "", "🧬": ""})


def parse_document(path: Path) -> etree._Element:
    return html.document_fromstring(path.read_text(encoding="utf-8", errors="replace"))


def write_document(path: Path, document: etree._Element) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = etree.tostring(document, method="html", encoding="unicode", doctype="<!DOCTYPE html>", pretty_print=False)
    path.write_text(rendered, encoding="utf-8")


def qmd_metadata(source: Path) -> dict[str, object]:
    text = source.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    header = text.split("---", 2)[1]
    result: dict[str, object] = {}
    key: str | None = None
    for line in header.splitlines():
        item = re.match(r"^\s*-\s+(.+)$", line)
        if item and key:
            result.setdefault(key, [])
            assert isinstance(result[key], list)
            result[key].append(item.group(1).strip().strip('"\''))
            continue
        match = re.match(r"^([\w-]+):\s*(.*)$", line)
        if not match:
            continue
        key, value = match.groups()
        result[key] = value.strip().strip('"\'') if value else []
    return result


def pandoc_fragment(source: Path) -> etree._Element:
    rendered = subprocess.check_output(["pandoc", str(source), "--from", "markdown+raw_html", "--to", "html", "--wrap=none"], text=True)
    return html.fragment_fromstring(f"<div>{rendered}</div>")


def add_classes(element: etree._Element, classes: str) -> None:
    current = set((element.get("class") or "").split())
    current.update(classes.split())
    element.set("class", " ".join(sorted(current)))


def sync_title_block(document: etree._Element, source: Path) -> None:
    metadata = qmd_metadata(source)
    title = str(metadata.get("title", source.stem))
    description = str(metadata.get("description", ""))
    published = str(metadata.get("date", ""))
    author = str(metadata.get("author", "Dr Tahir Ali"))
    categories = metadata.get("categories", [])
    for node in document.xpath('//*[@id="title-block-header"]//h1[contains(@class,"title")]'):
        node.text = title
    for node in document.xpath('//*[@id="title-block-header"]//*[contains(concat(" ", normalize-space(@class), " "), " description ")]'):
        node.text = description
    author_nodes = document.xpath('//*[@id="title-block-header"]//*[contains(concat(" ", normalize-space(@class), " "), " author ")]')
    if author_nodes:
        author_nodes[0].text = author
    if published:
        try:
            display_date = datetime.strptime(published, "%Y-%m-%d").strftime("%B %-d, %Y")
        except ValueError:
            display_date = published
        for node in document.xpath('//*[@id="title-block-header"]//p[contains(concat(" ", normalize-space(@class), " "), " date ")]'):
            node.text = display_date
    category_boxes = document.xpath('//*[@id="title-block-header"]//*[contains(concat(" ", normalize-space(@class), " "), " quarto-categories ")]')
    if category_boxes and isinstance(categories, list):
        box = category_boxes[0]
        for child in list(box):
            box.remove(child)
        box.text = None
        for category in categories:
            item = html.Element("div", {"class": "quarto-category"})
            item.text = str(category)
            box.append(item)
    title_nodes = document.xpath("//head/title")
    if title_nodes:
        title_nodes[0].text = f"{title} – Dr. Tahir Ali"
    for meta in document.xpath('//meta[@name="description"] | //meta[@property="og:description"]'):
        meta.set("content", description)


def prepare_post_targets() -> None:
    if not POST_TEMPLATE.exists():
        raise RuntimeError(f"Post template missing: {POST_TEMPLATE}")
    for slug, _ in POSTS:
        target = SITE / "posts" / slug / "index.html"
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(POST_TEMPLATE, target)


def replace_main(source: Path, target: Path, keep_title: bool, keep_listing: bool, body_classes: str) -> None:
    document = parse_document(target)
    main_nodes = document.xpath('//*[@id="quarto-document-content"]')
    if not main_nodes:
        raise RuntimeError(f"Main content not found in {target}")
    main = main_nodes[0]
    preserved: list[etree._Element] = []
    if keep_title:
        title = main.xpath('./header[@id="title-block-header"]')
        if title:
            preserved.append(title[0])
    listing = main.xpath('.//*[@id="listing-listing"]') if keep_listing else []
    for child in list(main):
        main.remove(child)
    main.text = None
    for node in preserved:
        main.append(node)
    fragment = pandoc_fragment(source)
    for child in list(fragment):
        fragment.remove(child)
        main.append(child)
    if listing:
        main.append(listing[0])
    add_classes(document.xpath("//body")[0], body_classes)
    if keep_title:
        sync_title_block(document, source)
    write_document(target, document)


def post_image(source: Path, metadata: dict[str, object]) -> str:
    image_path = str(metadata.get("image", ""))
    if not image_path:
        return "assets/popgenlm/benchmark-overview.png"
    resolved = (source.parent / image_path).resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return image_path


def rebuild_journal_listing() -> None:
    target = SITE / "genomes-to-ai.html"
    document = parse_document(target)
    holders = document.xpath('//*[@id="listing-listing"]')
    if not holders:
        raise RuntimeError("Journal listing container missing")
    holder = holders[0]
    for child in list(holder):
        holder.remove(child)
    grid = html.Element("div", {"class": "list grid quarto-listing-cols-2"})
    records = []
    for slug, _ in POSTS:
        source = ROOT / "posts" / slug / "index.qmd"
        records.append((str(qmd_metadata(source).get("date", "")), slug, source, qmd_metadata(source)))
    for index, (published, slug, source, metadata) in enumerate(sorted(records, reverse=True)):
        column = html.Element("div", {"class": "g-col-1", "data-index": str(index)})
        anchor = html.Element("a", {"href": f"./posts/{slug}/index.html", "class": "quarto-grid-link"})
        card = html.Element("article", {"class": "quarto-grid-item card h-100 card-left"})
        image_wrap = html.Element("p", {"class": "card-img-top"})
        image_wrap.append(html.Element("img", {"src": f"./{post_image(source, metadata)}", "class": "thumbnail-image card-img", "alt": f"Concept sketch for {metadata.get('title', slug)}", "loading": "lazy", "decoding": "async"}))
        card.append(image_wrap)
        body = html.Element("div", {"class": "card-body post-contents"})
        title = html.Element("h3", {"class": "no-anchor card-title listing-title"})
        title.text = str(metadata.get("title", slug))
        description = html.Element("div", {"class": "card-text listing-description delink"})
        paragraph = html.Element("p")
        paragraph.text = str(metadata.get("description", ""))
        description.append(paragraph)
        attribution = html.Element("div", {"class": "card-attribution card-text-small justify"})
        author = html.Element("div", {"class": "listing-author"})
        author.text = str(metadata.get("author", "Dr Tahir Ali"))
        shown_date = html.Element("time", {"class": "listing-date", "datetime": published})
        try:
            shown_date.text = datetime.strptime(published, "%Y-%m-%d").strftime("%b %-d, %Y")
        except ValueError:
            shown_date.text = published
        attribution.extend([author, shown_date])
        body.extend([title, description, attribution])
        card.append(body)
        anchor.append(card)
        column.append(anchor)
        grid.append(column)
    holder.append(grid)
    no_match = html.Element("div", {"class": "listing-no-matching d-none"})
    no_match.text = "No matching items"
    holder.append(no_match)
    write_document(target, document)


def relative_link(page: Path, site_root: Path, target: str) -> str:
    return Path(os.path.relpath(site_root / target, page.parent)).as_posix()


def rendered_css_asset(kind: str) -> str:
    """Return the CSS asset selected by the current Quarto render.

    Quarto content hashes dependency filenames.  Reading the freshly rendered
    home page keeps the post-processing step compatible across Quarto releases
    instead of pinning hashes from the version used to create the archive.
    """
    home = SITE / "index.html"
    if not home.exists():
        raise RuntimeError("Rendered home page missing; run `quarto render` first")

    document = parse_document(home)
    for link in document.xpath("//link[@href]"):
        href = link.get("href") or ""
        is_match = (
            kind == "syntax" and "quarto-syntax-highlighting-" in href
        ) or (
            kind == "bootstrap"
            and "/bootstrap/bootstrap-" in href
            and href.endswith(".min.css")
        )
        if not is_match:
            continue
        clean = unquote(href.split("?", 1)[0].split("#", 1)[0]).lstrip("./")
        if (SITE / clean).exists():
            return clean

    if kind == "syntax":
        candidates = sorted((SITE / "site_libs" / "quarto-html").glob("quarto-syntax-highlighting-*.css"))
    elif kind == "bootstrap":
        candidates = sorted((SITE / "site_libs" / "bootstrap").glob("bootstrap-*.min.css"))
    else:
        raise ValueError(f"Unknown CSS dependency kind: {kind}")

    if not candidates:
        raise RuntimeError(f"Current Quarto {kind} stylesheet was not found in _site/site_libs")
    return candidates[-1].relative_to(SITE).as_posix()


def active_target(relative: Path) -> str:
    rel = relative.as_posix()
    if rel.startswith("teaching/"):
        return "teaching/teaching.html"
    if rel.startswith("workshops/"):
        return "workshops/workshops.html"
    if rel.startswith("posts/"):
        return "genomes-to-ai.html"
    return rel


def make_quarto_nav(page: Path, site_root: Path, current: Path) -> list[etree._Element]:
    items: list[etree._Element] = []
    current_target = active_target(current)
    for text, target in NAVIGATION:
        li = html.Element("li", {"class": "sidebar-item"})
        container = html.Element("div", {"class": "sidebar-item-container"})
        classes = "sidebar-item-text sidebar-link" + (" active" if current_target == target else "")
        anchor = html.Element("a", {"href": relative_link(page, site_root, target), "class": classes})
        label = html.Element("span", {"class": "menu-text"})
        label.text = text
        anchor.append(label)
        container.append(anchor)
        li.append(container)
        items.append(li)
    li = html.Element("li", {"class": "sidebar-item"})
    container = html.Element("div", {"class": "sidebar-item-container"})
    anchor = html.Element("a", {"href": "https://github.com/tahirali-biomics", "class": "sidebar-item-text sidebar-link", "target": "_blank"})
    label = html.Element("span", {"class": "menu-text"})
    label.text = "GitHub"
    anchor.append(label)
    container.append(anchor)
    li.append(container)
    items.append(li)
    return items


def ensure_stylesheet(document: etree._Element, page: Path, site_root: Path) -> None:
    expected = relative_link(page, site_root, "styles.css")
    links = document.xpath('//link[contains(@href, "styles.css")]')
    if links:
        links[-1].set("href", expected)
    else:
        document.xpath("//head")[0].append(html.Element("link", {"rel": "stylesheet", "href": expected}))


def slugify(text: str, used: set[str]) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "section"
    base, number = slug, 2
    while slug in used:
        slug = f"{base}-{number}"
        number += 1
    used.add(slug)
    return slug


def clean_visible_text(value: str) -> str:
    return " ".join(EMOJI_RE.sub("", value.translate(DECORATIVE_MARKS)).replace("¶", "").split())


def remove_decorative_text(value: str | None) -> str | None:
    if value is None:
        return None
    return EMOJI_RE.sub("", value.translate(DECORATIVE_MARKS))


def strip_decorative_marks(document: etree._Element) -> None:
    excluded = {"pre", "code", "script", "style", "textarea"}
    for node in document.xpath("//body//*"):
        if node.tag in excluded or any(ancestor.tag in excluded for ancestor in node.iterancestors()):
            continue
        node.text = remove_decorative_text(node.text)
        for child in node:
            child.tail = remove_decorative_text(child.tail)
    for title in document.xpath("//head/title"):
        title.text = remove_decorative_text(title.text)
    for metadata in document.xpath('//head/meta[@content]'):
        key = (metadata.get("property") or metadata.get("name") or "").lower()
        if key in {"title", "description", "og:title", "og:description", "twitter:title", "twitter:description"}:
            metadata.set("content", remove_decorative_text(metadata.get("content")) or "")


def toc_label(heading: etree._Element) -> str:
    return clean_visible_text(heading.text_content())


def meaningful_headings(document: etree._Element, page: Path) -> list[etree._Element]:
    scopes = document.xpath('//*[@id="quarto-document-content"] | //main | //*[@class="main-container"]')
    scope = scopes[0] if scopes else document.xpath("//body")[0]
    candidates = [
        heading for heading in scope.xpath('.//*[self::h1 or self::h2 or self::h3]')
        if toc_label(heading)
        and toc_label(heading).lower() != "contents"
        and not heading.xpath('ancestor::nav | ancestor::aside | ancestor::header[@id="title-block-header"]')
    ]
    if not candidates:
        return []

    preferred_terms: dict[str, list[str]] = {
        "practical_day4.html": [
            "summary", "analysis overview", "0. setup", "1. load", "2. define", "3. read vcf",
            "5. create sliding windows", "6. calculate", "8. genome-wide", "9. annotate",
            "13. fst outlier", "interpretation",
        ],
        "Practical_Day_6.html": [
            "overview", "practical setup", "conceptual", "0. required", "1. load", "2. visualise",
            "3. gene annotation", "4. identify", "5. go", "6. interactive", "7. visualisation",
            "9. analysis summary",
        ],
        "awk_sed_reference.html": [
            "introduction", "category 1", "category 2", "category 3", "category 5", "category 7",
            "category 8", "category 9", "category 10", "category 11", "category 14", "common pitfalls",
        ],
    }
    if page.name in preferred_terms:
        selected: list[etree._Element] = []
        used_nodes: set[int] = set()
        for term in preferred_terms[page.name]:
            for heading in candidates:
                if id(heading) in used_nodes:
                    continue
                if term in toc_label(heading).lower():
                    selected.append(heading)
                    used_nodes.add(id(heading))
                    break
        if selected:
            return selected[:12]

    levels = {tag: [heading for heading in candidates if heading.tag == tag] for tag in ("h1", "h2", "h3")}
    if len(levels["h1"]) >= 3:
        selected = levels["h1"]
    elif len(levels["h2"]) >= 4:
        selected = levels["h2"]
    elif len(levels["h3"]) >= 4:
        selected = levels["h3"]
    elif levels["h2"]:
        selected = levels["h2"]
    else:
        selected = candidates
    if len(selected) > 12:
        selected = selected[:10] + selected[-2:]
    return selected


def heading_container_id(heading: etree._Element) -> str | None:
    """Return the stable section wrapper used by legacy Quarto exports."""
    for ancestor in heading.iterancestors():
        if ancestor.tag in {"main", "body"}:
            break
        if ancestor.tag in {"section", "div"} and ancestor.get("id"):
            return ancestor.get("id")
    return None


def heading_target_id(heading: etree._Element, prefer_container: bool = False) -> str | None:
    if prefer_container:
        container_id = heading_container_id(heading)
        if container_id:
            return container_id
    return heading.get("id")


def ensure_heading_ids(
    document: etree._Element,
    headings: list[etree._Element],
    prefer_container: bool = False,
) -> None:
    used = {node.get("id") for node in document.xpath('//*[@id]') if node.get("id")}
    for heading in headings:
        if not heading_target_id(heading, prefer_container):
            heading.set("id", slugify(toc_label(heading), used))


def append_flat_toc(
    container: etree._Element,
    headings: list[etree._Element],
    prefer_container: bool = False,
) -> None:
    toc_list = html.Element("ul", {"class": "technical-toc-list"})
    for heading in headings:
        target_id = heading_target_id(heading, prefer_container)
        if not target_id:
            continue
        item = html.Element("li")
        anchor = html.Element("a", {"href": f"#{target_id}"})
        anchor.text = toc_label(heading)
        item.append(anchor)
        toc_list.append(item)
    container.append(toc_list)


def remove_legacy_chrome(document: etree._Element) -> None:
    selector = '//*[@id="legacy-site-nav"] | //*[contains(concat(" ", normalize-space(@class), " "), " legacy-menu-toggle ")] | //*[contains(concat(" ", normalize-space(@class), " "), " legacy-toc-nav ")] | //*[contains(concat(" ", normalize-space(@class), " "), " legacy-inline-toc ")]'
    for node in list(document.xpath(selector)):
        if node.getparent() is not None:
            node.getparent().remove(node)
    for script in list(document.xpath('//script[contains(text(), "legacy-menu-open")]')):
        if script.getparent() is not None:
            script.getparent().remove(script)


def inject_notebook_navigation(document: etree._Element, page: Path, site_root: Path, current: Path, tutorial: bool) -> None:
    remove_legacy_chrome(document)
    body = document.xpath("//body")[0]
    add_classes(body, "legacy-notebook-page technical-page content-dense")
    if tutorial:
        add_classes(body, "legacy-tutorial-page")
    if page.name == "Temporal_Genomics_Workshop_TemporalGenomics.html":
        add_classes(body, "wide-output-page")
    button = html.Element("button", {"class": "legacy-menu-toggle", "type": "button", "aria-controls": "legacy-site-nav", "aria-expanded": "false"})
    button.text = "Menu"
    nav = html.Element("nav", {"id": "legacy-site-nav", "class": "legacy-site-nav", "aria-label": "Primary navigation"})
    brand = html.Element("a", {"href": relative_link(page, site_root, "index.html"), "class": "legacy-site-brand"})
    brand.text = "Dr. Tahir Ali"
    nav.append(brand)
    current_target = active_target(current)
    for text, target in NAVIGATION:
        anchor = html.Element("a", {"href": relative_link(page, site_root, target), "class": "active" if current_target == target else ""})
        anchor.text = text
        nav.append(anchor)
    github = html.Element("a", {"href": "https://github.com/tahirali-biomics", "target": "_blank"})
    github.text = "GitHub"
    nav.append(github)
    toc = html.Element("aside", {"class": "legacy-toc-nav", "aria-label": "Contents"})
    title = html.Element("div", {"class": "legacy-toc-title"})
    title.text = "Contents"
    toc.append(title)
    headings = meaningful_headings(document, page)
    ensure_heading_ids(document, headings, prefer_container=tutorial)
    append_flat_toc(toc, headings, prefer_container=tutorial)
    inline_toc = html.Element("details", {"class": "legacy-inline-toc", "open": "open"})
    inline_title = html.Element("summary")
    inline_title.text = "Contents"
    inline_toc.append(inline_title)
    append_flat_toc(inline_toc, headings, prefer_container=tutorial)
    script = html.Element("script")
    script.text = """(() => { const b=document.querySelector('.legacy-menu-toggle'); if(!b)return; b.addEventListener('click',()=>{const o=document.body.classList.toggle('legacy-menu-open'); b.setAttribute('aria-expanded',String(o));}); })();"""
    body.insert(0, toc)
    body.insert(0, nav)
    body.insert(0, button)
    main = body.xpath("./main")
    if main:
        main[0].addprevious(inline_toc)
    else:
        body.insert(3, inline_toc)
    body.append(script)


def normalise_technical_toc(document: etree._Element, page: Path) -> None:
    for nav in document.xpath('//nav[@role="doc-toc"]'):
        title = nav.xpath('./h2 | ./*[contains(concat(" ", normalize-space(@class), " "), " toc-title ")]')
        if title:
            title[0].text = "Contents"
        for listing in list(nav.xpath('.//ul')):
            if listing.getparent() is not None:
                listing.getparent().remove(listing)
        headings = meaningful_headings(document, page)
        ensure_heading_ids(document, headings)
        append_flat_toc(nav, headings)


def remove_page_code_tools(document: etree._Element) -> None:
    selectors = [
        '//button[contains(concat(" ", normalize-space(@class), " "), " code-tools-button ")]',
        '//*[@id="quarto-embedded-source-code-modal"]',
        '//*[contains(concat(" ", normalize-space(@class), " "), " code-tools-menu ")]',
    ]
    for selector in selectors:
        for node in list(document.xpath(selector)):
            if node.getparent() is not None:
                node.getparent().remove(node)


def normalise_popgenlm_images(document: etree._Element, page: Path, site_root: Path) -> None:
    if page.name not in {"popgenlm.html", "genomes-to-ai.html", "index.html"} and "2026-08-31-popgenlm-bench" not in page.as_posix():
        return
    benchmark = relative_link(page, site_root, "assets/popgenlm/benchmark-overview.png")
    for image in document.xpath('//img[contains(@src,"score-distribution") or contains(@src,"benchmark-overview")]'):
        image.set("src", benchmark)
        image.set("alt", "Four-panel PopGenLM Bench validation overview")
        for attribute in ("style", "height", "width"):
            image.attrib.pop(attribute, None)


def normalise_image_loading(document: etree._Element) -> None:
    for image in document.xpath("//img"):
        if "hero-profile" in set((image.get("class") or "").split()):
            image.set("loading", "eager")
            image.set("fetchpriority", "high")
        else:
            image.set("loading", "lazy")
            image.set("decoding", "async")


def code_summary() -> etree._Element:
    summary = html.Element("summary", {"class": "code-details-summary"})
    label = html.Element("span", {"class": "code-toggle-label", "aria-hidden": "true"})
    label.append(html.Element("span", {"class": "code-label-closed"}))
    label[-1].text = "Show code"
    label.append(html.Element("span", {"class": "code-label-open"}))
    label[-1].text = "Hide code"
    hint = html.Element("span", {"class": "code-hint"})
    hint.text = "Copyable source"
    summary.extend([label, hint])
    return summary


def has_copy_button(node: etree._Element) -> bool:
    return bool(node.xpath('.//button[contains(@class,"code-copy") or contains(@class,"technical-copy-button")]'))


def add_copy_button(details: etree._Element) -> None:
    if has_copy_button(details):
        return
    button = html.Element("button", {"type": "button", "class": "technical-copy-button", "aria-label": "Copy code"})
    button.text = "Copy"
    summary = details.xpath('./summary')[0]
    summary.append(button)


def wrap_code_target(target: etree._Element) -> etree._Element:
    existing = target.xpath('ancestor::details[contains(concat(" ", normalize-space(@class), " "), " code-details ")]')
    if existing:
        return existing[0]
    parent = target.getparent()
    if parent is None:
        return target
    details = html.Element("details", {"class": "code-details"})
    summary = code_summary()
    panel = html.Element("div", {"class": "code-panel-body"})
    parent.replace(target, details)
    panel.append(target)
    details.extend([summary, panel])
    add_copy_button(details)
    return details


def make_code_collapsible(document: etree._Element) -> None:
    for details in document.xpath('//details[contains(concat(" ", normalize-space(@class), " "), " code-fold ")]'):
        add_classes(details, "code-details")
        summaries = details.xpath('./summary')
        if summaries:
            details.replace(summaries[0], code_summary())
        else:
            details.insert(0, code_summary())
        add_copy_button(details)

    selectors = [
        '//div[contains(concat(" ", normalize-space(@class), " "), " code-copy-outer-scaffold ")][not(ancestor::details[contains(@class,"code-details")])]',
        '//div[contains(concat(" ", normalize-space(@class), " "), " sourceCode ")][not(ancestor::div[contains(@class,"code-copy-outer-scaffold")])][not(ancestor::details[contains(@class,"code-details")])]',
        '//div[contains(concat(" ", normalize-space(@class), " "), " jp-Cell-inputWrapper ")][ancestor::div[contains(concat(" ", normalize-space(@class), " "), " jp-CodeCell ")]][not(ancestor::details[contains(@class,"code-details")])]',
        '//pre[(contains(@class,"sourceCode") or .//code[contains(@class,"sourceCode") or contains(@class,"language-")])][not(ancestor::div[contains(@class,"sourceCode")])][not(ancestor::div[contains(@class,"code-copy-outer-scaffold")])][not(ancestor::div[contains(@class,"jp-Cell-inputWrapper")])][not(ancestor::details[contains(@class,"code-details")])]',
    ]
    for selector in selectors:
        for target in list(document.xpath(selector)):
            wrap_code_target(target)

    if not document.xpath('//script[@id="technical-code-copy"]'):
        script = html.Element("script", {"id": "technical-code-copy"})
        script.text = """(() => { document.addEventListener('click', async (event) => { const button=event.target.closest('.technical-copy-button'); if(!button)return; event.preventDefault(); event.stopPropagation(); const details=button.closest('details'); const code=details?.querySelector('pre code, pre'); if(!code)return; const text=code.innerText; try { await navigator.clipboard.writeText(text); } catch (_) { const area=document.createElement('textarea'); area.value=text; area.style.position='fixed'; area.style.opacity='0'; document.body.appendChild(area); area.select(); document.execCommand('copy'); area.remove(); } const old=button.textContent; button.textContent='Copied'; setTimeout(()=>{button.textContent=old;},1400); }); })();"""
        document.xpath("//body")[0].append(script)


def code_container(node: etree._Element) -> etree._Element:
    for ancestor in node.iterancestors():
        if ancestor.tag == "details" and "code-details" in set((ancestor.get("class") or "").split()):
            return ancestor
    for ancestor in node.iterancestors():
        if "code-copy-outer-scaffold" in set((ancestor.get("class") or "").split()):
            return ancestor
    return node


def place_practical_outputs(document: etree._Element, page: Path, groups: list[tuple[str, list[tuple[str, str]]]]) -> None:
    for node in list(document.xpath('//*[@id="preserved-analysis-outputs"] | //*[contains(concat(" ", normalize-space(@class), " "), " preserved-output-group ")]')):
        if node.getparent() is not None:
            node.getparent().remove(node)
    for index, (token, files) in enumerate(groups, start=1):
        sources = document.xpath(f'//*[self::code or self::pre][contains(string(.), {json.dumps(token)})]')
        if not sources:
            raise RuntimeError(f"Could not place restored outputs in {page}: code token not found: {token}")
        grid = html.Element("div", {"class": "tutorial-output-grid preserved-output-group", "data-output-group": str(index)})
        for name, caption in files:
            image_path = page.parent / f"{page.stem}_files/figure-html/{name}"
            if not image_path.exists():
                raise RuntimeError(f"Restored output missing for {page}: {image_path}")
            figure = html.Element("figure")
            figure.append(html.Element("img", {"src": f"{page.stem}_files/figure-html/{name}", "alt": caption, "loading": "lazy", "decoding": "async"}))
            figcaption = html.Element("figcaption")
            figcaption.text = caption
            figure.append(figcaption)
            grid.append(figure)
        code_container(sources[0]).addnext(grid)


def replace_missing_figure_images(document: etree._Element, page: Path) -> int:
    count = 0
    for image in list(document.xpath("//img[@src]")):
        src = image.get("src") or ""
        if src.startswith(("http://", "https://", "data:", "//")):
            continue
        clean = unquote(src.split("?", 1)[0].split("#", 1)[0])
        if not clean or (page.parent / clean).resolve().exists():
            continue
        if "_files/figure-html/" not in clean and not clean.startswith("images/"):
            continue
        if page.name == "Hands-on-Session_2.html" and clean.endswith("clipboard-4195840738.png"):
            panel = html.fragment_fromstring(
                '<div class="formula-panel" role="figure" aria-label="Z-score standardisation concept">'
                '<strong>Z-score standardisation</strong>'
                '<div class="formula-expression">z = (x − mean) / standard deviation</div>'
                '<p>After standardisation, each predictor is centred near 0 and expressed in standard-deviation units. '
                'This makes effect sizes comparable while retaining the shape of each distribution.</p>'
                '<small>Concept panel retained because the original exported screenshot was not included with the archived session.</small>'
                '</div>'
            )
            if image.getparent() is not None:
                image.getparent().replace(image, panel)
            continue
        note = html.Element("div", {"class": "missing-asset-notice", "role": "note"})
        note.text = "Archived figure unavailable: the supplied page refers to an image that was not included in its original export. The analysis code remains available for reproducible re-rendering."
        if image.getparent() is not None:
            image.getparent().replace(image, note)
            count += 1
    return count


def normalise_legacy_dependencies(document: etree._Element, page: Path, site_root: Path) -> None:
    syntax_css = relative_link(page, site_root, rendered_css_asset("syntax"))
    bootstrap_css = relative_link(page, site_root, rendered_css_asset("bootstrap"))
    for link in document.xpath("//link[@href]"):
        href = link.get("href") or ""
        if "quarto-syntax-highlighting-" in href:
            link.set("href", syntax_css)
        elif "/bootstrap/bootstrap-" in href and href.endswith(".min.css"):
            link.set("href", bootstrap_css)
    for script in list(document.xpath('//script[contains(@src, "/axe/axe-check.js")]')):
        script.getparent().remove(script)
    if page.name != "sdm_biomode2_v2.html":
        return
    dependencies = ("htmltools-fill-", "htmlwidgets-", "jquery-", "leaflet-", "leafletfix-", "proj4-", "Proj4Leaflet-", "rstudio_leaflet-", "leaflet-binding-", "leaflet-providers-")
    for element in list(document.xpath("//head/link[@href] | //head/script[@src]")):
        reference = element.get("href") or element.get("src") or ""
        if any(dependency in reference for dependency in dependencies):
            element.getparent().remove(element)
    for widget in list(document.xpath('//div[contains(concat(" ", normalize-space(@class), " "), " html-widget ")]')):
        widget_id = widget.get("id")
        note = html.Element("div", {"class": "missing-asset-notice", "role": "note"})
        note.text = "Interactive map preserved as reproducible code: its archived Leaflet dependencies were not included. The static map and complete R code remain available."
        widget.getparent().replace(widget, note)
        if widget_id:
            for data_script in list(document.xpath(f'//script[@data-for="{widget_id}"]')):
                data_script.getparent().remove(data_script)


def normalise_notebook_anchors(document: etree._Element, page: Path) -> None:
    if page.name == "Temporal_Genomics_Workshop_TemporalGenomics.html":
        headings = document.xpath("//h1[@id] | //h2[@id] | //h3[@id]")
        heading_ids = {heading.get("id") for heading in headings if heading.get("id")}
        used = {
            element.get("id")
            for element in document.xpath('//*[@id]')
            if element.get("id") and element.get("id") not in heading_ids
        }
        mapping: dict[str, str] = {}
        for heading in headings:
            old_id = heading.get("id") or ""
            new_id = slugify(toc_label(heading), used)
            heading.set("id", new_id)
            mapping[old_id] = new_id
        for anchor in document.xpath('//a[starts-with(@href,"#")]'):
            old_fragment = unquote((anchor.get("href") or "")[1:])
            if old_fragment in mapping:
                anchor.set("href", f"#{mapping[old_fragment]}")


def patch_html_tree(site_root: Path, pages: list[Path]) -> int:
    missing = 0
    for page in pages:
        document = parse_document(page)
        relative = page.relative_to(site_root)
        technical = ((relative.as_posix().startswith("teaching/tutorials/") and relative.name != "Hands-on Genomics Tutorials.html") or (relative.as_posix().startswith("workshops/") and relative.name != "workshops.html"))
        body = document.xpath("//body")
        if body and technical:
            add_classes(body[0], "technical-page content-dense")
        ensure_stylesheet(document, page, site_root)
        normalise_legacy_dependencies(document, page, site_root)
        normalise_notebook_anchors(document, page)
        strip_decorative_marks(document)
        sidebars = document.xpath('//*[@id="quarto-sidebar"]')
        if sidebars:
            lists = sidebars[0].xpath('.//*[contains(concat(" ", normalize-space(@class), " "), " sidebar-menu-container ")]//ul[1]')
            if lists:
                menu = lists[0]
                for child in list(menu):
                    menu.remove(child)
                for item in make_quarto_nav(page, site_root, relative):
                    menu.append(item)
        elif technical:
            inject_notebook_navigation(document, page, site_root, relative, relative.name in LEGACY_TUTORIALS)
        normalise_technical_toc(document, page)
        if relative.name in PRACTICAL_OUTPUT_GROUPS:
            place_practical_outputs(document, page, PRACTICAL_OUTPUT_GROUPS[relative.name])
        if technical:
            make_code_collapsible(document)
        normalise_popgenlm_images(document, page, site_root)
        normalise_image_loading(document)
        remove_page_code_tools(document)
        missing += replace_missing_figure_images(document, page)
        write_document(page, document)
    return missing


def source_html_pages() -> list[Path]:
    return sorted({path for folder in (ROOT / "teaching", ROOT / "workshops") for path in folder.rglob("*.html") if SITE not in path.parents})


def copy_resources() -> None:
    shutil.copy2(ROOT / "styles.css", SITE / "styles.css")
    shutil.copy2(ROOT / "profile.webp", SITE / "profile.webp")
    for image in ROOT.glob("project*.webp"):
        shutil.copy2(image, SITE / image.name)
    for directory in (ROOT / "assets", ROOT / "notebooks"):
        shutil.copytree(directory, SITE / directory.name, dirs_exist_ok=True)
    for folder_name in ("teaching", "workshops"):
        folder = ROOT / folder_name
        for source in folder.rglob("*.html"):
            relative = source.relative_to(ROOT)
            if relative.as_posix() in GENERATED_RELATIVE:
                continue
            target = SITE / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        for directory in folder.rglob("*_files"):
            if directory.is_dir():
                shutil.copytree(directory, SITE / directory.relative_to(ROOT), dirs_exist_ok=True)
    figures = ROOT / "workshops" / "figs"
    if figures.exists():
        shutil.copytree(figures, SITE / "workshops" / "figs", dirs_exist_ok=True)


def refresh_search_index() -> int:
    records: list[dict[str, object]] = []
    for page in sorted(SITE.rglob("*.html")):
        document = parse_document(page)
        relative = page.relative_to(SITE).as_posix()
        title_nodes = document.xpath("//title")
        title = " ".join(title_nodes[0].text_content().split()) if title_nodes else page.stem
        title = re.sub(r"\s+[–—-]\s+Dr\.?\s*Tahir Ali.*$", "", title).strip()
        content = document.xpath('//*[@id="quarto-document-content"]') or document.xpath("//body")
        if content:
            records.append({"objectID": relative, "href": relative, "title": title, "section": "", "text": " ".join(content[0].text_content().split()), "crumbs": [title]})
    (SITE / "search.json").write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    return len(records)


def main() -> None:
    prepare_post_targets()
    for source, target, keep_title, keep_listing, body_classes in PAGES:
        replace_main(source, target, keep_title, keep_listing, body_classes)
    rebuild_journal_listing()
    source_pages = source_html_pages()
    source_missing = patch_html_tree(ROOT, source_pages)
    copy_resources()
    site_pages = sorted(SITE.rglob("*.html"))
    site_missing = patch_html_tree(SITE, site_pages)
    indexed = refresh_search_index()
    print(f"Updated {len(PAGES)} rendered content pages")
    print(f"Normalised navigation and contents across {len(source_pages) + len(site_pages)} HTML files")
    print(f"Replaced {source_missing + site_missing} unresolved legacy figure references with explicit notices")
    print(f"Refreshed search text for {indexed} current pages")


if __name__ == "__main__":
    main()
