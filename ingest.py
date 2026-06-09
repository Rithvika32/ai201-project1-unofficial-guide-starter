"""
ingest.py — Document ingestion pipeline for UNL CS Unofficial Guide.

Fetches all 10 sources from planning.md and saves them as .txt files in documents/.
Also provides chunk_text() used by embed.py.

Run:
    python ingest.py
"""

import base64
import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DOCUMENTS_DIR = Path("documents")
DOCUMENTS_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}


# ── Chunking ──────────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = 600, overlap: int = 75) -> list[str]:
    """
    Split text into overlapping character-level chunks.
    chunk_size=600 and overlap=75 match the spec in planning.md.
    Drops any chunk shorter than 50 chars (whitespace-only fragments).
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if len(chunk.strip()) >= 50:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


# ── Helpers ───────────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n ", "\n", text)
    return text.strip()


def save(filename: str, text: str):
    path = DOCUMENTS_DIR / filename
    path.write_text(text, encoding="utf-8")
    print(f"  saved: {filename}  ({len(text):,} chars)")


# ── Reddit (old.reddit.com HTML scraping) ────────────────────────────────────

def fetch_reddit(url: str, filename: str):
    # Convert to old.reddit.com which serves plain HTML without JS rendering
    old_url = url.replace("www.reddit.com", "old.reddit.com").rstrip("/")
    resp = requests.get(old_url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    lines = []

    # Post title
    title_tag = soup.find("a", class_="title")
    if title_tag:
        lines.append(f"Title: {title_tag.get_text(strip=True)}")
        lines.append("")

    # Post body (self-text)
    selftext = soup.find("div", class_="usertext-body")
    if selftext:
        lines.append(selftext.get_text(separator="\n", strip=True))
        lines.append("")

    lines.append("--- Comments ---")
    lines.append("")

    # Comments
    for comment_div in soup.find_all("div", class_="usertext-body"):
        text = comment_div.get_text(separator=" ", strip=True)
        if text and len(text) > 20:
            lines.append(text)
            lines.append("---")
            lines.append("")

    save(filename, clean_text("\n".join(lines)))
    time.sleep(1.5)


# ── UNL Catalog (BeautifulSoup) ───────────────────────────────────────────────

def fetch_unl(url: str, filename: str):
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup(["nav", "footer", "script", "style", "header", "aside"]):
        tag.decompose()

    main = (
        soup.find("main")
        or soup.find("div", id="contentarea")
        or soup.find("div", class_="page-content")
        or soup.body
    )

    save(filename, clean_text(main.get_text(separator="\n")))
    time.sleep(1.5)


# ── Rate My Professors (GraphQL) ──────────────────────────────────────────────

RMP_GRAPHQL = "https://www.ratemyprofessors.com/graphql"

RMP_QUERY = """
query GetRatings($id: ID!) {
  node(id: $id) {
    ... on Teacher {
      firstName
      lastName
      department
      school { name }
      avgRating
      avgDifficulty
      numRatings
      ratings(first: 20) {
        edges {
          node {
            class
            date
            comment
            qualityRating
            difficultyRating
          }
        }
      }
    }
  }
}
"""


def rmp_encode_id(legacy_id: int) -> str:
    return base64.b64encode(f"Teacher-{legacy_id}".encode()).decode()


def fetch_rmp(legacy_id: int, course: str, filename: str) -> bool:
    encoded_id = rmp_encode_id(legacy_id)
    payload = {"query": RMP_QUERY, "variables": {"id": encoded_id}}
    rmp_headers = {
        **HEADERS,
        "Content-Type": "application/json",
        "Authorization": "Basic dGVzdDp0ZXN0",
        "Referer": f"https://www.ratemyprofessors.com/professor/{legacy_id}",
    }

    try:
        resp = requests.post(RMP_GRAPHQL, json=payload, headers=rmp_headers, timeout=15)
    except requests.RequestException as e:
        print(f"  request failed for {course}: {e}")
        return False

    if resp.status_code != 200:
        print(f"  RMP returned HTTP {resp.status_code} for {course}")
        return False

    node = resp.json().get("data", {}).get("node")
    if not node:
        print(f"  RMP returned no data for {course}")
        return False

    lines = [
        f"Professor: {node['firstName']} {node['lastName']}",
        f"Department: {node.get('department', 'N/A')}",
        f"School: {node.get('school', {}).get('name', 'UNL')}",
        f"Course: {course}",
        f"Average Rating: {node.get('avgRating')}/5",
        f"Average Difficulty: {node.get('avgDifficulty')}/5",
        f"Total Ratings: {node.get('numRatings')}",
        "",
        "--- Student Reviews ---",
        "",
    ]

    for edge in node.get("ratings", {}).get("edges", []):
        r = edge["node"]
        lines.append(f"Course: {r.get('class', course)}")
        lines.append(f"Quality: {r.get('qualityRating')}/5   Difficulty: {r.get('difficultyRating')}/5")
        lines.append(f"Date: {str(r.get('date', ''))[:10]}")
        lines.append(r.get("comment", ""))
        lines.append("---")
        lines.append("")

    save(filename, clean_text("\n".join(lines)))
    time.sleep(1.5)
    return True


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\nFetching Reddit posts...")
    fetch_reddit(
        "https://www.reddit.com/r/Nebraska/comments/1bcxahr/university_of_nebraskalincoln_review_for_computer/",
        "reddit_unl_cs_review.txt",
    )
    fetch_reddit(
        "https://www.reddit.com/r/UNLincoln/comments/qkig1k/computer_science_questions/",
        "reddit_cs_questions.txt",
    )
    fetch_reddit(
        "https://www.reddit.com/r/UNLincoln/comments/giq20o/sccunl_comp_sci/",
        "reddit_transfer_cs.txt",
    )

    print("\nFetching UNL catalog pages...")
    fetch_unl(
        "https://catalog.unl.edu/undergraduate/engineering/computer-science/",
        "unl_cs_overview.txt",
    )
    fetch_unl(
        "http://catalog.unl.edu/undergraduate/engineering/computer-science/#text",
        "unl_cs_requirements.txt",
    )

    print("\nFetching Rate My Professors...")
    rmp_sources = [
        (1753186, "CS155E",   "rmp_cs155e.txt"),
        (3124994, "CSCE322",  "rmp_csce322.txt"),
        (2548211, "CSCE235",  "rmp_csce235.txt"),
        (2787050, "CSCE378",  "rmp_csce378.txt"),
        (2398527, "CSCE230",  "rmp_csce230.txt"),
    ]

    failed_rmp = []
    for legacy_id, course, fname in rmp_sources:
        ok = fetch_rmp(legacy_id, course, fname)
        if not ok:
            failed_rmp.append((legacy_id, course, fname))

    if failed_rmp:
        print("\n" + "=" * 60)
        print("MANUAL STEP REQUIRED — RMP blocked the following:")
        print("Visit each URL, copy all review text, and paste it")
        print("into the corresponding file under documents/")
        print()
        for legacy_id, course, fname in failed_rmp:
            print(f"  {course}: https://www.ratemyprofessors.com/professor/{legacy_id}")
            print(f"  -> documents/{fname}")
            print()
        print("=" * 60)

    print("\nDone. Files saved to documents/")
    print(f"Total files: {len(list(DOCUMENTS_DIR.glob('*.txt')))}")
