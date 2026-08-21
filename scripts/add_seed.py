"""Interactive: append one hand-labeled seed example."""
import json
from pathlib import Path

from src.schema import PICO

RAW = Path("data/raw/abstracts.jsonl")
OUT = Path("data/processed/gold_seed.jsonl")
OUT.parent.mkdir(parents=True, exist_ok=True)

pmid = input("PMID: ").strip()
rows = {json.loads(l)["pmid"]: json.loads(l) for l in RAW.open()}
if pmid not in rows:
    raise SystemExit(f"PMID {pmid} not in abstracts.jsonl")

existing = set()
if OUT.exists():
    existing = {json.loads(l)["pmid"] for l in OUT.open() if l.strip()}
if pmid in existing:
    raise SystemExit(f"PMID {pmid} already seeded")

rec = rows[pmid]
print("\n" + "=" * 78)
print(rec["title"])
print("-" * 78)
print(rec["abstract"])
print("=" * 78 + "\n")

label = {
    "population": input("population        : ").strip(),
    "intervention": input("intervention      : ").strip(),
    "comparator": input("comparator        : ").strip(),
    "primary_outcome": input("primary_outcome   : ").strip(),
    "effect_direction": input(
        "effect_direction  [intervention_favored/comparator_favored/"
        "no_difference/unclear]: "
    ).strip(),
}
n = input("sample_size (blank=null): ").strip()
label["sample_size"] = int(n) if n else None

PICO.model_validate(label)

with OUT.open("a") as f:
    f.write(json.dumps({
        "pmid": pmid,
        "abstract": rec["abstract"],
        "label": label,
    }, ensure_ascii=False) + "\n")

print(f"\nsaved. total seeds: {len(existing) + 1}")
