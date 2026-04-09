from __future__ import annotations

import json
from pathlib import Path


ROOT = Path("backend/data/olive_knowledge")
SOURCES_PATH = ROOT / "sources.json"
ENTRIES_PATH = ROOT / "knowledge_entries.json"


NEW_SOURCES = [
    {
        "id": "pmc_olive_leaf_spot_review_2023",
        "title": "Olive leaf spot caused by Venturia oleaginea: An updated review",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC9868462/",
        "publisher": "Frontiers in Plant Science (PMC)",
        "accessed_on": "2026-04-09",
        "trust_level": "peer_reviewed_review",
    },
    {
        "id": "eppo_saisol",
        "title": "EPPO Global Database - Saissetia oleae (SAISOL)",
        "url": "https://gd.eppo.int/taxon/SAISOL",
        "publisher": "EPPO Global Database",
        "accessed_on": "2026-04-09",
        "trust_level": "official_phytosanitary_database",
    },
    {
        "id": "eppo_euphol",
        "title": "EPPO Global Database - Euphyllura olivina (EUPHOL)",
        "url": "https://gd.eppo.int/taxon/EUPHOL",
        "publisher": "EPPO Global Database",
        "accessed_on": "2026-04-09",
        "trust_level": "official_phytosanitary_database",
    },
    {
        "id": "mdpi_olive_psyllid_2020",
        "title": "Current Distribution of the Olive Psyllid, Euphyllura olivina, in California",
        "url": "https://www.mdpi.com/2075-4450/11/3/146",
        "publisher": "Insects (MDPI)",
        "accessed_on": "2026-04-09",
        "trust_level": "peer_reviewed_article",
    },
]


ENTRY_ENRICHMENT = {
    "peacock_spot": {
        "keywords": [
            "olive peacock spot",
            "peacock eye disease",
            "venturia oleaginea",
            "spilocaea oleagina",
            "circular dark leaf spots",
            "yellow halo on olive leaves",
            "olive leaf defoliation after rain",
        ],
        "source_ids": ["pmc_olive_leaf_spot_review_2023", "ucipm_peacock_spot", "eppo_cycol"],
    },
    "olive_anthracnose": {
        "keywords": [
            "olive anthracnose",
            "colletotrichum acutatum",
            "colletotrichum gloeosporioides",
            "orange spore masses",
            "mummified fruit on tree",
            "fruit rot in wet weather",
        ],
        "source_ids": ["pubmed_olive_anthracnose_2009", "pubmed_olive_anthracnose_2012", "eppo_collac"],
    },
    "olive_knot": {
        "keywords": [
            "olive tuberculosis",
            "tuberculosis of olive",
            "pseudomonas savastanoi",
            "woody galls on twigs",
            "knots on olive branches",
            "bacterial knot disease",
        ],
        "source_ids": ["ucipm_olive_knot", "eppo_psdmsa"],
    },
    "olive_psyllid": {
        "keywords": [
            "olive psyllid",
            "euphyllura olivina",
            "cottony wax on flowers",
            "psyllid nymph colonies",
            "spring olive bloom feeding",
            "honeydew from psyllids",
        ],
        "source_ids": ["ucipm_olive_psyllid", "eppo_euphol", "mdpi_olive_psyllid_2020"],
    },
    "sooty_mold_black_scale": {
        "keywords": [
            "black scale",
            "saissetia oleae",
            "olive soft scale",
            "black sooty mold coating",
            "sticky honeydew on leaves",
            "scale insects on twigs",
        ],
        "source_ids": ["ucipm_black_scale", "eppo_saisol"],
    },
}


def main() -> None:
    sources = json.loads(SOURCES_PATH.read_text(encoding="utf-8-sig"))
    entries = json.loads(ENTRIES_PATH.read_text(encoding="utf-8-sig"))

    source_by_id = {s["id"]: s for s in sources}
    for src in NEW_SOURCES:
        source_by_id[src["id"]] = src
    sources_out = sorted(source_by_id.values(), key=lambda x: x["id"])

    changed_entries = 0
    for e in entries:
        for prefix, enrich in ENTRY_ENRICHMENT.items():
            if e["id"] == prefix or e["id"].startswith(prefix + "__"):
                current_keywords = list(e.get("keywords", []))
                for kw in enrich["keywords"]:
                    if kw not in current_keywords:
                        current_keywords.append(kw)
                e["keywords"] = current_keywords

                current_sources = list(e.get("source_ids", []))
                for sid in enrich["source_ids"]:
                    if sid not in current_sources:
                        current_sources.append(sid)
                e["source_ids"] = current_sources
                changed_entries += 1
                break

    SOURCES_PATH.write_text(json.dumps(sources_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ENTRIES_PATH.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"sources_total={len(sources_out)}")
    print(f"entries_touched={changed_entries}")


if __name__ == "__main__":
    main()
