#!/usr/bin/env python
"""Refresh Google Scholar citation data for every active group member.

Unlike a single-author site, a lab site has many authors. This script
screens the Google Scholar profile of every "active" team member listed
under the faculty and researchers ("Research Fellows") categories in
_data/team.yml (skipping adjunct_alumni, phd/msc alumni, and anyone with no
scholar link on their card) and merges their publications into one
_data/citations.yml, keyed by Scholar's own author_pub_id (which already
embeds the author's Scholar user id, e.g. "Jxm1UeYAAAAJ:_xSYboBqXhAC"), so
entries from different members never collide.
"""

import os
import re
import sys
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import yaml
from scholarly import scholarly

TEAM_FILE = "_data/team.yml"
OUTPUT_FILE = "_data/citations.yml"
ACTIVE_CATEGORIES = ["faculty", "researchers"]


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


def get_scholar_citations() -> None:
    scholars = load_active_scholars()
    if not scholars:
        print("No active member has a Scholar link on file. Nothing to do.")
        return

    today = datetime.now().strftime("%Y-%m-%d")

    existing_data = None
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE) as f:
                existing_data = yaml.safe_load(f)
        except Exception as e:
            print(f"Warning: could not read existing citation data from {OUTPUT_FILE}: {e}.")

    citation_data = {"metadata": {"last_updated": today}, "papers": {}}

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
                citation_data["papers"][pub_id] = {
                    "title": title,
                    "year": year,
                    "citations": citations,
                }
            except Exception as e:
                print(f"Error processing a publication for {name}: {e}. Skipped.")

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
