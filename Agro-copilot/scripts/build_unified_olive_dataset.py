from __future__ import annotations

import argparse
import csv
import json
import random
import re
import shutil
import unicodedata
from dataclasses import dataclass
from pathlib import Path


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

GLOBAL3_LABEL_ALIASES: dict[str, tuple[str, ...]] = {
    "saglam": ("saglam", "sağlam", "saÄŸlam"),
    "hastalikli": ("hastalikli", "hastalıklı", "hastalÄ±klÄ±"),
}


@dataclass(frozen=True)
class SourceSpec:
    dataset_name: str
    split_name: str
    root: Path
    class_map: dict[str, str]


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
    label = normalize_label_token(source_class)
    if dataset_name != "olive_global3_zeytin":
        return label
    for canonical, aliases in GLOBAL3_LABEL_ALIASES.items():
        if label in {normalize_label_token(alias) for alias in aliases}:
            return canonical
    return label


def collect_records(specs: list[SourceSpec]) -> list[dict]:
    records: list[dict] = []
    for spec in specs:
        if not spec.root.exists():
            continue
        for source_class, unified_class in spec.class_map.items():
            class_dirs: list[Path] = [spec.root / source_class]
            if spec.dataset_name == "olive_global3_zeytin":
                canonical = canonical_source_class(spec.dataset_name, source_class)
                for alias in GLOBAL3_LABEL_ALIASES.get(canonical, ()):
                    class_dirs.append(spec.root / alias)

            seen_dirs: set[Path] = set()
            for class_dir in class_dirs:
                class_dir = class_dir.resolve()
                if class_dir in seen_dirs or not class_dir.exists():
                    continue
                seen_dirs.add(class_dir)

                for img in class_dir.rglob("*"):
                    if not img.is_file():
                        continue
                    if img.suffix.lower() not in IMAGE_EXTS:
                        continue
                    records.append(
                        {
                            "source_dataset": spec.dataset_name,
                            "source_split": spec.split_name,
                            "source_class": canonical_source_class(spec.dataset_name, class_dir.name),
                            "unified_class": unified_class,
                            "source_path": img.resolve(),
                        }
                    )
    return records


def stratified_split(
    records: list[dict],
    val_ratio: float,
    test_ratio: float,
    seed: int,
) -> dict[str, list[dict]]:
    by_class: dict[str, list[dict]] = {}
    for rec in records:
        by_class.setdefault(rec["unified_class"], []).append(rec)

    rng = random.Random(seed)
    split_buckets = {"train": [], "val": [], "test": []}

    for cls, cls_items in by_class.items():
        items = cls_items[:]
        rng.shuffle(items)
        n = len(items)

        n_test = int(round(n * test_ratio))
        n_val = int(round(n * val_ratio))

        if n >= 3:
            n_test = max(1, n_test)
            n_val = max(1, n_val)

        if n_test + n_val >= n:
            overflow = (n_test + n_val) - (n - 1)
            while overflow > 0 and n_test > 1:
                n_test -= 1
                overflow -= 1
            while overflow > 0 and n_val > 1:
                n_val -= 1
                overflow -= 1
            if overflow > 0:
                n_test = max(0, n_test - overflow)

        n_train = n - n_val - n_test
        if n_train <= 0:
            raise RuntimeError(f"Invalid split sizes for class '{cls}' with n={n}")

        split_buckets["test"].extend(items[:n_test])
        split_buckets["val"].extend(items[n_test : n_test + n_val])
        split_buckets["train"].extend(items[n_test + n_val :])

    return split_buckets


def link_or_copy(src: Path, dst: Path, mode: str) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst.unlink()
    if mode == "hardlink":
        try:
            dst.hardlink_to(src)
            return
        except OSError:
            pass
    shutil.copy2(src, dst)


