#!/usr/bin/env python
"""Refresh Google Scholar citation data and add any papers missing from bib.

Unlike a single-author site, a lab site has many authors. This script
screens the Google Scholar profile of every "active" team member listed
under the faculty and researchers ("Research Fellows") categories in
_data/team.yml (skipping adjunct_alumni, phd/msc alumni, and anyone with no
scholar link on their card).

For every publication it finds:
  - It always records title/year/citation-count/venue into
    _data/citations.yml, keyed by Scholar's own author_pub_id, so entries
    from different members never collide. This part is one bulk request per
    member - cheap regardless of how many papers they have.
  - If the paper's title doesn't match (exactly or fuzzily) anything already
    in _bibliography/papers.bib AND its year is at or after the earliest
    year already curated there, it is treated as missing from the lab's
    bibliography and gets ONE extra scholarly.fill() call to pull its full
    author list, abstract and venue, which is used to append a new BibTeX
    entry. This extra request only happens for genuinely new/missing papers
    (typically zero to a handful per run), not for the full publication
    list, to keep Scholar request volume low. The year cutoff matters: a
    member's Scholar profile includes their entire career, and without it
    the first run for a newly-added member would dump decades of pre-lab
    publications (old PhD/postdoc work, unrelated prior affiliations) into
    the lab bibliography instead of just catching genuinely new lab output.

update_publication_venues.py handles the complementary case: an existing
arXiv-only bib entry that has since been accepted somewhere.
"""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import yaml
from _bibtex_utils import (
    BIB_FILE,
    earliest_bib_year,
    format_authors,
    guess_abbr,
    known_string_macros,
    load_bib_titles,
    slugify_key,
    split_entries,
    venue_from_citation,
)
from _bibtex_utils import best_title_match as match_title
from scholarly import scholarly

TEAM_FILE = "_data/team.yml"
OUTPUT_FILE = "_data/citations.yml"
ACTIVE_CATEGORIES = ["faculty", "researchers"]

CONFERENCE_HINTS = (
    "conference",
    "workshop",
    "symposium",
    "proceedings",
    "advances in neural",
    "international",
)


def load_active_scholars() -> list[tuple[str, str]]:
    """Return [(name, scholar_user_id), ...] for active members with a Scholar link."""
    if not os.path.exists(TEAM_FILE):
        print(f"Team file {TEAM_FILE} not found.")
        sys.exit(1)

    with open(TEAM_FILE) as f:
        team = yaml.safe_load(f)

    scholars = []
    for category in ACTIVE_CATEGORIES:
        for member in team.get(category) or []:
            scholar_url = member.get("scholar")
            name = member.get("name", "Unknown")
            if not scholar_url:
                print(f"Skipping {name} ({category}): no scholar link on file.")
                continue
            user_ids = parse_qs(urlparse(scholar_url).query).get("user")
            if not user_ids:
                print(f"Skipping {name} ({category}): could not parse a Scholar user id from {scholar_url}.")
                continue
            scholars.append((name, user_ids[0]))

    return scholars


def build_new_entry(filled: dict, existing_keys: set[str], defined_macros: set[str]) -> tuple[str, str] | None:
    """Return (key, bibtex_text) for a newly-discovered publication, or None."""
    bib = filled.get("bib", {})
    title = bib.get("title")
    author_str = bib.get("author")
    year = str(bib.get("pub_year") or "").strip()
    if not title or not author_str or not year:
        print(f"    Missing title/author/year in filled record for '{title}'. Skipping auto-add.")
        return None

    authors = format_authors(author_str)
    first_author = author_str.split(" and ")[0]
    key = slugify_key(first_author, year, title)
    if key in existing_keys:
        suffix = 2
        while f"{key}{suffix}" in existing_keys:
            suffix += 1
        key = f"{key}{suffix}"

    citation = bib.get("citation", "")
    venue = venue_from_citation(citation)
    abstract = (bib.get("abstract") or "").replace("\n", " ").strip()
    url = filled.get("pub_url") or filled.get("eprint_url") or ""

    lines = []
    abbr = guess_abbr(venue) if venue else "arXiv"
    if venue:
        is_conference = any(hint in venue.lower() for hint in CONFERENCE_HINTS)
        macro = abbr.lower() if abbr and abbr.lower() in defined_macros else None
        venue_ref = macro if macro else f"{{{venue}}}"
        entry_type = "inproceedings" if is_conference else "article"
        venue_field = "booktitle" if is_conference else "journal"
        lines.append(f"@{entry_type}{{{key},")
        lines.append(f"\tabbr         = {{{abbr}}},")
        lines.append(f"\ttitle        = {{{title}}},")
        lines.append(f"\tauthor       = {{{authors}}},")
        lines.append(f"\tyear         = {{{year}}},")
        lines.append(f"\t{venue_field}    = {venue_ref},")
    else:
        lines.append(f"@article{{{key},")
        lines.append("\tabbr         = {arXiv},")
        lines.append(f"\ttitle        = {{{title}}},")
        lines.append(f"\tauthor       = {{{authors}}},")
        lines.append(f"\tyear         = {{{year}}},")
        lines.append("\tjournal      = arxiv,")

    if url:
        lines.append(f"\turl          = {{{url}}},")
        lines.append(f"\thtml         = {{{url}}},")
    lines.append("\tselected     = {false},")
    lines.append("\tbibtex_show  = {true},")
    if abstract:
        lines.append(f"\tabstract     = {{{abstract}}},")
    lines.append("}\n")
    return key, "\n".join(lines)


