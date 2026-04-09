from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_EXE = Path(sys.executable)
TRAIN_SCRIPT = REPO_ROOT / "scripts" / "train_olive_transfer.py"
MANIFEST_PATH = REPO_ROOT / "backend" / "data" / "datasets" / "olive_unified_v1" / "manifest.csv"


def count_classes() -> None:
    with MANIFEST_PATH.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    counts = Counter(r["unified_class"] for r in rows)
    print(f"total: {len(rows)}")
    for cls, n in sorted(counts.items()):
        print(f"{cls}: {n}")


def run_train(mode: str, cli_args: argparse.Namespace) -> None:
    if not PYTHON_EXE.exists():
        raise SystemExit(f"Python not found at: {PYTHON_EXE}")
    if not TRAIN_SCRIPT.exists():
        raise SystemExit(f"Training script not found: {TRAIN_SCRIPT}")

    common = [
        str(PYTHON_EXE),
        str(TRAIN_SCRIPT),
        "--model-id",
        cli_args.model_id,
        "--dataset-root",
        cli_args.dataset_root,
        "--use-weighted-sampler",
        "--amp",
    ]

    if mode == "smoke":
        args = [
            "--output-dir",
            cli_args.output_dir_smoke,
            "--epochs",
            str(cli_args.smoke_epochs),
            "--batch-size",
            str(cli_args.smoke_batch_size),
            "--workers",
            str(cli_args.smoke_workers),
        ]
    else:
        args = [
            "--output-dir",
            cli_args.output_dir_full,
            "--epochs",
            str(cli_args.full_epochs),
            "--batch-size",
            str(cli_args.full_batch_size),
            "--workers",
            str(cli_args.full_workers),
            "--lr-head",
            "3e-4",
            "--lr-backbone",
            "3e-5",
            "--weight-decay",
            "1e-4",
            "--label-smoothing",
            "0.05",
            "--warmup-epochs",
            "2",
            "--early-stop-patience",
            "5",
        ]

    cmd = common + args
    print("Running:")
    print(" ".join(cmd))
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)


def list_artifacts(mode: str, cli_args: argparse.Namespace) -> None:
    out_dir = REPO_ROOT / "backend" / "models"
    if mode == "smoke":
        out_dir = REPO_ROOT / cli_args.output_dir_smoke
    else:
        out_dir = REPO_ROOT / cli_args.output_dir_full

    if not out_dir.exists():
        print(f"No artifacts yet at: {out_dir}")
        return

    print(out_dir)
    for p in sorted(out_dir.rglob("*")):
        rel = p.relative_to(REPO_ROOT)
        if p.is_dir():
            print(f"[DIR]  {rel}")
        else:
            print(f"[FILE] {rel}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple runner for olive transfer learning workflow.")
    parser.add_argument(
        "action",
        choices=["count", "smoke", "full", "list-smoke", "list-full"],
        help="Action to run.",
    )
    parser.add_argument("--model-id", default="mesabo/agri-plant-disease-resnet50")
    parser.add_argument("--dataset-root", default="backend/data/datasets/olive_unified_v1")
    parser.add_argument("--output-dir-smoke", default="backend/models/olive_transfer_mesabo_resnet50_smoke")
    parser.add_argument("--output-dir-full", default="backend/models/olive_transfer_mesabo_resnet50")
    parser.add_argument("--smoke-epochs", type=int, default=1)
    parser.add_argument("--smoke-batch-size", type=int, default=8)
    parser.add_argument("--smoke-workers", type=int, default=0)
    parser.add_argument("--full-epochs", type=int, default=20)
    parser.add_argument("--full-batch-size", type=int, default=16)
    parser.add_argument("--full-workers", type=int, default=2)
    args = parser.parse_args()
    if args.action == "count":
        count_classes()
    elif args.action == "smoke":
        run_train("smoke", args)
    elif args.action == "full":
        run_train("full", args)
    elif args.action == "list-smoke":
        list_artifacts("smoke", args)
    elif args.action == "list-full":
        list_artifacts("full", args)
    else:
        raise SystemExit(f"Unknown action: {args.action}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"Command failed with exit code {exc.returncode}", file=sys.stderr)
        raise
