"""FAQPage JSON-LD must render only on the dedicated /faq page; snippet length guards."""
import json
import re
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[1] / "frontend"
LD = re.compile(r"<script\b[^>]*\btype\s*=\s*[\"']?application/ld\+json[\"']?[^>]*>(.*?)</script>", re.S | re.I)


def _types(node):
    if isinstance(node, dict):
        t = node.get("@type")
        yield from ([t] if isinstance(t, str) else (t or []))
        for v in node.values():
            yield from _types(v)
    elif isinstance(node, list):
        for v in node:
            yield from _types(v)


def _has_faqpage(html):
    for block in LD.findall(html):
        try:
            data = json.loads(block)
        except ValueError:
            # unparseable block: fall back to substring check
            if '"FAQPage"' in block:
                return True
            continue
        if "FAQPage" in _types(data):
            return True
    return False


def _pages():
    return sorted(FRONTEND.rglob("*.html"))


def test_no_faqpage_jsonld_outside_faq_page():
    bad = [
        p.relative_to(FRONTEND).as_posix()
        for p in _pages()
        if p.name != "faq.html" or p.parent != FRONTEND
        if _has_faqpage(p.read_text(encoding="utf-8"))
    ]
    assert bad == []


def test_faq_page_has_faqpage_jsonld():
    assert _has_faqpage((FRONTEND / "faq.html").read_text(encoding="utf-8"))


SNIPPET_PAGES = [
    "alternatives/agent-ai.html",
    "alternatives/ai-agent-marketplaces.html",
    "agents.html",
    "blog/index.html",
    "guides/index.html",
    "meetings.html",
]


def test_snippet_lengths():
    for name in SNIPPET_PAGES:
        s = (FRONTEND / name).read_text(encoding="utf-8")
        title = re.search(r"<title>(.*?)</title>", s, re.S).group(1).strip()
        desc = re.search(r'<meta name="description" content="([^"]*)"', s).group(1)
        assert 30 <= len(title) <= 60, (name, len(title))
        assert len(desc) <= 155, (name, len(desc))
