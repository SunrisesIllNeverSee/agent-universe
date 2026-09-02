from __future__ import annotations

import json
import sqlite3
from collections import Counter
from dataclasses import dataclass
from typing import Any


@dataclass
class ThreadProfile:
    thread_id: str
    record_count: int
    turn_count: int
    item_count: int
    document_count: int
    categories: dict[str, int]
    authorities: dict[str, int]
    statuses: dict[str, int]
    tags: list[str]
    manual_tags: list[str]
    parser_tags: list[str]
    decisions: list[dict[str, str]]
    open_actions: list[dict[str, str]]
    canon_updates: list[dict[str, str]]

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _counter(conn: sqlite3.Connection, thread_id: str, column: str) -> dict[str, int]:
    rows = conn.execute(
        f"SELECT {column}, COUNT(*) n FROM records WHERE thread_id=? AND COALESCE({column},'')<>'' GROUP BY {column}",
        (thread_id,),
    ).fetchall()
    return {str(row[0]): int(row[1]) for row in rows}


def _selected_items(conn: sqlite3.Connection, thread_id: str, category: str, status: str | None = None) -> list[dict[str, str]]:
    sql = "SELECT record_key,target_id,title,content,authority,status FROM records WHERE thread_id=? AND record_type='item' AND category=?"
    params: list[Any] = [thread_id, category]
    if status:
        sql += " AND status=?"
        params.append(status)
    sql += " ORDER BY record_key"
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def _tags_by_source(conn: sqlite3.Connection, thread_id: str) -> tuple[list[str], list[str], list[str]]:
    rows = conn.execute(
        """SELECT DISTINCT t.tag,t.source FROM tags t JOIN records r ON r.record_key=t.record_key
           WHERE r.thread_id=? ORDER BY t.tag,t.source""",
        (thread_id,),
    ).fetchall()
    all_tags = sorted({str(row[0]) for row in rows if row[0]})
    manual = sorted({str(row[0]) for row in rows if row[0] and str(row[1]) == "manual"})
    parser = sorted({str(row[0]) for row in rows if row[0] and str(row[1]) != "manual"})
    return all_tags, manual, parser


def profile_thread(conn: sqlite3.Connection, thread_id: str) -> ThreadProfile:
    total = conn.execute("SELECT COUNT(*) FROM records WHERE thread_id=?", (thread_id,)).fetchone()[0]
    by_type = {
        row[0]: row[1]
        for row in conn.execute(
            "SELECT record_type,COUNT(*) FROM records WHERE thread_id=? GROUP BY record_type", (thread_id,)
        ).fetchall()
    }
    tags, manual_tags, parser_tags = _tags_by_source(conn, thread_id)
    open_actions = [
        dict(row)
        for row in conn.execute(
            """SELECT record_key,target_id,title,content,authority,status FROM records
               WHERE thread_id=? AND record_type='item' AND category='ACTION'
                 AND status IN ('OPEN','PROPOSED','CHALLENGED') ORDER BY record_key""",
            (thread_id,),
        ).fetchall()
    ]
    decisions = _selected_items(conn, thread_id, "DECISION")
    canon_updates = _selected_items(conn, thread_id, "CANON_UPDATE")
    return ThreadProfile(
        thread_id=thread_id,
        record_count=int(total),
        turn_count=int(by_type.get("turn", 0)),
        item_count=int(by_type.get("item", 0)),
        document_count=int(by_type.get("document", 0)),
        categories=_counter(conn, thread_id, "category"),
        authorities=_counter(conn, thread_id, "authority"),
        statuses=_counter(conn, thread_id, "status"),
        tags=tags,
        manual_tags=manual_tags,
        parser_tags=parser_tags,
        decisions=decisions,
        open_actions=open_actions,
        canon_updates=canon_updates,
    )


def _common_and_unique(tag_sets: dict[str, set[str]]) -> tuple[list[str], dict[str, list[str]]]:
    common = sorted(set.intersection(*(tags for tags in tag_sets.values()))) if tag_sets else []
    unique = {
        thread_id: sorted(tags - set().union(*(other for other_id, other in tag_sets.items() if other_id != thread_id)))
        for thread_id, tags in tag_sets.items()
    }
    return common, unique


