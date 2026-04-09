from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_ROOT = REPO_ROOT / "backend" / "data" / "datasets" / "olive_unified_v1"
MANIFEST_PATH = DATASET_ROOT / "manifest.csv"
METADATA_PATH = DATASET_ROOT / "metadata.json"

RF_DATASET = "olive_tree_diseases_rf"
PROMOTE_CLASSES = {"anthracnose", "blackscale", "psyllid", "tuberculosis"}


def compute_split_counts(rows: list[dict[str, str]]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {"train": {}, "val": {}, "test": {}}
    for row in rows:
        split = row["split"]
        cls = row["unified_class"]
        if split not in counts:
            counts[split] = {}
        counts[split][cls] = counts[split].get(cls, 0) + 1
    return counts


def main() -> None:
    if not MANIFEST_PATH.exists():
        raise SystemExit(f"Missing manifest: {MANIFEST_PATH}")
    if not METADATA_PATH.exists():
        raise SystemExit(f"Missing metadata: {METADATA_PATH}")

    with MANIFEST_PATH.open("r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    changed = 0
    moved_files = 0

    for row in rows:
        if row["source_dataset"] != RF_DATASET:
            continue
        source_class = row["source_class"]
        if source_class not in PROMOTE_CLASSES:
            continue
        if row["unified_class"] == source_class:
            continue

        row["unified_class"] = source_class

        old_rel = Path(row["output_path"])
        old_abs = old_rel if old_rel.is_absolute() else (REPO_ROOT / old_rel)
        new_abs = DATASET_ROOT / row["split"] / source_class / old_abs.name
        new_abs.parent.mkdir(parents=True, exist_ok=True)

        if old_abs.exists():
            if new_abs.exists() and new_abs.resolve() != old_abs.resolve():
                new_abs.unlink()
            shutil.move(str(old_abs), str(new_abs))
            moved_files += 1

        row["output_path"] = str(new_abs.relative_to(REPO_ROOT)).replace("/", "\\")
        changed += 1

    fieldnames = [
        "split",
        "unified_class",
        "source_dataset",
        "source_split",
        "source_class",
        "source_path",
        "output_path",
    ]
    with MANIFEST_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8-sig"))
    split_counts = compute_split_counts(rows)
    metadata["split_counts"] = split_counts
    metadata["total_images"] = sum(sum(v.values()) for v in split_counts.values())

    class_mapping = metadata.get("class_mapping", {})
    class_mapping[RF_DATASET] = {
        "anthracnose": "anthracnose",
        "blackscale": "blackscale",
        "olivepeacockspot": "peacock_spot",
        "psyllid": "psyllid",
        "tuberculosis": "tuberculosis",
    }
    metadata["class_mapping"] = class_mapping

    METADATA_PATH.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"rows_changed={changed}")
    print(f"files_moved={moved_files}")
    print(f"total_images={metadata['total_images']}")


if __name__ == "__main__":
    main()
