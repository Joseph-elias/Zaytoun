from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path("backend/data/olive_knowledge")
SOURCES_PATH = ROOT / "sources.json"
ENTRIES_PATH = ROOT / "knowledge_entries.json"
ONTOLOGY_PATH = ROOT / "ontology.json"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    sources = load_json(SOURCES_PATH)
    entries = load_json(ENTRIES_PATH)
    ontology = load_json(ONTOLOGY_PATH)

    source_ids = [s["id"] for s in sources]
    source_id_set = set(source_ids)
    source_refs = Counter()

    missing_source_refs = []
    for entry in entries:
        for source_id in entry.get("source_ids", []):
            source_refs[source_id] += 1
            if source_id not in source_id_set:
                missing_source_refs.append((entry.get("id"), source_id))

    unused_sources = [sid for sid in source_ids if source_refs[sid] == 0]

    allowed = {
        "category": set(ontology["categories"]),
        "decision_type": set(ontology["decision_types"]),
        "organ_targets": set(ontology["organ_targets"]),
        "phenology_stages": set(ontology["phenology_stages"]),
        "symptom_tags": set(ontology["symptom_tags"]),
    }

    ontology_issues = {
        "category": [],
        "decision_type": [],
        "organ_targets": [],
        "phenology_stages": [],
        "symptom_tags": [],
    }

    for entry in entries:
        entry_id = entry.get("id")

        if entry.get("category") not in allowed["category"]:
            ontology_issues["category"].append(entry_id)
        if entry.get("decision_type") not in allowed["decision_type"]:
            ontology_issues["decision_type"].append(entry_id)

        for key in ("organ_targets", "phenology_stages", "symptom_tags"):
            for val in entry.get(key, []):
                if val not in allowed[key]:
                    ontology_issues[key].append((entry_id, val))

    classifier_mapping_issues = []
    entry_ids = {entry.get("id") for entry in entries}
    mapping_rows = ontology.get("classifier_label_mapping", [])
    for row in mapping_rows:
        label = row.get("label")
        if not str(label or "").strip():
            classifier_mapping_issues.append(("missing_label", row))
            continue
        display = row.get("display", {})
        if not all(str(display.get(lang, "")).strip() for lang in ("en", "fr", "ar")):
            classifier_mapping_issues.append(("missing_display_lang", label))
        for prefix in row.get("knowledge_prefixes", []):
            exists = any(eid == prefix or str(eid).startswith(f"{prefix}__") for eid in entry_ids if eid)
            if not exists:
                classifier_mapping_issues.append(("unknown_knowledge_prefix", label, prefix))

    policy_issues = []
    policies = ontology.get("classifier_policies", {})
    for key in ("peacock_min_score", "peacock_min_margin", "low_conf_threshold", "healthy_high_conf_threshold"):
        val = policies.get(key, None)
        if not isinstance(val, (int, float)):
            policy_issues.append((key, "not_numeric"))
        elif not (0.0 <= float(val) <= 1.0):
            policy_issues.append((key, "outside_0_1"))

    required_source_fields = [
        "id",
        "title",
        "url",
        "publisher",
        "accessed_on",
        "trust_level",
    ]
    bad_sources = []
    for source in sources:
        missing = [k for k in required_source_fields if not str(source.get(k, "")).strip()]
        if missing:
            bad_sources.append((source.get("id"), missing))

    print(f"sources={len(sources)}")
    print(f"entries={len(entries)}")
    print(f"missing_source_refs={len(missing_source_refs)}")
    print(f"unused_sources={len(unused_sources)}")
    print(f"sources_missing_required_fields={len(bad_sources)}")
    for key, issues in ontology_issues.items():
        print(f"{key}_issues={len(issues)}")
    print(f"classifier_mapping_issues={len(classifier_mapping_issues)}")
    print(f"classifier_policy_issues={len(policy_issues)}")

    has_errors = (
        bool(missing_source_refs)
        or bool(unused_sources)
        or bool(bad_sources)
        or any(ontology_issues.values())
        or bool(classifier_mapping_issues)
        or bool(policy_issues)
    )
    if has_errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
