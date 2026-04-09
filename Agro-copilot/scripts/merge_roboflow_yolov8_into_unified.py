from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_CLASS_MAP: dict[str, str] = {
    "anthracnose": "anthracnose",
    "blackscale": "blackscale",
    "olivepeacockspot": "peacock_spot",
    "psyllid": "psyllid",
    "tuberculosis": "tuberculosis",
}


def sanitize_token(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"\s+", "_", value)
    value = re.sub(r"[^a-z0-9_.-]", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "unknown"


def load_yolo_class_names(data_yaml: Path) -> list[str]:
    names_line = None
    for line in data_yaml.read_text(encoding="utf-8-sig").splitlines():
        if line.strip().startswith("names:"):
            names_line = line.split(":", 1)[1].strip()
            break
    if not names_line:
        raise RuntimeError(f"Could not parse names from {data_yaml}")
    # Format is "['A', 'B', ...]"; eval with json-like normalization.
    names_text = names_line.replace("'", '"')
    return json.loads(names_text)


def parse_yolo_labels(label_file: Path) -> list[tuple[int, float, float, float, float]]:
    rows: list[tuple[int, float, float, float, float]] = []
    if not label_file.exists():
        return rows
    for line in label_file.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 5:
            continue
        cls = int(parts[0])
        cx, cy, w, h = map(float, parts[1:])
        rows.append((cls, cx, cy, w, h))
    return rows


def yolo_to_xyxy(
    cx: float,
    cy: float,
    w: float,
    h: float,
    width: int,
    height: int,
    pad_ratio: float = 0.03,
) -> tuple[int, int, int, int]:
    bw = w * width
    bh = h * height
    x1 = (cx * width) - (bw / 2)
    y1 = (cy * height) - (bh / 2)
    x2 = (cx * width) + (bw / 2)
    y2 = (cy * height) + (bh / 2)

    pad_x = bw * pad_ratio
    pad_y = bh * pad_ratio
    x1 -= pad_x
    y1 -= pad_y
    x2 += pad_x
    y2 += pad_y

    x1 = max(0, int(round(x1)))
    y1 = max(0, int(round(y1)))
    x2 = min(width, int(round(x2)))
    y2 = min(height, int(round(y2)))
    return x1, y1, x2, y2


def ensure_unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    n = 1
    while True:
        candidate = path.with_name(f"{stem}__{n}{suffix}")
        if not candidate.exists():
            return candidate
        n += 1


def compute_split_counts_from_manifest(rows: list[dict[str, str]]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {"train": {}, "val": {}, "test": {}}
    for row in rows:
        split = row["split"]
        cls = row["unified_class"]
        if split not in counts:
            counts[split] = {}
        counts[split][cls] = counts[split].get(cls, 0) + 1
    return counts


def short_stem(value: str, max_len: int = 40) -> str:
    token = sanitize_token(value)
    if len(token) <= max_len:
        return token
    digest = hashlib.sha1(token.encode("utf-8")).hexdigest()[:10]
    return f"{token[:max_len]}_{digest}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge Roboflow YOLOv8 detection dataset into olive_unified_v1.")
    parser.add_argument(
        "--rf-root",
        default="backend/data/datasets/olive_tree_diseases_rf/yolov8",
        help="Roboflow YOLOv8 extracted dataset root.",
    )
    parser.add_argument(
        "--unified-root",
        default="backend/data/datasets/olive_unified_v1",
        help="Unified dataset root.",
    )
    parser.add_argument(
        "--source-name",
        default="olive_tree_diseases_rf",
        help="Source dataset name to store in manifest.",
    )
    parser.add_argument(
        "--min-crop-size",
        type=int,
        default=24,
        help="Minimum width/height of crop to keep.",
    )
    args = parser.parse_args()

    rf_root = (REPO_ROOT / args.rf_root).resolve()
    unified_root = (REPO_ROOT / args.unified_root).resolve()
    manifest_path = unified_root / "manifest.csv"
    metadata_path = unified_root / "metadata.json"

    if not rf_root.exists():
        raise SystemExit(f"Missing rf_root: {rf_root}")
    if not manifest_path.exists():
        raise SystemExit(f"Missing unified manifest: {manifest_path}")
    if not metadata_path.exists():
        raise SystemExit(f"Missing unified metadata: {metadata_path}")

    split_map = {"train": "train", "valid": "val", "test": "test"}
    names = load_yolo_class_names(rf_root / "data.yaml")
    normalized_name_to_index = {sanitize_token(name): i for i, name in enumerate(names)}
    for required in DEFAULT_CLASS_MAP:
        if required not in normalized_name_to_index:
            raise SystemExit(f"Expected class '{required}' not found in Roboflow names: {names}")

    with manifest_path.open("r", newline="", encoding="utf-8-sig") as f:
        existing_rows = list(csv.DictReader(f))

    # Remove partial files from aborted runs (before manifest write).
    source_prefix = f"{sanitize_token(args.source_name)}__"
    for p in unified_root.rglob(f"{source_prefix}*.jpg"):
        if p.is_file():
            p.unlink()

    # Remove previous rows/files from same source to make reruns idempotent.
    kept_rows: list[dict[str, str]] = []
    removed = 0
    for row in existing_rows:
        if row["source_dataset"] != args.source_name:
            kept_rows.append(row)
            continue
        out_path = Path(row["output_path"])
        if not out_path.is_absolute():
            out_path = REPO_ROOT / out_path
        if out_path.exists():
            out_path.unlink()
        removed += 1

    new_rows: list[dict[str, str]] = []
    crops_written = 0

    for rf_split, unified_split in split_map.items():
        image_dir = rf_root / rf_split / "images"
        label_dir = rf_root / rf_split / "labels"
        if not image_dir.exists() or not label_dir.exists():
            continue

        for image_path in sorted(image_dir.glob("*")):
            if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
                continue
            label_path = label_dir / f"{image_path.stem}.txt"
            labels = parse_yolo_labels(label_path)
            if not labels:
                continue

            with Image.open(image_path) as im:
                im = im.convert("RGB")
                width, height = im.size
                for idx, (cls_idx, cx, cy, w, h) in enumerate(labels):
                    raw_name = names[cls_idx]
                    canonical = sanitize_token(raw_name)
                    unified_class = DEFAULT_CLASS_MAP.get(canonical)
                    if unified_class is None:
                        continue

                    x1, y1, x2, y2 = yolo_to_xyxy(cx, cy, w, h, width, height)
                    if (x2 - x1) < args.min_crop_size or (y2 - y1) < args.min_crop_size:
                        continue

                    crop = im.crop((x1, y1, x2, y2))
                    short_image_stem = short_stem(image_path.stem)
                    base_name = (
                        f"{sanitize_token(args.source_name)}__{sanitize_token(rf_split)}__"
                        f"{canonical}__{short_image_stem}__bbox{idx}.jpg"
                    )
                    out_dir = unified_root / unified_split / unified_class
                    out_dir.mkdir(parents=True, exist_ok=True)
                    out_path = ensure_unique_path(out_dir / base_name)
                    crop.save(out_path, format="JPEG", quality=95)
                    crops_written += 1

                    source_path = "/".join(
                        [
                            sanitize_token(args.source_name),
                            sanitize_token(rf_split),
                            canonical,
                            f"{image_path.name}#bbox{idx}",
                        ]
                    )

                    new_rows.append(
                        {
                            "split": unified_split,
                            "unified_class": unified_class,
                            "source_dataset": sanitize_token(args.source_name),
                            "source_split": sanitize_token(rf_split),
                            "source_class": canonical,
                            "source_path": source_path,
                            "output_path": str(out_path.relative_to(REPO_ROOT)).replace("/", "\\"),
                        }
                    )

    merged_rows = kept_rows + new_rows
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
    split_counts = compute_split_counts_from_manifest(merged_rows)
    metadata["split_counts"] = split_counts
    metadata["total_images"] = sum(sum(v.values()) for v in split_counts.values())

    class_mapping = metadata.get("class_mapping", {})
    class_mapping[sanitize_token(args.source_name)] = {
        key: value for key, value in DEFAULT_CLASS_MAP.items()
    }
    metadata["class_mapping"] = class_mapping

    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"removed_previous_rows={removed}")
    print(f"new_rows_added={len(new_rows)}")
    print(f"crops_written={crops_written}")
    print(f"manifest_rows_total={len(merged_rows)}")
    print(f"total_images={metadata['total_images']}")


if __name__ == "__main__":
    main()
