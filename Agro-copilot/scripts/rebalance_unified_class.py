from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def compute_split_counts(rows: list[dict[str, str]]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {"train": {}, "val": {}, "test": {}}
    for row in rows:
        split = row["split"]
        cls = row["unified_class"]
        if split not in counts:
            counts[split] = {}
        counts[split][cls] = counts[split].get(cls, 0) + 1
    return counts


def allocate_targets(
    groups: dict[tuple[str, str, str], list[dict[str, str]]],
    target_total: int,
) -> dict[tuple[str, str, str], int]:
    group_sizes = {k: len(v) for k, v in groups.items()}
    total = sum(group_sizes.values())
    if target_total > total:
        raise ValueError(f"target_total={target_total} exceeds class count={total}")

    raw = {
        k: (size * target_total) / total
        for k, size in group_sizes.items()
    }
    base = {k: int(v) for k, v in raw.items()}
    remainder = target_total - sum(base.values())
    frac_sorted = sorted(
        raw.items(),
        key=lambda kv: (kv[1] - int(kv[1]), kv[0]),
        reverse=True,
    )
    for k, _ in frac_sorted:
        if remainder <= 0:
            break
        if base[k] < group_sizes[k]:
            base[k] += 1
            remainder -= 1
    return base


def main() -> None:
    parser = argparse.ArgumentParser(description="Downsample one class in olive_unified manifest + files.")
    parser.add_argument(
        "--dataset-root",
        default="backend/data/datasets/olive_unified_v1",
        help="Unified dataset root directory.",
    )
    parser.add_argument(
        "--class-name",
        required=True,
        help="Unified class name to downsample (e.g., diseased_unspecified).",
    )
    parser.add_argument(
        "--target-total",
        type=int,
        required=True,
        help="Target total number of rows for class-name after downsampling.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic sampling.",
    )
    args = parser.parse_args()

    dataset_root = (REPO_ROOT / args.dataset_root).resolve()
    manifest_path = dataset_root / "manifest.csv"
    metadata_path = dataset_root / "metadata.json"
    if not manifest_path.exists():
        raise SystemExit(f"Missing manifest: {manifest_path}")
    if not metadata_path.exists():
        raise SystemExit(f"Missing metadata: {metadata_path}")

    with manifest_path.open("r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    target_rows = [r for r in rows if r["unified_class"] == args.class_name]
    keep_other_rows = [r for r in rows if r["unified_class"] != args.class_name]
    current_total = len(target_rows)
    if args.target_total >= current_total:
        raise SystemExit(
            f"Nothing to do: class '{args.class_name}' has {current_total} rows, target={args.target_total}."
        )

    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in target_rows:
        key = (row["split"], row["source_dataset"], row["source_class"])
        grouped[key].append(row)

    target_per_group = allocate_targets(grouped, args.target_total)
    rng = random.Random(args.seed)

    kept_target_rows: list[dict[str, str]] = []
    dropped_target_rows: list[dict[str, str]] = []
    for key, group_rows in grouped.items():
        keep_n = target_per_group[key]
        shuffled = group_rows[:]
        rng.shuffle(shuffled)
        kept_target_rows.extend(shuffled[:keep_n])
        dropped_target_rows.extend(shuffled[keep_n:])

    # Delete dropped files.
    deleted_files = 0
    for row in dropped_target_rows:
        out_path = Path(row["output_path"])
        if not out_path.is_absolute():
            out_path = REPO_ROOT / out_path
        try:
            out_path.relative_to(dataset_root)
        except ValueError as exc:
            raise SystemExit(f"Refusing to delete outside dataset root: {out_path}") from exc
        if out_path.exists():
            out_path.unlink()
            deleted_files += 1

    merged_rows = keep_other_rows + kept_target_rows
    fieldnames = [
        "split",
        "unified_class",
        "source_dataset",
        "source_split",
        "source_class",
        "source_path",
        "output_path",
    ]
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(merged_rows)

    metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
    split_counts = compute_split_counts(merged_rows)
    metadata["split_counts"] = split_counts
    metadata["total_images"] = sum(sum(v.values()) for v in split_counts.values())
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"class_name={args.class_name}")
    print(f"current_total={current_total}")
    print(f"target_total={args.target_total}")
    print(f"dropped_rows={len(dropped_target_rows)}")
    print(f"deleted_files={deleted_files}")
    print(f"new_manifest_total={len(merged_rows)}")


if __name__ == "__main__":
    main()
