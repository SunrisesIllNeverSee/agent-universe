"""FAQPage JSON-LD must render only on the dedicated /faq page; snippet length guards."""
import json
import re
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[1] / "frontend"
LD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


def _types(node):
    if isinstance(node, dict):
        t = node.get("@type")
        yield from ([t] if isinstance(t, str) else (t or []))
        for v in node.values():
            yield from _types(v)
    elif isinstance(node, list):
        for v in node:
            yield from _types(v)


def _pages_with_faqpage():
    out = []
    for p in sorted(FRONTEND.rglob("*.html")):
        for block in LD.findall(p.read_text(encoding="utf-8")):
            try:
                data = json.loads(block)
            except ValueError:
                continue
            if "FAQPage" in _types(data):
                out.append(p.relative_to(FRONTEND).as_posix())
    return out


def test_faqpage_jsonld_only_on_faq_page():
    assert _pages_with_faqpage() == ["faq.html"]


def _meta(name):
    s = (FRONTEND / "alternatives" / f"{name}.html").read_text(encoding="utf-8")
    title = re.search(r"<title>(.*?)</title>", s, re.S).group(1).strip()
    desc = re.search(r'<meta name="description" content="([^"]*)"', s).group(1)
    return title, desc


def test_alternatives_snippet_lengths():
    for name in ("agent-ai", "ai-agent-marketplaces"):
        title, desc = _meta(name)
        assert 30 <= len(title) <= 60, (name, len(title))
        assert len(desc) <= 155, (name, len(desc))
