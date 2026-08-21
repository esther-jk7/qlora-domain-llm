"""Download RCT abstracts from PubMed E-utilities. Resumable."""
import json
import os
import time
import urllib.parse
import urllib.request
import ssl
import xml.etree.ElementTree as ET

import certifi
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("NCBI_API_KEY", "")
EMAIL = os.getenv("NCBI_EMAIL", "")
BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# python.org builds ship no configured CA store, so point at certifi.
CA_BUNDLE = os.getenv("NCBI_CA_BUNDLE") or certifi.where()
SSL_CTX = ssl.create_default_context(cafile=CA_BUNDLE)

# Restrict to RCTs published recently, in English, with a real abstract.
QUERY = (
    'randomized controlled trial[pt] AND hasabstract '
    'AND english[lang] AND ("2018"[dp] : "2025"[dp]) '
    'AND humans[mh] '
    'AND (drug therapy[sh] OR therapeutics[mh] OR "clinical trial, phase iii"[pt]) '
    'AND (placebo[tiab] OR "double-blind"[tiab] OR "randomly assigned"[tiab])'
)
TARGET = 1600
BATCH = 200
DELAY = 0.11 if API_KEY else 0.35  # respect NCBI rate limits

OUT = Path("data/raw/abstracts.jsonl")
OUT.parent.mkdir(parents=True, exist_ok=True)


def call(endpoint: str, params: dict) -> str:
    params = {**params, "tool": "qlora-domain-llm", "email": EMAIL}
    if API_KEY:
        params["api_key"] = API_KEY
    url = f"{BASE}/{endpoint}?{urllib.parse.urlencode(params)}"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60, context=SSL_CTX) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:
            wait = 2 ** attempt
            print(f"  retry {attempt + 1} in {wait}s ({e})")
            time.sleep(wait)
    raise RuntimeError(f"failed after 4 attempts: {endpoint}")


def parse_batch(xml_text: str):
    """Yield {pmid, title, abstract} from an efetch XML response."""
    root = ET.fromstring(xml_text)
    for art in root.findall(".//PubmedArticle"):
        pmid_el = art.find(".//PMID")
        title_el = art.find(".//ArticleTitle")
        if pmid_el is None:
            continue

        # Structured abstracts split into labelled sections; join them,
        # keeping the labels because they help the extractor.
        parts = []
        for seg in art.findall(".//Abstract/AbstractText"):
            text = "".join(seg.itertext()).strip()
            if not text:
                continue
            label = seg.get("Label")
            parts.append(f"{label}: {text}" if label else text)

        abstract = " ".join(parts).strip()
        if len(abstract) < 900 or len(abstract) > 6000:
            continue

        yield {
            "pmid": pmid_el.text,
            "title": "".join(title_el.itertext()).strip() if title_el is not None else "",
            "abstract": abstract,
        }


def main():
    seen = set()
    if OUT.exists():
        with OUT.open() as f:
            seen = {json.loads(line)["pmid"] for line in f if line.strip()}
        print(f"resuming — {len(seen)} already downloaded")

    print("searching PubMed...")
    search = json.loads(
        call("esearch.fcgi", {
            "db": "pubmed", "term": QUERY,
            "retmax": TARGET * 2, "retmode": "json",
        })
    )
    pmids = [p for p in search["esearchresult"]["idlist"] if p not in seen]
    print(f"{len(pmids)} new PMIDs to fetch")

    kept = len(seen)
    with OUT.open("a") as out:
        for i in range(0, len(pmids), BATCH):
            chunk = pmids[i:i + BATCH]
            xml_text = call("efetch.fcgi", {
                "db": "pubmed", "id": ",".join(chunk), "retmode": "xml",
            })
            for rec in parse_batch(xml_text):
                if rec["pmid"] in seen:
                    continue
                seen.add(rec["pmid"])
                out.write(json.dumps(rec) + "\n")
                kept += 1
            out.flush()
            print(f"  {kept} abstracts kept")
            if kept >= TARGET:
                break
            time.sleep(DELAY)

    print(f"\nDONE — {kept} abstracts in {OUT}")


if __name__ == "__main__":
    main()
