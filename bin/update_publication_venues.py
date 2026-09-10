#!/usr/bin/env python
"""Update arXiv-only papers.bib entries once Scholar shows a real venue.

update_scholar_citations.py already does one bulk fetch per active member's
Scholar profile, and that fetch includes Scholar's own "citation" string per
paper (e.g. "ICLR, 2026", or "arXiv preprint arXiv:2505.19682, 2025" while
still unpublished) at no extra request cost - so this script works purely
from the _data/citations.yml that produces, matching by title (falling back
to a fuzzy match, since an arXiv revision can rename a paper before Scholar's
cached title catches up). It makes no Scholar requests of its own: doing a
live search or fill() per publication would add a request per paper on every
run, which is exactly the kind of extra Scholar load we want to avoid for
something that only concerns the handful of entries still marked as
preprints.

Run update_scholar_citations.py first so citations.yml is fresh.
"""

from __future__ import annotations

import re
import sys

import yaml
from _bibtex_utils import (
    BIB_FILE,
    entry_key,
    extract_field,
    guess_abbr,
    known_string_macros,
    normalize_title,
    split_entries,
    venue_from_citation,
)
from _bibtex_utils import best_title_match as match_title

CITATIONS_FILE = "_data/citations.yml"

CONFERENCE_HINTS = (
    "conference",
    "workshop",
    "symposium",
    "proceedings",
    "advances in neural",
    "international",
)


def load_citations_by_title() -> dict[str, str]:
    """Return {normalized_title: venue_citation} from _data/citations.yml."""
    try:
        with open(CITATIONS_FILE) as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        print(f"{CITATIONS_FILE} not found. Run update_scholar_citations.py first.")
        return {}

    by_title = {}
    for paper in (data.get("papers") or {}).values():
        title = paper.get("title")
        citation = paper.get("venue_citation")
        if title and citation:
            by_title[normalize_title(title)] = citation
    return by_title


def rewrite_entry(entry: str, venue: str, defined_macros: set[str]) -> str:
    is_conference = any(hint in venue.lower() for hint in CONFERENCE_HINTS)
    escaped_venue = venue.replace("{", "").replace("}", "")

    abbr = guess_abbr(venue)
    # Prefer the file's existing @string macro (e.g. `icml`) over a literal
    # venue string when the guessed abbreviation already has one defined,
    # matching how every other entry in this file references its venue.
    macro = abbr.lower() if abbr and abbr.lower() in defined_macros else None
    venue_ref = macro if macro else f"{{{escaped_venue}}}"

    if is_conference:
        entry = re.sub(r"^@article\{", "@inproceedings{", entry, count=1)
        entry = re.sub(r"\bjournal\s*=\s*arxiv\s*,", f"booktitle    = {venue_ref},", entry, count=1)
    else:
        entry = re.sub(r"\bjournal\s*=\s*arxiv\s*,", f"journal      = {venue_ref},", entry, count=1)

    if abbr:
        entry = re.sub(r"abbr\s*=\s*\{arXiv\}", f"abbr         = {{{abbr}}}", entry, count=1)

    return entry


def update_venues() -> None:
    citations_by_title = load_citations_by_title()
    if not citations_by_title:
        print("No usable citation data found. Nothing to check.")
        return

    with open(BIB_FILE) as f:
        text = f.read()

    defined_macros = known_string_macros(text)
    scholar_titles = list(citations_by_title.keys())

    candidates = []
    for start, end, entry in split_entries(text):
        if not re.search(r"\bjournal\s*=\s*arxiv\s*,", entry):
            continue
        title = extract_field(entry, "title")
        if title:
            candidates.append((start, end, entry, entry_key(entry), title))

    if not candidates:
        print("No arXiv-only entries found. Nothing to check.")
        return

    print(f"Checking {len(candidates)} arXiv-only entrie(s) against cached Scholar data...")
    updates = []
    for start, end, entry, key, title in candidates:
        matched_title = match_title(title, scholar_titles)
        if matched_title is None:
            print(f"  - {key}: no matching Scholar record (even fuzzily) in {CITATIONS_FILE}. Skipping.")
            continue

        raw_citation = citations_by_title[matched_title]
        venue = venue_from_citation(raw_citation)
        if not venue:
            print(f"  - {key}: still arXiv-only on Scholar ('{raw_citation}'). No change.")
            continue

        print(f"  - {key}: now published - '{raw_citation}' -> venue '{venue}'")
        updates.append((start, end, rewrite_entry(entry, venue, defined_macros), key, venue))

    if not updates:
        print("No entries changed.")
        return

    for start, end, new_entry, _key, _venue in sorted(updates, key=lambda u: u[0], reverse=True):
        text = text[:start] + new_entry + text[end:]

    with open(BIB_FILE, "w") as f:
        f.write(text)

    print(f"Updated {len(updates)} entrie(s) with their published venue:")
    for _start, _end, _new, key, venue in updates:
        print(f"  - {key}: {venue}")


if __name__ == "__main__":
    try:
        update_venues()
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
