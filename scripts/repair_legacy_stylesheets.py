"""Keep archived HTML pages linked to the stylesheets in this Quarto build.

Quarto copies these older HTML files as resources, but regenerates the hashed
Bootstrap filename whenever the site theme changes. Run after every render so
their sidebars and tables of contents retain the Quarto grid layout.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"
LINK = re.compile(r"<link\b[^>]*>", re.IGNORECASE)
HREF = re.compile(r"(\bhref\s*=\s*)([\"'])([^\"']+)\2", re.IGNORECASE)
ASSETS = {
    "bootstrap": re.compile(r"(?:^|/)bootstrap/bootstrap-[0-9a-f]+\.min\.css$"),
    "syntax": re.compile(r"(?:^|/)quarto-html/quarto-syntax-highlighting-[0-9a-f]+\.css$"),
}


def asset_kind(href: str) -> str | None:
    path = unquote(urlsplit(href).path)
    return next((kind for kind, pattern in ASSETS.items() if pattern.search(path)), None)


def current_assets() -> dict[str, Path]:
    home = SITE / "index.html"
    if not home.is_file():
        raise RuntimeError("Rendered home page missing; run a full `quarto render` first")
    assets: dict[str, Path] = {}
    for tag in LINK.findall(home.read_text(encoding="utf-8")):
        match = HREF.search(tag)
        if not match:
            continue
        kind = asset_kind(match.group(3))
        if kind:
            asset = (SITE / unquote(urlsplit(match.group(3)).path)).resolve()
            if not asset.is_file() or not asset.is_relative_to(SITE.resolve()):
                raise RuntimeError(f"Rendered {kind} stylesheet missing: {asset}")
            assets[kind] = asset
    if set(assets) != set(ASSETS):
        raise RuntimeError("Home page lacks the rendered Bootstrap or syntax stylesheet")
    return assets


def repair_page(page: Path, assets: dict[str, Path]) -> bool:
    original = page.read_text(encoding="utf-8")
    found: set[str] = set()

    def replace_link(link: re.Match[str]) -> str:
        tag = link.group()
        match = HREF.search(tag)
        if not match:
            return tag
        kind = asset_kind(match.group(3))
        if kind is None:
            return tag
        found.add(kind)
        href = Path(os.path.relpath(assets[kind], page.parent)).as_posix()
        return tag[: match.start(3)] + href + tag[match.end(3) :]

    updated = LINK.sub(replace_link, original)
    if updated != original:
        page.write_text(updated, encoding="utf-8")
    for kind in found:
        href = Path(os.path.relpath(assets[kind], page.parent))
        if not (page.parent / href).is_file():
            raise RuntimeError(f"Missing {kind} stylesheet for {page}")
    return updated != original


def main() -> None:
    assets = current_assets()
    pages = sorted(
        SITE / source.relative_to(ROOT)
        for folder in (ROOT / "teaching", ROOT / "workshops")
        for source in folder.rglob("*.html")
    )
    missing = [page for page in pages if not page.is_file()]
    if missing:
        raise RuntimeError(f"Archived HTML not copied to site: {missing[0]}")
    changed = sum(repair_page(page, assets) for page in pages)
    print(f"Checked {len(pages)} archived pages; updated stylesheet links in {changed}")


if __name__ == "__main__":
    main()
