"""ST-008 regression contracts for first-party rendering of user-generated content."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_kassa_detail_renders_post_body_as_text():
    html = _read("kassa-post.html")
    assert "body.textContent = p.body;" in html


def test_kassa_thread_renders_message_body_as_text():
    html = _read("kassa-thread.html")
    assert "bubble.textContent = msg.text || '';" in html


def test_forums_render_thread_and_reply_bodies_as_text():
    html = _read("forums.html")
    assert "fullBody.textContent = t.body || '(no content)';" in html
    assert "reBody.textContent = r.body || '';" in html


def test_kassa_board_keeps_explicit_html_escape_function():
    html = _read("kassa.html")
    assert "function esc(s)" in html
    assert "esc(p.title" in html
    assert "esc(p.body" in html
