#!/usr/bin/env python3
"""Copy selected rendered pages and their local dependencies into a clean gh-pages worktree."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit


class LocalReferences(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key in {"src", "href"} and value:
                parts = urlsplit(value)
                if not parts.scheme and not value.startswith("//") and parts.path:
                    self.references.append(unquote(parts.path))


def git(path: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(path), *args], check=True, text=True, capture_output=True)
    return result.stdout.strip()


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", required=True, action="append", type=Path, help="Rendered output directory; repeat for multiple selected pages")
    parser.add_argument("--worktree", required=True, type=Path, help="Existing clean worktree based on origin/gh-pages")
    parser.add_argument("--page", action="append", required=True, help="Rendered HTML path relative to build-dir; repeat for approved pages")
    args = parser.parse_args()
    builds = [path.resolve() for path in args.build_dir]
    worktree = args.worktree.resolve()
    try:
        if not all(path.is_dir() for path in builds) or not worktree.is_dir():
            raise ValueError("All build directories and the publishing worktree must already exist")
        if git(worktree, "status", "--porcelain"):
            raise ValueError("Publishing worktree is dirty; inspect it manually and use a fresh clean gh-pages worktree")
        branch = git(worktree, "branch", "--show-current")
        if branch:
            raise ValueError(f"Publishing worktree must be detached to avoid moving an existing branch (found {branch})")
        if git(worktree, "rev-parse", "--abbrev-ref", "HEAD") != "HEAD":
            raise ValueError("Publishing worktree is not detached")
        if git(worktree, "rev-parse", "HEAD") != git(worktree, "rev-parse", "origin/gh-pages"):
            raise ValueError("Publishing worktree is not based on the latest fetched origin/gh-pages; fetch and create a fresh worktree")

        staged: set[str] = set()
        selected_pages: set[str] = set()
        selected_sources: list[tuple[PurePosixPath, Path]] = []
        for raw in args.page:
            rel = PurePosixPath(raw)
            if rel.is_absolute() or ".." in rel.parts or rel.suffix.lower() != ".html":
                raise ValueError(f"Page must be a repository-relative HTML path: {raw}")
            candidates = [root.joinpath(*rel.parts) for root in builds]
            matches = [candidate for root, candidate in zip(builds, candidates) if candidate.is_file() and inside(root, candidate)]
            if len(matches) != 1:
                raise ValueError(f"Expected exactly one matching rendered page among build directories: {raw}")
            source = matches[0]
            if not source.is_file():
                raise ValueError(f"Rendered page not found inside build directory: {raw}")
            selected_pages.add(rel.as_posix())
            selected_sources.append((rel, source))

        for rel, source in selected_sources:
            build = next(root for root in builds if inside(root, source))
            refs = LocalReferences()
            refs.feed(source.read_text(encoding="utf-8"))
            files = {rel.as_posix(): source}
            for value in refs.references:
                candidate = PurePosixPath(value)
                if candidate.is_absolute() or ".." in candidate.parts:
                    # Relative references may climb from a nested HTML directory; resolve below.
                    target = (source.parent / value).resolve()
                    if not inside(build, target):
                        continue
                else:
                    target = source.parent.joinpath(*candidate.parts).resolve()
                if target == source.resolve() or not inside(build, target):
                    continue
                target_rel = target.relative_to(build).as_posix()
                if target.suffix.lower() == ".html" and target_rel not in selected_pages:
                    if not (worktree / target_rel).is_file():
                        raise ValueError(f"Linked site page is not present on gh-pages: {target_rel}")
                    continue
                if target.is_file():
                    files[target_rel] = target
            for target_rel, origin in files.items():
                destination = worktree / target_rel
                if target_rel not in selected_pages and destination.exists() and sha(destination) != sha(origin):
                    raise ValueError(f"Referenced existing asset differs on gh-pages; refusing to overwrite shared file: {target_rel}")
                destination.parent.mkdir(parents=True, exist_ok=True)
                if target_rel in selected_pages or not destination.exists():
                    shutil.copy2(origin, destination)
                staged.add(target_rel)

        # Stage exact, validated paths only. Do not commit or push automatically.
        subprocess.run(["git", "-C", str(worktree), "add", "--", *sorted(staged)], check=True)
        print(git(worktree, "diff", "--cached", "--stat"))
        print("\nStaged paths:")
        print(git(worktree, "diff", "--cached", "--name-only"))
        print(f"\nReview in {worktree}; this command does not commit or push.")
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", None) or str(exc)
        print(f"publish_tutorials: {detail}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
