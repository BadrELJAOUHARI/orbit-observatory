"""Deterministic extraction. Offsets address normalized Unicode code points."""

import re
import unicodedata
from html.parser import HTMLParser

NORMALIZATION_VERSION = "orbit-text-v1"


def normalize(text):
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    paragraphs = []
    for line in text.split("\n"):
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            paragraphs.append(line)
    return "\n".join(paragraphs)


class PageText(HTMLParser):
    """Exclude active content and navigation; optionally require main/article."""

    SKIP = {"script", "style", "nav", "footer", "header", "noscript", "template", "head"}
    BLOCK = {"p", "div", "section", "article", "main", "br", "li", "h1", "h2", "h3", "tr"}
    VOID = {"br", "hr", "img", "meta", "link", "input", "source", "wbr", "area", "base", "embed", "param", "col", "track"}

    def __init__(self, root=None):
        super().__init__(convert_charrefs=True)
        self.root = root
        self.stack = []
        self.parts = []
        self.links = []
        self.canonical = None
        self.root_seen = root is None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            self.links.append((attrs["href"], attrs.get("hreflang", ""), attrs.get("title", "")))
        if tag == "link" and "canonical" in attrs.get("rel", "").split():
            self.canonical = attrs.get("href")
        if tag not in self.VOID:
            self.stack.append(tag)
        if tag == self.root:
            self.root_seen = True
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in self.stack:
            index = len(self.stack) - 1 - self.stack[::-1].index(tag)
            self.stack = self.stack[:index]
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, text):
        if not self.SKIP.intersection(self.stack) and (self.root is None or self.root in self.stack):
            self.parts.append(text)


def html_text(raw, extraction):
    # The encoding is explicit in the manifest, rather than silently replacing bytes.
    parser = PageText(extraction.get("root"))
    parser.feed(raw.decode(extraction.get("encoding", "utf-8"), errors="strict"))
    if not parser.root_seen:
        raise ValueError("Required HTML content root absent")
    text = normalize("".join(parser.parts))
    start = extraction.get("start_marker")
    end = extraction.get("end_marker")
    if start:
        pos = text.find(start)
        if pos < 0:
            raise ValueError("Transcript start marker absent")
        text = text[pos:]
    if end:
        pos = text.find(end)
        if pos < 0:
            raise ValueError("Transcript end marker absent")
        text = text[:pos]
    return text.strip(), parser


def candidate_spans(text, keywords):
    """Legacy v1 physical-line candidates, not semantic PDF paragraphs/claims.

    Preserve this frozen behavior for existing IDs. Boundary review and future
    sentence segmentation belong to separate versioned artifacts, not a reflow
    of the source text or an in-place replacement of annotated candidates.
    """
    start = 0
    for paragraph in text.split("\n"):
        end = start + len(paragraph)
        if any(word.casefold() in paragraph.casefold() for word in keywords):
            yield start, end, text[start:end]
        start = end + 1
