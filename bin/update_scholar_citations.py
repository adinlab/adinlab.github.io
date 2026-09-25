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

import json
import os
import re
import sys
from datetime import datetime
from difflib import SequenceMatcher
from urllib.parse import parse_qs, urlparse

import yaml
from _bibtex_utils import (
    BIB_FILE,
    earliest_bib_year,
    format_authors,
    guess_abbr,
    is_junk_title,
    is_patent,
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


def load_active_scholars() -> list[dict]:
    """Return active members with a Scholar link and their employment window.

    Each entry is a dict {name, scholar_id, since, until}. `since`/`until`
    come from the member's _data/team.yml entry (record-only fields, never
    rendered on the site) and bound the auto-add screen to papers published
    during their time in the lab: a member's Scholar profile spans their
    whole career, and pre-lab output (PhD-era work, previous affiliations)
    must not leak into the lab bibliography. `since` defaults to the bib's
    earliest curated year, `until` to the present.
    """
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
            try:
                since = int(member.get("since")) if member.get("since") else None
            except (TypeError, ValueError):
                print(f"Warning: unparsable 'since' ({member.get('since')}) for {name}; treating as unset.")
                since = None
            try:
                until = int(member.get("until")) if member.get("until") else None
            except (TypeError, ValueError):
                print(f"Warning: unparsable 'until' ({member.get('until')}) for {name}; treating as unset.")
                until = None
            scholars.append(
                {
                    "name": name,
                    "scholar_id": user_ids[0],
                    "since": since,
                    "until": until,
                }
            )

    return scholars


def crossref_lookup(title: str) -> dict | None:
    """Query Crossref for the cleanest published record matching a title.

    Scholar's scraped metadata is frequently mangled: diacritics are dropped
    (Çelikok -> Gelikok), surnames merge into one token (Goncalvez Braz ->
    Goncalvezbraz), venues truncate with a literal ellipsis, and pub_url can
    point at the whole proceedings volume rather than the paper. Crossref's
    curated records don't have these problems, so when it returns a
    confident bibliographic match we prefer it.
    """
    try:
        import urllib.parse
        import urllib.request

        q = urllib.parse.urlencode({"query.bibliographic": title, "rows": "3"})
        req = urllib.request.Request(
            f"https://api.crossref.org/works?{q}",
            headers={"User-Agent": "adinlab-site-daemon/1.0 (mailto:kandemir@imada.sdu.dk)"},
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"    Crossref lookup failed for '{title[:40]}...': {e}")
        return None

    norm = lambda t: re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", "", t.lower())).strip()
    want = norm(title)
    for item in data.get("message", {}).get("items", []):
        got = norm(item.get("title", [""])[0] if item.get("title") else "")
        if got and (got == want or SequenceMatcher(None, want, got).ratio() >= 0.9):
            return item
    return None


def build_new_entry(filled: dict, existing_keys: set[str], defined_macros: set[str]) -> tuple[str, str] | None:
    """Return (key, bibtex_text) for a newly-discovered publication, or None."""
    bib = filled.get("bib", {})
    title = bib.get("title")
    author_str = bib.get("author")
    year = str(bib.get("pub_year") or "").strip()
    if not title or not author_str or not year:
        print(f"    Missing title/author/year in filled record for '{title}'. Skipping auto-add.")
        return None

    # Prefer Crossref's curated record when one matches the title confidently.
    cr = crossref_lookup(title)
    if cr:
        cr_authors = [f"{a.get('family', '').strip()}, {a.get('given', '').strip()}".strip(", ") for a in cr.get("author", [])]
        cr_authors = [a for a in cr_authors if a]
        if len(cr_authors) >= 2:
            # Scholar-style "Last, Given and Last2, Given2": format_authors will
            # re-split on " and ", so authors containing " and " internally are fine
            # only if we join with " and " at the person level. Build the Scholar
            # convention directly: "Given Last" per person.
            cr_authors = [f"{a.get('given', '').strip()} {a.get('family', '').strip()}".strip() for a in cr.get("author", [])]
            author_str = " and ".join(a for a in cr_authors if a)
        cr_title = (cr.get("title") or [""])[0]
        if cr_title:
            title = cr_title
        cr_year = (cr.get("issued", {}).get("date-parts") or [[None]])[0][0]
        if cr_year:
            year = str(cr_year)
        doi = (cr.get("DOI") or "").lower()
        if doi:
            cr_url = f"https://doi.org/{doi}"
        else:
            cr_url = ""
        print(f"    Crossref match found: DOI {doi or 'n/a'} - using curated metadata.")

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
    # NeurIPS proceedings appear the year after the conference: volume N is
    # the (N + 1987) conference. Scholar's year can be the publication year,
    # so correct it to the conference year when the volume number disagrees.
    vol_m = re.search(r"Advances in Neural Information Processing Systems (\d+)", citation, re.IGNORECASE)
    if vol_m:
        conf_year = int(vol_m.group(1)) + 1987
        try:
            if abs(int(year) - conf_year) == 1:
                year = str(conf_year)
        except ValueError:
            pass
    if cr:
        containers = cr.get("container-title") or []
        if containers:
            # Crossref lists the series first and the actual venue last
            # (e.g. "Frontiers in AI and Applications" + "HHAI 2025"); prefer
            # the most specific (last) container.
            venue = containers[-1]
    abstract = (bib.get("abstract") or "").replace("\n", " ").strip()
    if cr and cr_url:
        url = cr_url
    else:
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
        lines.append(f"\tabbr         = {{{abbr or 'arXiv'}}},")
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

    for member in scholars:
        name = member["name"]
        scholar_id = member["scholar_id"]
        member_since = member["since"] if member["since"] is not None else min_year
        member_until = member["until"] if member["until"] is not None else 9999
        print(
            f"Fetching citations for {name} (Scholar ID: {scholar_id}, employment window: {member_since}-{member_until if member_until != 9999 else 'present'})"
        )
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

                if is_junk_title(title):
                    print(f"  '{title[:60]}' looks like a Scholar pseudo-entry. Skipping auto-add.")
                    continue

                if is_patent(pub):
                    print(f"  '{title[:60]}' is a patent. Skipping auto-add.")
                    continue

                try:
                    year_int = int(str(year).strip())
                except ValueError:
                    year_int = None
                if year_int is not None and year_int < member_since:
                    continue  # published before joining the lab; not our scope to auto-add
                if year_int is not None and year_int > member_until:
                    continue  # published after leaving the lab; not our scope to auto-add

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
