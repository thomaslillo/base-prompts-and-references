#!/usr/bin/env python3
"""Check the markup, slide budget and code sidebars of an explain-diff-html deck.

Usage: python3 check_deck.py <deck.html>

Run it from the repository the deck explains, so it can confirm that every file
path in the deck exists. FAIL marks broken markup. WARN marks a budget or style
problem to fix unless the content justifies it. The checker does not assess the
story, technical accuracy or quiz answers.
"""

import json
import re
import subprocess
import sys
from html.parser import HTMLParser

__all__ = ["check"]

_FAIL: list[str] = []
_WARN: list[str] = []

HEADLINE_WORDS = 14
PROSE_WORDS = 110
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
SKIP_TEXT_TAGS = {"pre", "svg", "table", "details", "script", "style", "h1", "h2"}
SKIP_TEXT_CLASSES = {"eyebrow", "transition", "gallery-note", "legend", "flow", "page"}
VISUAL_CLASSES = {"flow", "grid", "tablewrap", "page", "codeview", "svgwrap"}
FLAIR = re.compile(
    r"\b(for the first time|game[- ]chang\w*|seamless\w*|robust|crucial|leverag\w*|powerful|elegant\w*|"
    r"under the hood|the magic|main event|key insight|here's the catch|ensur\w*)\b",
    re.I,
)
PASSIVE = re.compile(r"\b(is|are|was|were|been|being)\s+[a-z]+ed\b", re.I)
FIRST_PERSON = re.compile(r"\b(I|we|our|us)\b")


def _fail(message: str) -> None:
    _FAIL.append(message)


def _warn(message: str) -> None:
    _WARN.append(message)


class _Slide:
    """What the checker records about one slide."""

    def __init__(self, number: int) -> None:
        self.number = number
        self.headline: list[str] = []
        self.prose: list[str] = []
        self.visuals = 0
        self.callouts = 0
        self.code_blocks = 0
        self.contexts = 0
        self.has_tree = False
        self.paths: list[str] = []
        self.hits: list[str] = []