def build_output(
    splits: dict[str, list[dict]],
    out_dir: Path,
    link_mode: str,
) -> tuple[int, dict[str, dict[str, int]]]:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict] = []
    counts: dict[str, dict[str, int]] = {"train": {}, "val": {}, "test": {}}

    for split_name, items in splits.items():
        seen_names: set[str] = set()
        for rec in items:
            src = rec["source_path"]
            unified_class = rec["unified_class"]
            source_dataset = sanitize_token(rec["source_dataset"])
            source_split = sanitize_token(rec["source_split"])
            source_class = sanitize_token(rec["source_class"])
            stem = sanitize_token(src.stem)
            ext = src.suffix.lower()
            base_name = f"{source_dataset}__{source_split}__{source_class}__{stem}{ext}"
            candidate = base_name
            idx = 1
            while candidate in seen_names:
                candidate = f"{base_name.rsplit('.', 1)[0]}__{idx}.{ext.lstrip('.')}"
                idx += 1
            seen_names.add(candidate)

            dst = out_dir / split_name / unified_class / candidate
            link_or_copy(src, dst, link_mode)

            counts[split_name][unified_class] = counts[split_name].get(unified_class, 0) + 1
            manifest_rows.append(
                {
                    "split": split_name,
                    "unified_class": unified_class,
                    "source_dataset": rec["source_dataset"],
                    "source_split": rec["source_split"],
                    "source_class": rec["source_class"],
                    "source_path": "/".join(
                        [
                            sanitize_token(rec["source_dataset"]),
                            sanitize_token(rec["source_split"]),
                            sanitize_token(rec["source_class"]),
                            src.name,
                        ]
                    ),
                    "output_path": str(dst),
                }
            )

    manifest_path = out_dir / "manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "split",
                "unified_class",
                "source_dataset",
                "source_split",
                "source_class",
                "source_path",
                "output_path",
            ],
        )
        writer.writeheader()
        writer.writerows(manifest_rows)

    return len(manifest_rows), counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a unified olive disease dataset from local Kaggle sources."
    )
    parser.add_argument(
        "--output-dir",
        default="backend/data/datasets/olive_unified_v1",
        help="Destination folder for unified dataset.",
    )
    parser.add_argument(
        "--val-ratio",
        type=float,
        default=0.15,
        help="Validation split ratio (per class).",
    )
    parser.add_argument(
        "--test-ratio",
        type=float,
        default=0.15,
        help="Test split ratio (per class).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic splits.",
    )
    parser.add_argument(
        "--link-mode",
        choices=["hardlink", "copy"],
        default="hardlink",
        help="Use hardlink where possible, fallback/copy otherwise.",
    )
    args = parser.parse_args()

    specs = [
        SourceSpec(
            dataset_name="olive_leaf_kaggle",
            split_name="train",
            root=Path("backend/data/datasets/olive_leaf_kaggle/data/dataset/train"),
            class_map={
                "Healthy": "healthy",
                "olive_peacock_spot": "peacock_spot",
                "aculus_olearius": "aculus_olearius",
            },
        ),
        SourceSpec(
            dataset_name="olive_leaf_kaggle",
            split_name="test",
            root=Path("backend/data/datasets/olive_leaf_kaggle/data/dataset/test"),
            class_map={
                "Healthy": "healthy",
                "olive_peacock_spot": "peacock_spot",
                "aculus_olearius": "aculus_olearius",
            },
        ),
        SourceSpec(
            dataset_name="olive_global3_zeytin",
            split_name="all",
            root=Path("backend/data/datasets/olive_global3/data"),
            class_map={
                "sağlam": "healthy",
                "hastalıklı": "diseased_unspecified",
            },
        ),
    ]

    records = collect_records(specs)
    if not records:
        raise SystemExit("No source images found. Verify dataset paths first.")

    splits = stratified_split(
        records=records,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        seed=args.seed,
    )

    out_dir = Path(args.output_dir)
    total_written, counts = build_output(
        splits=splits,
        out_dir=out_dir,
        link_mode=args.link_mode,
    )

    metadata = {
        "version": "olive_unified_v1",
        "total_images": total_written,
        "split_counts": counts,
        "parameters": {
            "val_ratio": args.val_ratio,
            "test_ratio": args.test_ratio,
            "seed": args.seed,
            "link_mode": args.link_mode,
        },
        "class_mapping": {
            "olive_leaf_kaggle": {
                "healthy": "healthy",
                "olive_peacock_spot": "peacock_spot",
                "aculus_olearius": "aculus_olearius",
            },
            "olive_global3_zeytin": {
                "saglam": "healthy",
                "hastalikli": "diseased_unspecified",
            },
        },
        "source_label_aliases": {
            "olive_global3_zeytin": {
                "saglam": ["saglam"],
                "hastalikli": ["hastalikli"],
            },
        },
    }

    (out_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"output_dir={out_dir}")
    print(f"total_images={total_written}")
    for split_name in ("train", "val", "test"):
        split_total = sum(counts.get(split_name, {}).values())
        print(f"{split_name}_total={split_total}")
        for cls, n in sorted(counts.get(split_name, {}).items()):
            print(f"  {split_name}:{cls}={n}")


if __name__ == "__main__":
    main()