def get_scholar_citations() -> None:
    scholars = load_active_scholars()
    if not scholars:
        print("No active member has a Scholar link on file. Nothing to do.")
        return

    with open(BIB_FILE) as f:
        bib_text = f.read()
    bib_titles = load_bib_titles(bib_text)
    existing_keys = {m.group(1) for m in (re.match(r"@\w+\{([^,]+),", e) for _s, _e, e in split_entries(bib_text)) if m}
    defined_macros = known_string_macros(bib_text)
    min_year = earliest_bib_year(bib_text)
    print(f"Only screening for missing publications from {min_year} onward (earliest year already in {BIB_FILE}).")

    today = datetime.now().strftime("%Y-%m-%d")

    existing_data = None
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE) as f:
                existing_data = yaml.safe_load(f)
        except Exception as e:
            print(f"Warning: could not read existing citation data from {OUTPUT_FILE}: {e}.")

    citation_data = {"metadata": {"last_updated": today}, "papers": {}}
    new_entries = []  # (key, bibtex_text)

    scholarly.set_timeout(15)
    scholarly.set_retries(3)

    for name, scholar_id in scholars:
        print(f"Fetching citations for {name} (Scholar ID: {scholar_id})")
        try:
            author = scholarly.search_author_id(scholar_id)
            author_data = scholarly.fill(author, sections=["publications"])
        except Exception as e:
            print(f"Error fetching Scholar data for {name} ({scholar_id}): {e}. Skipping.")
            continue

        for pub in author_data.get("publications", []):
            try:
                pub_id = pub.get("author_pub_id") or pub.get("pub_id")
                if not pub_id:
                    continue
                title = pub.get("bib", {}).get("title", "Unknown Title")
                year = pub.get("bib", {}).get("pub_year", "Unknown Year")
                citations = pub.get("num_citations", 0)
                venue_citation = pub.get("bib", {}).get("citation", "")
                citation_data["papers"][pub_id] = {
                    "title": title,
                    "year": year,
                    "citations": citations,
                    "venue_citation": venue_citation,
                }

                if match_title(title, bib_titles) is not None:
                    continue  # already in papers.bib (exactly or fuzzily)

                try:
                    year_int = int(str(year).strip())
                except ValueError:
                    year_int = None
                if year_int is not None and year_int < min_year:
                    continue  # predates the lab's curated era; not our scope to auto-add

                print(f"  '{title}' ({year}) is not in {BIB_FILE} yet. Fetching full record...")
                try:
                    filled = scholarly.fill(pub)
                except Exception as e:
                    print(f"    Error fetching full record: {e}. Skipping auto-add.")
                    continue

                result = build_new_entry(filled, existing_keys, defined_macros)
                if result:
                    key, entry_text = result
                    existing_keys.add(key)
                    bib_titles.append(title.lower())
                    new_entries.append((key, entry_text))
                    print(f"    Added new entry '{key}'.")
            except Exception as e:
                print(f"Error processing a publication for {name}: {e}. Skipped.")

    if new_entries:
        # Insert right after the last @string{...} definition line.
        last_string_end = 0
        for m in re.finditer(r"@string\{[^\n]*\}\n", bib_text):
            last_string_end = m.end()
        insertion = "\n" + "\n".join(text for _key, text in new_entries)
        bib_text = bib_text[:last_string_end] + insertion + bib_text[last_string_end:]
        with open(BIB_FILE, "w") as f:
            f.write(bib_text)
        print(f"Appended {len(new_entries)} new publication(s) to {BIB_FILE}: " + ", ".join(k for k, _t in new_entries))

    if not citation_data["papers"]:
        print("No publications were fetched for any active member. Not overwriting existing data.")
        return

    if existing_data and existing_data.get("papers") == citation_data["papers"]:
        print("No changes in citation data. Skipping file update.")
        return

    try:
        with open(OUTPUT_FILE, "w") as f:
            yaml.dump(citation_data, f, width=1000, sort_keys=True)
        print(f"Citation data for {len(scholars)} active member(s) saved to {OUTPUT_FILE}")
    except Exception as e:
        print(f"Error writing citation data to {OUTPUT_FILE}: {e}.")
        sys.exit(1)


if __name__ == "__main__":
    try:
        get_scholar_citations()
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