class _DeckScanner(HTMLParser):
    """Walk the deck once and collect per-slide facts."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.slides: list[_Slide] = []
        self._stack: list[tuple[str, set[str], bool, bool]] = []
        self._in_path = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = set((dict(attrs).get("class") or "").split())
        if tag == "section" and "slide" in classes:
            self.slides.append(_Slide(len(self.slides) + 1))
        slide = self.slides[-1] if self.slides and self._inside("section") else None
        in_visual = any(visual for _, _, _, visual in self._stack)
        is_visual = tag == "svg" or bool(classes & VISUAL_CLASSES) or (tag in {"table", "pre"} and not in_visual)
        if slide is not None:
            self._record(slide, tag, classes, dict(attrs), counts_as_visual=is_visual and not in_visual)
        if tag == "span" and "path" in classes:
            self._in_path = True
        if tag in VOID_TAGS:
            return
        skip = tag in SKIP_TEXT_TAGS or bool(classes & SKIP_TEXT_CLASSES)
        self._stack.append((tag, classes, skip, is_visual))

    def handle_endtag(self, tag: str) -> None:
        if tag == "span":
            self._in_path = False
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index][0] == tag:
                del self._stack[index:]
                return

    def handle_data(self, data: str) -> None:
        if not self.slides or not self._inside("section"):
            return
        slide = self.slides[-1]
        if self._in_path:
            slide.paths.append(data.strip())
        if self._inside("h1") or self._inside("h2"):
            slide.headline.append(data)
        if not any(skip for _, _, skip, _ in self._stack):
            slide.prose.append(data)

    def _inside(self, tag: str) -> bool:
        return any(open_tag == tag for open_tag, _, _, _ in self._stack)

    def _record(self, slide: _Slide, tag: str, classes: set[str], attrs: dict, *, counts_as_visual: bool) -> None:
        if counts_as_visual:
            slide.visuals += 1
        if "callout" in classes:
            slide.callouts += 1
        if tag == "pre" and "sample" not in classes:
            slide.code_blocks += 1
        if "code-context" in classes:
            slide.contexts += 1
        if tag == "details" and "tree" in classes:
            slide.has_tree = True
        if tag == "li" and "hit" in classes:
            slide.hits.append(attrs.get("data-path") or "")


def _check_chrome(html: str) -> None:
    """Check the navigation controls the shell provides."""
    for needle, label in (
        ('id="prev"', "Previous button"),
        ('id="next"', "Next button"),
        ("ArrowRight", "keyboard navigation"),
        ('id="prog"', "progress bar"),
        ('id="count"', "slide counter"),
    ):
        if needle not in html:
            _fail(f"missing {label} ({needle}); copy the shell from gallery.html")


def _check_quiz(html: str) -> None:
    """Check for five questions with four options, one answer and an explanation each."""
    match = re.search(r'<script type="application/json" id="quiz-data">(.*?)</script>', html, re.S)
    if match is None:
        _fail('missing <script type="application/json" id="quiz-data">')
        return
    try:
        questions = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        _fail(f"quiz-data is not valid JSON: {exc}")
        return
    if len(questions) != 5:
        _fail(f"{len(questions)} quiz questions, expected 5")
    for number, item in enumerate(questions, 1):
        if len(item.get("o", [])) != 4:
            _fail(f"quiz {number}: {len(item.get('o', []))} options, expected 4")
        if item.get("a") not in range(4):
            _fail(f"quiz {number}: answer index {item.get('a')!r} is not 0 to 3")
        if not str(item.get("e", "")).strip():
            _fail(f"quiz {number}: missing explanation")


def _check_code_markup(html: str) -> None:
    """Reject code containers that collapse newlines or carry inline styles."""
    for tag in re.findall(r"<pre[^>]*>", html):
        if tag not in ("<pre>", '<pre class="sample">'):
            _fail(f'{tag}: use <pre> or <pre class="sample"> and style it from CSS')
    if "white-space: pre" not in html and "white-space:pre" not in html:
        _fail("no white-space: pre rule for <pre>")
    if re.search(r"<pre[^>]*>\n", html):
        _warn("a newline directly after <pre> renders as a blank line")


def _check_svg_refs(html: str) -> None:
    """Check that markers are shared, unique and defined."""
    for marker_id in set(re.findall(r'<marker id="([^"]+)"', html)):
        if html.count(f'id="{marker_id}"') > 1:
            _fail(f'duplicate marker id="{marker_id}"')
        if '<section class="slide' in html[: html.index(f'<marker id="{marker_id}"')]:
            _fail(f'marker "{marker_id}" is inside a slide; move it to the shared defs at the top of <body>')
    for ref in set(re.findall(r"url\(#([^)]+)\)", html)):
        if f'id="{ref}"' not in html:
            _fail(f"url(#{ref}) has no matching definition")
    for tag in re.findall(r"<(?:rect|path|line|circle|text|polygon)\b[^>]*>", html):
        if re.search(r'(?:fill|stroke)="#', tag):
            _warn(f"hex color in SVG markup; use the .sv-* classes: {tag[:70]}")


def _check_prose(html: str) -> None:
    """Flag punctuation and wording the style guide rules out."""
    dashes = html.count("&mdash;") + html.count("\u2014") + html.count("&ndash;") + html.count("\u2013")
    if dashes:
        _fail(f"{dashes} em or en dashes; use periods or commas")
    curly = len(re.findall("[\u2018\u2019\u201c\u201d]", html))
    if curly:
        _fail(f"{curly} curly quotes; use straight quotes")
    if re.search(r"^\s*[|+][-=+|]{4,}", html, re.M):
        _fail("ASCII diagram detected; use HTML, CSS or SVG")


def _check_slide(slide: _Slide, known_paths: set[str] | None) -> None:
    """Check one slide against the budget and the code-sidebar rules."""
    label = f"slide {slide.number}"
    headline = " ".join("".join(slide.headline).split())
    prose = " ".join("".join(slide.prose).split())
    if len(headline.split()) > HEADLINE_WORDS:
        _warn(f"{label}: headline has {len(headline.split())} words; aim for about 12")
    if slide.visuals > 1:
        _warn(f"{label}: {slide.visuals} visuals; give each visual its own slide")
    if slide.callouts > 1:
        _warn(f"{label}: {slide.callouts} callouts; keep at most one")
    if len(prose.split()) > PROSE_WORDS:
        _warn(f"{label}: {len(prose.split())} words of prose; aim for about 80")
    for pattern, problem in ((FLAIR, "flair"), (PASSIVE, "possible passive voice"), (FIRST_PERSON, "first person")):
        for hit in sorted({m.group(0) for m in pattern.finditer(prose)}):
            _warn(f'{label}: {problem}: "{hit}"')
    _check_code(slide, label, known_paths)


def _check_code(slide: _Slide, label: str, known_paths: set[str] | None) -> None:
    """Check that each code block has context, a full path and a sidebar entry."""
    if not slide.code_blocks:
        return
    if slide.code_blocks > 2:
        _warn(f"{label}: {slide.code_blocks} code blocks; keep at most two that are read together")
    if not slide.has_tree:
        _fail(f'{label}: code without a <details class="tree"> directory sidebar')
    if not slide.contexts:
        _fail(f'{label}: code without a <p class="code-context"> sentence')
    if len(slide.paths) < slide.code_blocks:
        _fail(f'{label}: {slide.code_blocks} code blocks but {len(slide.paths)} <span class="path"> labels')
    for path in slide.paths:
        if path not in slide.hits:
            _fail(f'{label}: {path} has no <li class="hit" data-path="{path}"> in the sidebar')
        if known_paths is not None and path not in known_paths:
            _fail(f"{label}: {path} is not a file in this repository; use the full path from the repository root")


def _repo_paths() -> set[str] | None:
    """Return committed, staged and new unignored files, or None outside a git repository."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return set(result.stdout.splitlines())


def check(html: str, known_paths: set[str] | None = None) -> None:
    """Run all checks against a deck's markup."""
    scanner = _DeckScanner()
    scanner.feed(html)
    if not scanner.slides:
        _fail("no slides found")
    _check_chrome(html)
    _check_quiz(html)
    _check_code_markup(html)
    _check_svg_refs(html)
    _check_prose(html)
    for slide in scanner.slides:
        _check_slide(slide, known_paths)


def main() -> int:
    """Check the named deck and report every issue found."""
    if len(sys.argv) != 2:
        print("usage: check_deck.py <deck.html>")
        return 2
    check(open(sys.argv[1], encoding="utf-8").read(), _repo_paths())
    for warning in _WARN:
        print(f"WARN  {warning}")
    for failure in _FAIL:
        print(f"FAIL  {failure}")
    if _FAIL:
        print(f"\n{len(_FAIL)} failure(s).")
        return 1
    print(f"\nPASS ({len(_WARN)} warning(s)). Review the rendered deck for story and accuracy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
