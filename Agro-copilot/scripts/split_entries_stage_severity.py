import json
from copy import deepcopy
from pathlib import Path


ENTRIES_PATH = Path("backend/data/olive_knowledge/knowledge_entries.json")

SPLIT_TARGET_CATEGORIES = {"disease", "pest"}

STAGE_VARIANTS = [
    ("early", "Early-stage pattern", "Profil stade precoce", "نمط مرحلة مبكرة"),
    ("peak", "Peak-stage pattern", "Profil stade maximal", "نمط مرحلة ذروة"),
    ("late", "Late-stage pattern", "Profil stade tardif", "نمط مرحلة متأخرة"),
]

SEVERITY_VARIANTS = [
    ("low", "lower severity context", "contexte de severite faible", "سياق شدة منخفضة"),
    ("high", "higher severity context", "contexte de severite elevee", "سياق شدة مرتفعة"),
]


def _append_suffix(value: str, suffix: str) -> str:
    return f"{value} ({suffix})"


def _split_entry(entry: dict) -> list[dict]:
    variants: list[dict] = []
    for stage_code, stage_en, stage_fr, stage_ar in STAGE_VARIANTS:
        for sev_code, sev_en, sev_fr, sev_ar in SEVERITY_VARIANTS:
            variant = deepcopy(entry)
            variant_id = f"{entry['id']}__{stage_code}__{sev_code}"
            variant["id"] = variant_id
            variant["parent_id"] = entry["id"]
            variant["split_variant"] = True
            variant["severity_level"] = sev_code
            variant["phenology_focus"] = stage_code
            variant["decision_type"] = "diagnosis"

            kws = list(dict.fromkeys([*entry.get("keywords", []), stage_code, sev_code, "stage", "severity"]))
            variant["keywords"] = kws

            variant["probable_issue"] = {
                "en": _append_suffix(entry["probable_issue"]["en"], f"{stage_en}, {sev_en}"),
                "fr": _append_suffix(entry["probable_issue"]["fr"], f"{stage_fr}, {sev_fr}"),
                "ar": _append_suffix(entry["probable_issue"]["ar"], f"{stage_ar}، {sev_ar}"),
            }

            if sev_code == "high":
                variant["urgency_hint"] = "high"
            else:
                if entry.get("urgency_hint") == "high":
                    variant["urgency_hint"] = "medium"
                else:
                    variant["urgency_hint"] = entry.get("urgency_hint", "medium")

            wtc = variant.get("what_to_check_next", {})
            for lang, line in [
                ("en", f"Confirm stage/severity profile: {stage_en.lower()}, {sev_en}."),
                ("fr", f"Confirmer profil stade/severite: {stage_fr.lower()}, {sev_fr}."),
                ("ar", f"أكد نمط المرحلة/الشدة: {stage_ar}، {sev_ar}."),
            ]:
                if isinstance(wtc.get(lang), list):
                    wtc[lang] = [line, *wtc[lang]]
            variant["what_to_check_next"] = wtc

            variants.append(variant)
    return variants


def main() -> None:
    entries = json.loads(ENTRIES_PATH.read_text(encoding="utf-8"))

    if any(e.get("split_variant") is True for e in entries):
        print("split_variants_already_present=true; no-op")
        return

    base_entries = [e for e in entries if e.get("category") in SPLIT_TARGET_CATEGORIES]
    variants: list[dict] = []
    for entry in base_entries:
        variants.extend(_split_entry(entry))

    out = [*entries, *variants]
    ENTRIES_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"base_entries={len(base_entries)} variants_added={len(variants)} total_entries={len(out)}")


if __name__ == "__main__":
    main()