def compare_threads(conn: sqlite3.Connection, thread_ids: list[str]) -> dict[str, Any]:
    ids = list(dict.fromkeys(thread_ids))
    if len(ids) < 2:
        raise ValueError("Multi-thread comparison requires at least two unique thread ids")
    profiles = [profile_thread(conn, thread_id) for thread_id in ids]

    category_presence: dict[str, list[str]] = {}
    all_categories = sorted({category for profile in profiles for category in profile.categories})
    for category in all_categories:
        category_presence[category] = [profile.thread_id for profile in profiles if profile.categories.get(category, 0)]

    # Human organization tags and parser-generated analytical tags are intentionally
    # separated. Project comparison defaults to manual tags; parser tags remain visible
    # as a distinct signal instead of masquerading as human organization choices.
    manual_sets = {profile.thread_id: set(profile.manual_tags) for profile in profiles}
    parser_sets = {profile.thread_id: set(profile.parser_tags) for profile in profiles}
    common_tags, unique_tags = _common_and_unique(manual_sets)
    common_parser_tags, unique_parser_tags = _common_and_unique(parser_sets)

    shared_decision_terms = Counter()
    for profile in profiles:
        seen: set[str] = set()
        for decision in profile.decisions + profile.canon_updates:
            words = {
                word.lower().strip(".,:;()[]{}")
                for word in (decision.get("content") or "").split()
                if len(word.strip(".,:;()[]{}")) >= 5
            }
            seen |= words
        shared_decision_terms.update(seen)

    return {
        "comparison_schema": "0.2.0",
        "thread_ids": ids,
        "profiles": [profile.to_dict() for profile in profiles],
        "common_tags": common_tags,
        "unique_tags": unique_tags,
        "common_parser_tags": common_parser_tags,
        "unique_parser_tags": unique_parser_tags,
        "category_presence": category_presence,
        "shared_decision_terms": [
            {"term": term, "thread_count": count}
            for term, count in shared_decision_terms.most_common(30)
            if count > 1
        ],
        "tag_semantics": {
            "common_tags": "manual organizational tags only",
            "common_parser_tags": "parser/system-generated analytical tags only",
        },
        "interpretation_policy": (
            "Comparison is descriptive over indexed parser outputs. It does not reconcile conflicting canon "
            "or promote cross-thread truth."
        ),
    }


def render_markdown(comparison: dict[str, Any]) -> str:
    lines = ["# Thread Comparison", "", "Threads: " + ", ".join(comparison["thread_ids"]), ""]
    lines.extend(["## Profiles", ""])
    for profile in comparison["profiles"]:
        lines.append(f"### {profile['thread_id']}")
        lines.append("")
        lines.append(
            f"- Turns: **{profile['turn_count']}**; items: **{profile['item_count']}**; "
            f"documents: **{profile['document_count']}**"
        )
        lines.append(f"- Decisions: **{len(profile['decisions'])}**; open actions: **{len(profile['open_actions'])}**; canon updates: **{len(profile['canon_updates'])}**")
        if profile["manual_tags"]:
            lines.append("- Manual tags: " + ", ".join(profile["manual_tags"]))
        if profile["parser_tags"]:
            lines.append("- Parser tags: " + ", ".join(profile["parser_tags"]))
        lines.append("")
    lines.extend(["## Cross-thread signals", ""])
    lines.append("- Common manual tags: " + (", ".join(comparison["common_tags"]) or "none"))
    lines.append("- Common parser tags: " + (", ".join(comparison["common_parser_tags"]) or "none"))
    if comparison["shared_decision_terms"]:
        lines.append("- Shared decision/canon vocabulary: " + ", ".join(item["term"] for item in comparison["shared_decision_terms"][:15]))
    lines.extend(["", "> Comparison is descriptive only; conflicting thread-local state remains unresolved.", ""])
    return "\n".join(lines)


def dumps(comparison: dict[str, Any]) -> str:
    return json.dumps(comparison, indent=2, ensure_ascii=False)
