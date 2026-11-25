#!/usr/bin/env python3
"""Render selected Quarto tutorials in an isolated, one-page website project."""

from __future__ import annotations

import argparse
import json
import re
import os
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STYLE_NAME = "styles-tutorial-code.css"
STYLE_MARKER = "tutorial-code-style"
SCRIPT_NAME = "tutorial-code-copy.js"
SCRIPT_MARKER = "tutorial-code-copy-script"


class BodyExtractor(HTMLParser):
    """Capture legacy document body markup while keeping its original text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.depth = 0
        self.active = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        raw = self.get_starttag_text()
        if tag.lower() == "body":
            self.active = True
            self.depth = 1
            return
        if self.active:
            self.parts.append(raw)
            if tag.lower() not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
                self.depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        raw = self.get_starttag_text()
        if tag.lower() == "body":
            self.active = True
            self.depth = 1
        elif self.active:
            self.parts.append(raw)

    def handle_endtag(self, tag: str) -> None:
        if not self.active:
            return
        if tag.lower() == "body" and self.depth == 1:
            self.active = False
            return
        self.parts.append(f"</{tag}>")
        if tag.lower() not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.depth -= 1

    def handle_data(self, data: str) -> None:
        if self.active:
            self.parts.append(data)

    def handle_entityref(self, name: str) -> None:
        if self.active:
            self.parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if self.active:
            self.parts.append(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        if self.active:
            self.parts.append(f"<!--{data}-->")


class ReferenceExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.values: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key in {"src", "href"} and value:
                self.values.append(value)


def insert_style_link(html: str, href: str) -> str:
    """Idempotently enable page-scoped CSS and mark the body for its selectors."""
    html = re.sub(rf'<link\b(?=[^>]*\bid=["\']{STYLE_MARKER}["\'])[^>]*>\s*', "", html, flags=re.I)
    tag = f'<link id="{STYLE_MARKER}" rel="stylesheet" href="{href}">\n'
    if re.search(r"</head\s*>", html, flags=re.I):
        html = re.sub(r"</head\s*>", tag + "</head>", html, count=1, flags=re.I)
    else:
        raise ValueError("Rendered HTML has no closing </head>")
    html = re.sub(r"<body\b([^>]*)>", _mark_body, html, count=1, flags=re.I)
    return html


def insert_script_link(html: str, href: str) -> str:
    html = re.sub(rf'<script\b(?=[^>]*\bid=["\']{SCRIPT_MARKER}["\'])[^>]*>\s*</script>\s*', "", html, flags=re.I)
    tag = f'<script id="{SCRIPT_MARKER}" src="{href}" defer></script>\n'
    if not re.search(r"</head\s*>", html, flags=re.I):
        raise ValueError("Rendered HTML has no closing </head>")
    return re.sub(r"</head\s*>", tag + "</head>", html, count=1, flags=re.I)


def _mark_body(match: re.Match[str]) -> str:
    opening = match.group(0)
    if re.search(r"\bclass\s*=", opening, flags=re.I):
        def add_scope(class_match: re.Match[str]) -> str:
            classes = class_match.group(2).split()
            if "tutorial-code-ready" not in classes:
                classes.append("tutorial-code-ready")
            return f'class={class_match.group(1)}{" ".join(classes)}{class_match.group(1)}'
        return re.sub(r"\bclass\s*=\s*([\"'])(.*?)\1", add_scope, opening, count=1, flags=re.I)
    return opening[:-1] + ' class="tutorial-code-ready">'


def merge_legacy_body(rendered: str, legacy_path: Path) -> str:
    legacy = BodyExtractor()
    legacy.feed(legacy_path.read_text(encoding="utf-8"))
    body = "".join(legacy.parts).strip()
    if not body:
        raise ValueError(f"Could not extract a non-empty body from {legacy_path}")
    opening = re.search(r"<main\b[^>]*\bid=[\"']quarto-document-content[\"'][^>]*>", rendered, flags=re.I)
    if not opening:
        raise ValueError("Rendered Quarto page has no #quarto-document-content main element")
    closing = re.search(r"</main\s*>", rendered[opening.end():], flags=re.I)
    if not closing:
        raise ValueError("Rendered Quarto content main element is not closed")
    end = opening.end() + closing.start()
    # Keep the Quarto page title and site shell; retain the old rendered tutorial body verbatim.
    return rendered[:opening.end()] + "\n" + body + "\n" + rendered[end:]


def copy_input_tree(source: Path, project: Path) -> Path:
    try:
        relative = source.resolve().relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"Source must be inside the repository: {source}") from exc
    dest = project / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    # Copy sibling resources without touching or modifying the source directory.
    for item in source.parent.iterdir():
        if item == source or item.name.startswith("."):
            continue
        target = dest.parent / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        elif item.is_file():
            shutil.copy2(item, target)
    return dest


def inject_figures(copied_source: Path, original_source: Path, manifest: Path) -> None:
    """Add standard Markdown images to the temporary copy at exact text anchors."""
    entries = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        raise ValueError("Figure map must be a JSON list of {after, image, caption} objects")
    text = copied_source.read_text(encoding="utf-8")
    for index, item in enumerate(entries, 1):
        if not isinstance(item, dict) or not all(key in item for key in ("after", "image", "caption")):
            raise ValueError(f"Figure map entry {index} needs after, image, and caption")
        anchor = str(item["after"])
        image = (original_source.parent / str(item["image"])).resolve()
        if not image.is_file():
            raise ValueError(f"Figure file not found: {image}")
        try:
            image_relative = image.relative_to(original_source.parent.resolve()).as_posix()
        except ValueError as exc:
            raise ValueError(f"Figure must be inside the source tutorial directory: {image}") from exc
        if text.count(anchor) != 1:
            raise ValueError(f"Figure anchor must occur exactly once (entry {index}): {anchor!r}")
        markdown = f"\n\n![{item['caption']}]({image_relative})\n"
        text = text.replace(anchor, anchor + markdown, 1)
    copied_source.write_text(text, encoding="utf-8")


def build(source: Path, destination: Path, legacy_html: Path | None, figure_map: Path | None, base_css: Path | None, keep_build: bool) -> Path:
    source = source.resolve()
    destination = destination.resolve()
    if source.suffix.lower() not in {".qmd", ".md"} or not source.is_file():
        raise ValueError(f"Source must be an existing .qmd or .md file: {source}")
    if legacy_html is not None and not legacy_html.is_file():
        raise ValueError(f"Legacy rendered HTML not found: {legacy_html}")
    if destination.exists() and any(destination.iterdir()):
        raise ValueError(f"Output directory must be absent or empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)

    temp_context = tempfile.TemporaryDirectory(prefix="quarto-tutorial-")
    project = Path(temp_context.name)
    for name in ("_quarto.yml", "styles.css", "profile.webp"):
        candidate = ROOT / name
        if candidate.is_file():
            shutil.copy2(candidate, project / name)
    if base_css is not None:
        if not base_css.is_file():
            raise ValueError(f"Base site stylesheet not found: {base_css}")
        shutil.copy2(base_css.resolve(), project / "styles.css")
    project_config = project / "_quarto.yml"
    if project_config.is_file():
        # This full-site hook assumes index.html and all archived pages exist.
        # A one-page build keeps all website settings but omits that unrelated hook.
        config_text = project_config.read_text(encoding="utf-8")
        config_text = re.sub(r"(?m)^\s*post-render:\s*[^\n]*\n", "", config_text)
        project_config.write_text(config_text, encoding="utf-8")
    shutil.copy2(ROOT / STYLE_NAME, project / STYLE_NAME)
    shutil.copy2(ROOT / "scripts" / "tutorials" / SCRIPT_NAME, project / SCRIPT_NAME)
    copied_source = copy_input_tree(source, project)
    if figure_map is not None:
        inject_figures(copied_source, source, figure_map.resolve())

    # The existing website configuration is retained. Passing one explicit QMD to
    # `quarto render` limits rendering to that page even though this is a website.
    subprocess.run(["quarto", "render", str(copied_source)], cwd=project, check=True)
    rel_html = copied_source.relative_to(project).with_suffix(".html")
    rendered_path = project / "_site" / rel_html
    if not rendered_path.is_file():
        raise RuntimeError(f"Quarto did not create expected output: {rendered_path}")
    rendered = rendered_path.read_text(encoding="utf-8")
    if legacy_html is not None:
        rendered = merge_legacy_body(rendered, legacy_html.resolve())
    href = Path(os.path.relpath((project / "_site" / STYLE_NAME), rendered_path.parent)).as_posix()
    rendered = insert_style_link(rendered, href)
    script_href = Path(os.path.relpath((project / "_site" / SCRIPT_NAME), rendered_path.parent)).as_posix()
    rendered = insert_script_link(rendered, script_href)

    out_html = destination / rel_html
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(rendered, encoding="utf-8")
    # Preserve Quarto’s local libraries and the original directory-relative assets.
    site_output = project / "_site"
    library = site_output / "site_libs"
    if library.is_dir():
        shutil.copytree(library, destination / "site_libs", dirs_exist_ok=True)
    rendered_parent = site_output / rel_html.parent
    if rendered_parent.is_dir():
        for item in rendered_parent.rglob("*"):
            if not item.is_file() or item == rendered_path:
                continue
            target = destination / item.relative_to(site_output)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
    style_target = destination / STYLE_NAME
    shutil.copy2(project / STYLE_NAME, style_target)
    shutil.copy2(project / SCRIPT_NAME, destination / SCRIPT_NAME)
    # Project CSS is often linked relative to the site root and is not copied by
    # Quarto when rendering only one explicit document.
    if (project / "styles.css").is_file():
        shutil.copy2(project / "styles.css", destination / "styles.css")
    # Copy only local files actually referenced by this rendered page (theme CSS,
    # favicon, syntax assets, and images), keeping output independent of the repo.
    references = ReferenceExtractor()
    references.feed(rendered)
    for value in references.values:
        if value.startswith(("#", "data:", "//")):
            continue
        from urllib.parse import unquote, urlsplit
        parsed = urlsplit(value)
        if parsed.scheme:
            continue
        candidate = (rendered_path.parent / unquote(parsed.path)).resolve()
        if not candidate.exists():
            try:
                site_relative = candidate.relative_to(site_output.resolve())
            except ValueError:
                continue
            candidate = (project / site_relative).resolve()
        try:
            relative = candidate.relative_to(project.resolve())
        except ValueError:
            continue
        if not candidate.is_file() or candidate == rendered_path:
            continue
        if candidate.suffix.lower() == ".html":
            # Other site pages are links, not dependencies of this one-page build.
            # The publisher validates them against the published worktree instead.
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(candidate, target)
    if keep_build:
        retained = destination / ".build-project"
        shutil.copytree(project, retained, dirs_exist_ok=True)
    else:
        temp_context.cleanup()
    print(out_html)
    return out_html


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="One QMD/Markdown source page")
    parser.add_argument("--output-dir", required=True, type=Path, help="New or empty output directory")
    parser.add_argument("--legacy-html", type=Path, help="Keep the existing rendered body and results inside the Quarto site shell")
    parser.add_argument("--figure-map", type=Path, help="JSON list mapping exact text anchors to existing image files and captions")
    parser.add_argument("--base-css", type=Path, help="Optional styles.css from the current published site, to avoid changing shared styling during targeted page deployment")
    parser.add_argument("--keep-build", action="store_true", help="Retain isolated project files in output/.build-project for inspection")
    args = parser.parse_args()
    try:
        build(args.source, args.output_dir, args.legacy_html, args.figure_map, args.base_css, args.keep_build)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"build_tutorial: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
