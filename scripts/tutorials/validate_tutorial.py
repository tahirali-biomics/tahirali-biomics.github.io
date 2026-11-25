#!/usr/bin/env python3
"""Validate a rendered tutorial's shell, images, styles, and local references."""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class PageAudit(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.main_depth = 0
        self.main_found = False
        self.images = 0
        self.image_sources: list[str] = []
        self.local_refs: list[str] = []
        self.sidebar = False
        self.toc = False
        self.copy_buttons = 0
        self.code_blocks = 0
        self.style_link = False
        self.copy_script = None
        self.body_ready = False
        self.inline_script = False
        self.script_fragments: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        ident = values.get("id") or ""
        if tag == "body":
            self.body_ready = "tutorial-code-ready" in classes
        if tag == "main" and ident == "quarto-document-content":
            self.main_found = True
            self.main_depth += 1
        elif self.main_depth and tag == "main":
            self.main_depth += 1
        if self.main_depth and tag == "img":
            self.images += 1
            if values.get("src"):
                self.image_sources.append(values["src"])
        if tag == "nav" and ident == "quarto-sidebar":
            self.sidebar = True
        if tag == "nav" and ident.lower() in {"toc", "quarto-toc"}:
            self.toc = True
        if "code-copy-button" in classes or "qbio-copy-button" in classes:
            self.copy_buttons += 1
        if tag == "pre":
            self.code_blocks += 1
        if tag == "link" and values.get("id") == "tutorial-code-style":
            self.style_link = True
        if tag == "script" and values.get("id") == "tutorial-code-copy-script":
            self.copy_script = values.get("src")
        if tag == "script" and not values.get("src"):
            self.inline_script = True
            self.script_fragments.append("")
        if self.inline_script and tag == "script":
            return
        for key in ("src", "href"):
            value = values.get(key)
            if value:
                self.local_refs.append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag == "main" and self.main_depth:
            self.main_depth -= 1
        if tag == "script" and self.inline_script:
            self.inline_script = False

    def handle_data(self, data: str) -> None:
        if self.inline_script and self.script_fragments:
            self.script_fragments[-1] += data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path)
    parser.add_argument("--expected-images", type=int)
    parser.add_argument("--source-root", type=Path, help="Repository root used to resolve links to existing site pages")
    parser.add_argument("--site-root", type=Path, help="Published/site root used to resolve pages omitted from this one-page build")
    parser.add_argument("--site-page", help="Published path of this page, used with --site-root for relative links")
    args = parser.parse_args()
    page = args.html.resolve()
    try:
        text = page.read_text(encoding="utf-8")
        audit = PageAudit()
        audit.feed(text)
        problems: list[str] = []
        if not audit.sidebar:
            problems.append("Quarto sidebar nav is missing")
        if not audit.main_found:
            problems.append("Quarto document content main is missing")
        if not audit.body_ready or not audit.style_link:
            problems.append("reusable tutorial stylesheet or page scope marker is missing")
        if not audit.copy_script:
            problems.append("reusable copy-control script is not linked")
        else:
            copy_script_path = (page.parent / unquote(urlsplit(audit.copy_script).path)).resolve()
            if not copy_script_path.is_file() or "addLegacyControls" not in copy_script_path.read_text(encoding="utf-8"):
                problems.append("reusable legacy copy-control script asset is missing or incomplete")
        if audit.code_blocks == 0:
            problems.append("no code blocks found")
        if args.expected_images is not None and audit.images != args.expected_images:
            problems.append(f"expected {args.expected_images} content images, found {audit.images}")
        if not audit.copy_buttons and not audit.copy_script:
            problems.append("no copy-button control or script found")
        css = page.parent / ("styles-tutorial-code.css")
        css_candidates = [css, page.parent.parent / "styles-tutorial-code.css", page.parent.parent.parent / "styles-tutorial-code.css", page.parent.parent.parent.parent / "styles-tutorial-code.css", page.parent.parent.parent.parent.parent / "styles-tutorial-code.css"]
        css_path = next((p for p in css_candidates if p.is_file()), None)
        if css_path is None:
            problems.append("reusable tutorial CSS asset is missing")
        else:
            rules = css_path.read_text(encoding="utf-8")
            for evidence in ("#f0f2f4", "#d8dde2", "overflow-x: auto", "@media (max-width: 768px)"):
                if evidence not in rules:
                    problems.append(f"tutorial CSS lacks expected rule: {evidence}")
        for src in audit.image_sources:
            if src.startswith("data:"):
                continue
            target = (page.parent / unquote(urlsplit(src).path)).resolve()
            if not target.is_file():
                problems.append(f"content image is missing: {src}")
        source_root = args.source_root.resolve() if args.source_root else None
        site_root = args.site_root.resolve() if args.site_root else None
        site_page = Path(args.site_page) if args.site_page else None
        broken: list[str] = []
        for ref in audit.local_refs:
            split = urlsplit(ref)
            if split.scheme or ref.startswith("//") or not split.path or ref.startswith("data:"):
                continue
            target = (page.parent / unquote(split.path)).resolve()
            if target.is_file():
                continue
            if site_root is not None:
                site_target = (site_root / (site_page.parent if site_page else Path()) / unquote(split.path).lstrip("/")).resolve()
                if site_target.is_file():
                    continue
                if split.path.startswith("/") and (site_root / unquote(split.path).lstrip("/")).is_file():
                    continue
            if source_root is not None and (source_root / unquote(split.path).lstrip("/")).is_file():
                continue
            # Site absolute links may resolve against the site root rather than the page directory.
            if source_root is not None and split.path.startswith("/") and (source_root / split.path.lstrip("/")).is_file():
                continue
            # Fragment-only links and external website page targets are handled separately.
            if split.path.lower().endswith(".html"):
                broken.append(ref)
        if broken:
            problems.append("unresolved local HTML links: " + ", ".join(sorted(set(broken))))
        if problems:
            print("FAIL")
            for problem in problems:
                print(f"- {problem}")
            return 1
        print(f"PASS: {page}")
        print(f"images={audit.images}, code_blocks={audit.code_blocks}, sidebar=yes, reusable_css=yes")
        print(f"toc={'yes' if audit.toc else 'not generated'}")
        return 0
    except OSError as exc:
        print(f"validate_tutorial: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
