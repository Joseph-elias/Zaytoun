from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path


GLOBAL3_LABEL_ALIASES: dict[str, tuple[str, ...]] = {
    "saglam": ("saglam", "sağlam", "saÄŸlam"),
    "hastalikli": ("hastalikli", "hastalıklı", "hastalÄ±klÄ±"),
}


def sanitize_token(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"\s+", "_", value)
    value = re.sub(r"[^a-z0-9_.-]", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "unknown"


def normalize_label_token(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return sanitize_token(value)


def canonical_source_class(dataset_name: str, source_class: str) -> str:
    normalized = normalize_label_token(source_class)
    if dataset_name != "olive_global3_zeytin":
        return normalized
    for canonical, aliases in GLOBAL3_LABEL_ALIASES.items():
        alias_norm = {normalize_label_token(alias) for alias in aliases}
        if normalized in alias_norm:
            return canonical
    return normalized


def is_legacy_absolute_path(path: str) -> bool:
    return bool(re.match(r"^[a-zA-Z]:\\", path))


def build_stable_source_path(row: dict[str, str]) -> str:
    source_path_raw = row.get("source_path", "").strip()
    source_name = Path(source_path_raw).name if source_path_raw else "unknown"
    return "/".join(
        [
            sanitize_token(row["source_dataset"]),
            sanitize_token(row["source_split"]),
            sanitize_token(row["source_class"]),
            source_name,
        ]
    )


def normalize_manifest_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], int]:
    fixed_rows: list[dict[str, str]] = []
    changes = 0
    for row in rows:
        out = dict(row)
        canonical_class = canonical_source_class(out["source_dataset"], out["source_class"])
        if out["source_class"] != canonical_class:
            out["source_class"] = canonical_class
            changes += 1

        current_source_path = out.get("source_path", "")
        should_fix_path = is_legacy_absolute_path(current_source_path) or "\\" in current_source_path
        if should_fix_path:
            stable = build_stable_source_path(out)
            if current_source_path != stable:
                out["source_path"] = stable
                changes += 1

        fixed_rows.append(out)
    return fixed_rows, changes


