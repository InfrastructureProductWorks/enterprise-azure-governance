#!/usr/bin/env python3
"""Validate links referenced by a repository root README.

The checker is intentionally dependency-free so it can run in GitHub Actions
without installing third-party packages. It validates:

* same-document GitHub-style heading anchors;
* repository-relative files and images using the runner's case-sensitive FS;
* external HTTP(S) links, treating clear client-side dead links as failures.

Transient server/rate-limit responses (403, 429, and 5xx) are reported as
warnings rather than declaring a link broken.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
import time
import unicodedata
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen

MARKDOWN_TARGET_RE = re.compile(r"\]\(([^)]+)\)")
HTML_TARGET_RE = re.compile(r"\b(?:href|src)\s*=\s*([\"'])(.*?)\1", re.IGNORECASE)
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")

SKIP_SCHEMES = {"mailto", "tel", "javascript", "data"}
TRANSIENT_HTTP = {403, 429}
HARD_HTTP = {400, 404, 410, 451}
VARIATION_SELECTORS = {"\ufe0e", "\ufe0f"}


def strip_fenced_code(text: str) -> str:
    lines: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        match = FENCE_RE.match(line)
        if match:
            marker = match.group(1)
            if fence is None:
                fence = marker
            elif marker == fence:
                fence = None
            continue
        if fence is None:
            lines.append(line)
    return "\n".join(lines)


def clean_heading_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"[*_~`]", "", value)
    return html.unescape(value)


def github_slug(value: str) -> str:
    """Approximate GitHub's heading slug rules for README-local anchors."""
    value = clean_heading_text(value).lower()
    kept: list[str] = []
    for char in value:
        if char in VARIATION_SELECTORS:
            continue
        category = unicodedata.category(char)
        if char in "-_" or char.isspace() or category[0] in {"L", "N", "M"}:
            kept.append(char)
    return "".join("-" if char.isspace() else char for char in kept)


def heading_anchors(text: str) -> set[str]:
    anchors: set[str] = set()
    occurrences: dict[str, int] = {}
    for line in strip_fenced_code(text).splitlines():
        match = HEADING_RE.match(line)
        if not match:
            continue
        base = github_slug(match.group(1))
        count = occurrences.get(base, 0)
        anchor = base if count == 0 else f"{base}-{count}"
        occurrences[base] = count + 1
        anchors.add(anchor)
    return anchors


def normalize_target(raw: str) -> str:
    target = html.unescape(raw.strip())
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1].strip()
    # Markdown permits an optional quoted title after the destination.
    if " " in target and not target.startswith(("http://", "https://")):
        target = target.split(None, 1)[0]
    return target.strip()


def extract_targets(text: str) -> list[str]:
    visible = strip_fenced_code(text)
    targets = [normalize_target(match.group(1)) for match in MARKDOWN_TARGET_RE.finditer(visible)]
    targets.extend(normalize_target(match.group(2)) for match in HTML_TARGET_RE.finditer(visible))
    # Preserve first-seen order while de-duplicating repeated support links/badges.
    return list(dict.fromkeys(target for target in targets if target))


def local_path_for(readme: Path, target: str) -> Path:
    parsed = urlsplit(target)
    raw_path = unquote(parsed.path)
    if raw_path.startswith("/"):
        return readme.parent / raw_path.lstrip("/")
    return readme.parent / raw_path


def check_external(url: str, attempts: int = 3, timeout: int = 15) -> tuple[str, str]:
    last_error = "unknown error"
    for attempt in range(1, attempts + 1):
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; InfrastructureProductWorks-README-Link-Check/1.0)",
                "Accept": "*/*",
                "Range": "bytes=0-0",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                status = getattr(response, "status", 200)
                if 200 <= status < 400:
                    return "ok", f"HTTP {status}"
                if status in TRANSIENT_HTTP or status >= 500:
                    return "warn", f"transient HTTP {status}"
                return "fail", f"HTTP {status}"
        except HTTPError as exc:
            if exc.code in HARD_HTTP:
                return "fail", f"HTTP {exc.code}"
            if exc.code in TRANSIENT_HTTP or exc.code >= 500:
                return "warn", f"transient HTTP {exc.code}"
            last_error = f"HTTP {exc.code}"
        except URLError as exc:
            last_error = str(exc.reason)
        except TimeoutError:
            last_error = "timeout"

        if attempt < attempts:
            time.sleep(attempt)

    return "fail", last_error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("readme", nargs="?", default="README.md")
    parser.add_argument("--skip-external", action="store_true")
    args = parser.parse_args()

    readme = Path(args.readme).resolve()
    if not readme.is_file():
        print(f"FAIL: README not found: {readme}")
        return 1

    text = readme.read_text(encoding="utf-8")
    anchors = heading_anchors(text)
    targets = extract_targets(text)

    failures: list[str] = []
    warnings: list[str] = []
    checked = 0

    for target in targets:
        parsed = urlsplit(target)
        scheme = parsed.scheme.lower()

        if scheme in SKIP_SCHEMES:
            continue

        if scheme in {"http", "https"}:
            if args.skip_external:
                continue
            checked += 1
            state, detail = check_external(target)
            if state == "fail":
                failures.append(f"{target} ({detail})")
            elif state == "warn":
                warnings.append(f"{target} ({detail})")
            else:
                print(f"OK external: {target} [{detail}]")
            continue

        if scheme:
            warnings.append(f"{target} (unsupported scheme '{scheme}', not validated)")
            continue

        if not parsed.path and parsed.fragment:
            checked += 1
            fragment = unquote(parsed.fragment)
            if fragment not in anchors:
                failures.append(f"{target} (README anchor not found)")
            else:
                print(f"OK anchor: {target}")
            continue

        if parsed.path:
            checked += 1
            local = local_path_for(readme, target)
            if not local.exists():
                failures.append(f"{target} (repository path not found: {local.relative_to(readme.parent)})")
            else:
                print(f"OK local: {target}")

    for warning in warnings:
        print(f"WARN: {warning}")

    if failures:
        print("\nBroken README links:")
        for failure in failures:
            print(f"  - {failure}")
        print(f"\nFAIL: {len(failures)} broken link(s); {checked} target(s) checked.")
        return 1

    print(f"\nPASS: {checked} README target(s) checked; {len(warnings)} transient/unsupported warning(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
