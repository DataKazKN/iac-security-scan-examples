#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HTTP_PREFIXES = ("http://", "https://")


def extract_markdown_links(markdown: str) -> tuple[str, ...]:
    return tuple(match.group(1).strip() for match in LINK_PATTERN.finditer(markdown))


def markdown_files(root: Path) -> tuple[Path, ...]:
    return tuple(
        path
        for path in sorted(root.rglob("*.md"))
        if ".git" not in path.parts
    )


def validate_local_targets(root: Path) -> tuple[str, ...]:
    failures: list[str] = []
    for document in markdown_files(root):
        for raw_target in extract_markdown_links(
            document.read_text(encoding="utf-8")
        ):
            target = raw_target.split("#", 1)[0]
            if not target or target.startswith((*HTTP_PREFIXES, "mailto:")):
                continue
            if not (document.parent / target).resolve().exists():
                failures.append(f"{document.relative_to(root)} -> {raw_target}")
    return tuple(failures)


def public_urls(root: Path) -> tuple[str, ...]:
    urls = {
        target
        for document in markdown_files(root)
        for target in extract_markdown_links(document.read_text(encoding="utf-8"))
        if target.startswith(HTTP_PREFIXES)
    }
    return tuple(sorted(urls))


def check_http_url(url: str) -> str | None:
    headers = {"User-Agent": "iac-security-scan-examples-link-check/1.0"}
    for method in ("HEAD", "GET"):
        request = Request(url, method=method, headers=headers)
        try:
            with urlopen(request, timeout=30) as response:
                if 200 <= response.status < 400:
                    return None
                return f"{url} -> HTTP {response.status}"
        except HTTPError as error:
            if method == "HEAD" and error.code in {403, 405}:
                continue
            return f"{url} -> HTTP {error.code}"
        except (TimeoutError, URLError) as error:
            if method == "HEAD":
                continue
            return f"{url} -> {error}"
    return f"{url} -> no successful response"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Markdown links.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--local-only", action="store_true")
    mode.add_argument("--http", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    local_failures = validate_local_targets(root)
    for failure in local_failures:
        print(f"FAIL {failure}", file=sys.stderr)
    if local_failures:
        return 1

    print(f"PASS local links ({len(markdown_files(root))} Markdown files)")
    if args.local_only:
        return 0

    urls = public_urls(root)
    failures = tuple(filter(None, (check_http_url(url) for url in urls)))
    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    if failures:
        return 1

    print(f"PASS public links ({len(urls)} unique URLs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