def compute_manifest_counts(rows: list[dict[str, str]]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {"train": {}, "val": {}, "test": {}}
    for row in rows:
        split = row["split"]
        cls = row["unified_class"]
        if split not in counts:
            counts[split] = {}
        counts[split][cls] = counts[split].get(cls, 0) + 1
    return counts


def compute_disk_counts(dataset_dir: Path) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {"train": {}, "val": {}, "test": {}}
    for split_dir in dataset_dir.iterdir():
        if not split_dir.is_dir():
            continue
        if split_dir.name not in {"train", "val", "test"}:
            continue
        for class_dir in split_dir.iterdir():
            if not class_dir.is_dir():
                continue
            n = sum(1 for p in class_dir.iterdir() if p.is_file())
            counts[split_dir.name][class_dir.name] = n
    return counts


def compute_file_sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def find_split_leakage(rows: list[dict[str, str]], repo_root: Path) -> list[tuple[str, list[str]]]:
    hash_to_splits: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        output_path = Path(row["output_path"])
        if not output_path.is_absolute():
            output_path = repo_root / output_path
        if not output_path.exists():
            continue
        digest = compute_file_sha1(output_path)
        hash_to_splits[digest].add(row["split"])

    leaks: list[tuple[str, list[str]]] = []
    for digest, splits in hash_to_splits.items():
        if len(splits) > 1:
            leaks.append((digest, sorted(splits)))
    return leaks


def dedupe_cross_split_rows(
    rows: list[dict[str, str]],
    repo_root: Path,
) -> tuple[list[dict[str, str]], list[Path]]:
    split_priority = {"test": 0, "val": 1, "train": 2}
    digest_groups: dict[str, list[tuple[dict[str, str], Path]]] = defaultdict(list)

    for row in rows:
        output_path = Path(row["output_path"])
        if not output_path.is_absolute():
            output_path = repo_root / output_path
        if not output_path.exists():
            continue
        digest_groups[compute_file_sha1(output_path)].append((row, output_path))

    keep_row_ids: set[int] = set()
    paths_to_delete: list[Path] = []

    for group in digest_groups.values():
        if len(group) == 1:
            keep_row_ids.add(id(group[0][0]))
            continue

        group_sorted = sorted(
            group,
            key=lambda item: (
                split_priority.get(item[0]["split"], 99),
                str(item[1]).lower(),
            ),
        )
        keep_row_ids.add(id(group_sorted[0][0]))
        for row, path in group_sorted[1:]:
            if row["split"] != group_sorted[0][0]["split"]:
                paths_to_delete.append(path)
            else:
                keep_row_ids.add(id(row))

    kept_rows = [row for row in rows if id(row) in keep_row_ids]
    return kept_rows, paths_to_delete


def normalize_metadata(metadata: dict, manifest_counts: dict[str, dict[str, int]]) -> tuple[dict, int]:
    fixed = dict(metadata)
    changes = 0

    class_mapping = dict(fixed.get("class_mapping", {}))
    global3_map_raw = class_mapping.get("olive_global3_zeytin", {})
    global3_map_fixed: dict[str, str] = {}
    for src, dst in global3_map_raw.items():
        global3_map_fixed[canonical_source_class("olive_global3_zeytin", src)] = dst
    if global3_map_fixed:
        desired = {
            "saglam": global3_map_fixed.get("saglam", "healthy"),
            "hastalikli": global3_map_fixed.get("hastalikli", "diseased_unspecified"),
        }
        if class_mapping.get("olive_global3_zeytin") != desired:
            class_mapping["olive_global3_zeytin"] = desired
            changes += 1

    if "olive_leaf_kaggle" in class_mapping:
        leaf_map = class_mapping["olive_leaf_kaggle"]
        normalized_leaf = {
            canonical_source_class("olive_leaf_kaggle", k): v
            for k, v in leaf_map.items()
        }
        if normalized_leaf != leaf_map:
            class_mapping["olive_leaf_kaggle"] = normalized_leaf
            changes += 1

    if fixed.get("class_mapping") != class_mapping:
        fixed["class_mapping"] = class_mapping

    expected_aliases = {
        "saglam": ["saglam"],
        "hastalikli": ["hastalikli"],
    }
    aliases = fixed.get("source_label_aliases", {})
    if aliases.get("olive_global3_zeytin") != expected_aliases:
        aliases = dict(aliases)
        aliases["olive_global3_zeytin"] = expected_aliases
        fixed["source_label_aliases"] = aliases
        changes += 1

    if fixed.get("split_counts") != manifest_counts:
        fixed["split_counts"] = manifest_counts
        changes += 1

    if fixed.get("total_images") != sum(sum(v.values()) for v in manifest_counts.values()):
        fixed["total_images"] = sum(sum(v.values()) for v in manifest_counts.values())
        changes += 1

    return fixed, changes


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "split",
        "unified_class",
        "source_dataset",
        "source_split",
        "source_class",
        "source_path",
        "output_path",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate/fix unified dataset hygiene.")
    parser.add_argument(
        "--dataset-dir",
        default="backend/data/datasets/olive_unified_v1",
        help="Path to unified dataset root.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Apply normalization fixes to manifest and metadata.",
    )
    parser.add_argument(
        "--fix-leakage",
        action="store_true",
        help="When used with --write, remove cross-split duplicate images by content hash.",
    )
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    repo_root = Path.cwd()
    manifest_path = dataset_dir / "manifest.csv"
    metadata_path = dataset_dir / "metadata.json"

    if not manifest_path.exists():
        raise SystemExit(f"Missing manifest: {manifest_path}")
    if not metadata_path.exists():
        raise SystemExit(f"Missing metadata: {metadata_path}")

    with manifest_path.open("r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))

    normalized_rows, manifest_changes = normalize_manifest_rows(rows)
    deleted_paths: list[Path] = []
    if args.write and args.fix_leakage:
        deduped_rows, deleted_paths = dedupe_cross_split_rows(normalized_rows, repo_root)
        if len(deduped_rows) != len(normalized_rows):
            manifest_changes += len(normalized_rows) - len(deduped_rows)
            normalized_rows = deduped_rows

    manifest_counts = compute_manifest_counts(normalized_rows)
    normalized_metadata, metadata_changes = normalize_metadata(metadata, manifest_counts)

    missing_output = 0
    for row in normalized_rows:
        output_path = Path(row["output_path"])
        if not output_path.is_absolute():
            output_path = repo_root / output_path
        if not output_path.exists():
            missing_output += 1

    leakage = find_split_leakage(normalized_rows, repo_root)
    if args.write and args.fix_leakage and deleted_paths:
        dataset_root = dataset_dir.resolve()
        deleted_unique = sorted({p.resolve() for p in deleted_paths})
        for path in deleted_unique:
            try:
                path.relative_to(dataset_root)
            except ValueError as exc:
                raise SystemExit(f"Refusing to delete outside dataset dir: {path}") from exc
            if path.exists():
                path.unlink()

    disk_counts = compute_disk_counts(dataset_dir)
    counts_match = manifest_counts == disk_counts
    has_mojibake = "Ã" in json.dumps(normalized_metadata, ensure_ascii=False)
    if args.write and (manifest_changes or metadata_changes):
        write_manifest(manifest_path, normalized_rows)
        metadata_path.write_text(
            json.dumps(normalized_metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    print(f"manifest_rows={len(normalized_rows)}")
    print(f"manifest_changes={manifest_changes}")
    print(f"metadata_changes={metadata_changes}")
    print(f"split_leakage_groups={len(leakage)}")
    print(f"deleted_cross_split_duplicates={len({str(p) for p in deleted_paths})}")
    print(f"missing_output_files={missing_output}")
    print(f"manifest_vs_disk_counts_match={counts_match}")
    print(f"metadata_mojibake_detected={has_mojibake}")
    if leakage:
        print("sample_leakage_keys=")
        for key, splits in leakage[:10]:
            print(f"  {key} :: {','.join(splits)}")

    problems = []
    if leakage:
        problems.append("split leakage detected")
    if missing_output:
        problems.append("missing output files")
    if not counts_match:
        problems.append("manifest counts mismatch with disk")
    if has_mojibake:
        problems.append("metadata mojibake detected")

    if problems:
        raise SystemExit("Dataset hygiene check failed: " + "; ".join(problems))


if __name__ == "__main__":
    main()
