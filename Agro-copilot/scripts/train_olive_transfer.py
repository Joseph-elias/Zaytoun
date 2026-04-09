from __future__ import annotations

import argparse
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, WeightedRandomSampler
from torchvision import datasets, transforms
from transformers import (
    AutoConfig,
    AutoFeatureExtractor,
    AutoImageProcessor,
    AutoModelForImageClassification,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def compute_confusion_matrix(y_true: list[int], y_pred: list[int], num_classes: int) -> np.ndarray:
    cm = np.zeros((num_classes, num_classes), dtype=np.int64)
    for t, p in zip(y_true, y_pred):
        cm[t, p] += 1
    return cm


def compute_metrics_from_cm(cm: np.ndarray) -> dict[str, float]:
    tp = np.diag(cm).astype(np.float64)
    support = cm.sum(axis=1).astype(np.float64)
    pred_count = cm.sum(axis=0).astype(np.float64)
    total = cm.sum().astype(np.float64)

    precision = np.divide(tp, np.maximum(pred_count, 1.0))
    recall = np.divide(tp, np.maximum(support, 1.0))
    f1 = np.divide(2.0 * precision * recall, np.maximum(precision + recall, 1e-12))
    accuracy = float(tp.sum() / max(total, 1.0))

    return {
        "accuracy": accuracy,
        "macro_precision": float(np.mean(precision)),
        "macro_recall": float(np.mean(recall)),
        "macro_f1": float(np.mean(f1)),
    }


def build_classification_report(cm: np.ndarray, class_names: list[str]) -> dict:
    tp = np.diag(cm).astype(np.float64)
    support = cm.sum(axis=1).astype(np.float64)
    pred_count = cm.sum(axis=0).astype(np.float64)
    precision = np.divide(tp, np.maximum(pred_count, 1.0))
    recall = np.divide(tp, np.maximum(support, 1.0))
    f1 = np.divide(2.0 * precision * recall, np.maximum(precision + recall, 1e-12))

    report: dict[str, dict[str, float]] = {}
    for i, name in enumerate(class_names):
        report[name] = {
            "precision": float(precision[i]),
            "recall": float(recall[i]),
            "f1-score": float(f1[i]),
            "support": int(support[i]),
        }

    macro = compute_metrics_from_cm(cm)
    report["macro avg"] = {
        "precision": macro["macro_precision"],
        "recall": macro["macro_recall"],
        "f1-score": macro["macro_f1"],
        "support": int(support.sum()),
    }
    report["accuracy"] = {"value": macro["accuracy"]}
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transfer learning on olive_unified_v1 using HF plant-disease checkpoints."
    )
    parser.add_argument(
        "--model-id",
        default="mesabo/agri-plant-disease-resnet50",
        help="Hugging Face model id to fine-tune.",
    )
    parser.add_argument(
        "--dataset-root",
        default="backend/data/datasets/olive_unified_v1",
        help="Dataset root with train/val/test folders.",
    )
    parser.add_argument(
        "--output-dir",
        default="backend/models/olive_transfer_mesabo_resnet50",
        help="Directory for checkpoints and reports.",
    )
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--lr-head", type=float, default=3e-4)
    parser.add_argument("--lr-backbone", type=float, default=3e-5)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--label-smoothing", type=float, default=0.05)
    parser.add_argument("--warmup-epochs", type=int, default=2)
    parser.add_argument("--early-stop-patience", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--device",
        default="cuda" if torch.cuda.is_available() else "cpu",
        choices=["cuda", "cpu"],
    )
    parser.add_argument(
        "--use-weighted-sampler",
        action="store_true",
        help="Use weighted random sampler for train loader.",
    )
    parser.add_argument(
        "--amp",
        action="store_true",
        help="Enable mixed precision training (CUDA only).",
    )
    args = parser.parse_args()
    if args.epochs <= 0:
        raise SystemExit("--epochs must be > 0")
    if args.batch_size <= 0:
        raise SystemExit("--batch-size must be > 0")
    if args.workers < 0:
        raise SystemExit("--workers must be >= 0")
    if args.warmup_epochs < 0:
        raise SystemExit("--warmup-epochs must be >= 0")
    if args.early_stop_patience < 0:
        raise SystemExit("--early-stop-patience must be >= 0")
    return args


def set_seed(seed: int) -> None:
    torch.manual_seed(seed)
    np.random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def get_image_size_from_preprocess(preprocess_obj) -> int:
    size = getattr(preprocess_obj, "size", None)
    if size is None:
        return 224
    if isinstance(size, dict):
        if "shortest_edge" in size:
            return int(size["shortest_edge"])
        if "height" in size:
            return int(size["height"])
    if isinstance(size, int):
        return int(size)
    return 224


def load_preprocess_config(model_id: str) -> tuple[object | None, int, list[float], list[float], str]:
    image_mean_default = [0.485, 0.456, 0.406]
    image_std_default = [0.229, 0.224, 0.225]

    try:
        processor = AutoImageProcessor.from_pretrained(model_id)
        image_size = get_image_size_from_preprocess(processor)
        image_mean = list(getattr(processor, "image_mean", image_mean_default))
        image_std = list(getattr(processor, "image_std", image_std_default))
        return processor, image_size, image_mean, image_std, "auto_image_processor"
    except Exception:
        pass

    try:
        feature_extractor = AutoFeatureExtractor.from_pretrained(model_id)
        image_size = get_image_size_from_preprocess(feature_extractor)
        image_mean = list(getattr(feature_extractor, "image_mean", image_mean_default))
        image_std = list(getattr(feature_extractor, "image_std", image_std_default))
        return feature_extractor, image_size, image_mean, image_std, "auto_feature_extractor"
    except Exception:
        pass

    try:
        cfg = AutoConfig.from_pretrained(model_id)
        image_size = int(getattr(cfg, "image_size", 224))
    except Exception:
        image_size = 224

    return None, image_size, image_mean_default, image_std_default, "fallback_imagenet_defaults"


def build_transforms(image_size: int, image_mean: list[float], image_std: list[float]):
    train_tf = transforms.Compose(
        [
            transforms.RandomResizedCrop(image_size, scale=(0.75, 1.0)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomVerticalFlip(p=0.2),
            transforms.RandomRotation(degrees=12),
            transforms.ColorJitter(brightness=0.18, contrast=0.18, saturation=0.14, hue=0.03),
            transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 1.2)),
            transforms.ToTensor(),
            transforms.Normalize(mean=image_mean, std=image_std),
        ]
    )
    eval_tf = transforms.Compose(
        [
            transforms.Resize(int(image_size * 1.15)),
            transforms.CenterCrop(image_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=image_mean, std=image_std),
        ]
    )
    return train_tf, eval_tf


def compute_class_weights(targets: list[int], num_classes: int) -> torch.Tensor:
    counts = np.bincount(np.array(targets), minlength=num_classes)
    counts = np.maximum(counts, 1)
    inv = 1.0 / counts
    weights = inv / inv.sum() * num_classes
    return torch.tensor(weights, dtype=torch.float32)


def make_train_loader(
    ds: datasets.ImageFolder,
    batch_size: int,
    workers: int,
    use_weighted_sampler: bool,
):
    loader_kwargs: dict[str, Any] = {
        "batch_size": batch_size,
        "num_workers": workers,
        "pin_memory": torch.cuda.is_available(),
    }
    if workers > 0:
        loader_kwargs["persistent_workers"] = True

    if use_weighted_sampler:
        targets = ds.targets
        class_counts = np.bincount(np.array(targets))
        class_weights = 1.0 / np.maximum(class_counts, 1)
        sample_weights = [class_weights[t] for t in targets]
        sampler = WeightedRandomSampler(
            weights=torch.DoubleTensor(sample_weights),
            num_samples=len(sample_weights),
            replacement=True,
        )
        return DataLoader(ds, sampler=sampler, **loader_kwargs)
    return DataLoader(
        ds,
        shuffle=True,
        **loader_kwargs,
    )


def freeze_backbone(model: AutoModelForImageClassification, freeze: bool) -> None:
    backbone = getattr(model, model.base_model_prefix)
    for p in backbone.parameters():
        p.requires_grad = not freeze


def gather_trainable_params(model: AutoModelForImageClassification, lr_head: float, lr_backbone: float):
    backbone = getattr(model, model.base_model_prefix)
    backbone_params = [p for p in backbone.parameters() if p.requires_grad]
    classifier_params = [p for n, p in model.named_parameters() if p.requires_grad and model.base_model_prefix not in n]
    return [
        {"params": backbone_params, "lr": lr_backbone},
        {"params": classifier_params, "lr": lr_head},
    ]


def run_epoch(
    model: AutoModelForImageClassification,
    loader: DataLoader,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    train: bool,
    scaler: torch.amp.GradScaler | None,
    amp: bool,
):
    if train:
        model.train()
    else:
        model.eval()

    losses = []
    y_true: list[int] = []
    y_pred: list[int] = []

    for batch in loader:
        images, labels = batch
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)

        if train:
            optimizer.zero_grad(set_to_none=True)

        with torch.set_grad_enabled(train):
            with torch.amp.autocast("cuda", enabled=amp and device.type == "cuda"):
                logits = model(pixel_values=images).logits
                loss = criterion(logits, labels)
            if train:
                if scaler is not None and amp and device.type == "cuda":
                    scaler.scale(loss).backward()
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    loss.backward()
                    optimizer.step()

        losses.append(float(loss.item()))
        preds = logits.argmax(dim=1)
        y_true.extend(labels.detach().cpu().tolist())
        y_pred.extend(preds.detach().cpu().tolist())

    avg_loss = float(np.mean(losses)) if losses else math.inf
    cm = compute_confusion_matrix(y_true, y_pred, num_classes=model.config.num_labels)
    m = compute_metrics_from_cm(cm)
    metrics = {"loss": avg_loss, **m}
    return metrics


def evaluate_and_report(
    model: AutoModelForImageClassification,
    loader: DataLoader,
    device: torch.device,
    class_names: list[str],
    split_name: str,
    out_dir: Path,
) -> dict:
    model.eval()
    y_true: list[int] = []
    y_pred: list[int] = []

    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device, non_blocking=True)
            logits = model(pixel_values=images).logits
            preds = logits.argmax(dim=1).cpu().tolist()
            y_pred.extend(preds)
            y_true.extend(labels.tolist())

    cm = compute_confusion_matrix(y_true, y_pred, num_classes=len(class_names))
    report = build_classification_report(cm, class_names)
    m = compute_metrics_from_cm(cm)
    summary = {
        "split": split_name,
        "accuracy": m["accuracy"],
        "macro_f1": m["macro_f1"],
        "macro_precision": m["macro_precision"],
        "macro_recall": m["macro_recall"],
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
    }

    with (out_dir / f"evaluation_{split_name}.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return summary


def build_eval_loader(ds: datasets.ImageFolder, batch_size: int, workers: int) -> DataLoader:
    kwargs: dict[str, Any] = {
        "batch_size": batch_size,
        "shuffle": False,
        "num_workers": workers,
        "pin_memory": torch.cuda.is_available(),
    }
    if workers > 0:
        kwargs["persistent_workers"] = True
    return DataLoader(ds, **kwargs)


def save_best_checkpoint(
    model: AutoModelForImageClassification,
    output_dir: Path,
    payload: dict[str, Any],
) -> Path:
    best_model_dir = output_dir / "best_model"
    best_model_dir.mkdir(parents=True, exist_ok=True)

    tmp_ckpt = best_model_dir / "best_model.pt.tmp"
    final_ckpt = best_model_dir / "best_model.pt"
    tmp_ckpt.unlink(missing_ok=True)
    torch.save(payload, tmp_ckpt)
    os.replace(tmp_ckpt, final_ckpt)

    # Optional HF export; this can fail on some Windows envs due to safetensors internals.
    try:
        model.save_pretrained(best_model_dir, safe_serialization=False)
    except Exception as exc:
        print(f"warning: save_pretrained skipped due to: {exc}")
    return best_model_dir


def main() -> None:
    args = parse_args()
    set_seed(args.seed)

    dataset_root = (REPO_ROOT / args.dataset_root).resolve()
    output_dir = (REPO_ROOT / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    preprocess_obj, image_size, image_mean, image_std, preprocess_source = load_preprocess_config(
        args.model_id
    )
    print(f"preprocess_source={preprocess_source} image_size={image_size}")
    train_tf, eval_tf = build_transforms(image_size, image_mean, image_std)

    train_dir = dataset_root / "train"
    val_dir = dataset_root / "val"
    test_dir = dataset_root / "test"
    for required in (train_dir, val_dir, test_dir):
        if not required.exists():
            raise SystemExit(f"Missing dataset split directory: {required}")

    train_ds = datasets.ImageFolder(train_dir, transform=train_tf)
    val_ds = datasets.ImageFolder(val_dir, transform=eval_tf)
    test_ds = datasets.ImageFolder(test_dir, transform=eval_tf)
    class_names = train_ds.classes
    num_classes = len(class_names)
    if num_classes < 2:
        raise SystemExit("Need at least 2 classes to train classifier.")
    if len(train_ds) == 0 or len(val_ds) == 0 or len(test_ds) == 0:
        raise SystemExit("One or more dataset splits are empty.")

    if val_ds.classes != class_names or test_ds.classes != class_names:
        raise RuntimeError("Class order mismatch between train/val/test folders.")

    train_loader = make_train_loader(
        train_ds, args.batch_size, args.workers, args.use_weighted_sampler
    )
    val_loader = build_eval_loader(val_ds, args.batch_size, args.workers)
    test_loader = build_eval_loader(test_ds, args.batch_size, args.workers)

    id2label = {i: cls for i, cls in enumerate(class_names)}
    label2id = {cls: i for i, cls in id2label.items()}

    model = AutoModelForImageClassification.from_pretrained(
        args.model_id,
        num_labels=num_classes,
        ignore_mismatched_sizes=True,
        id2label=id2label,
        label2id=label2id,
    )
    device = torch.device(args.device)
    model.to(device)

    class_weights = compute_class_weights(train_ds.targets, num_classes).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=args.label_smoothing)

    freeze_backbone(model, freeze=True)
    optimizer = torch.optim.AdamW(
        gather_trainable_params(model, args.lr_head, args.lr_backbone),
        weight_decay=args.weight_decay,
    )
    scaler = torch.amp.GradScaler("cuda", enabled=args.amp and device.type == "cuda")

    history = []
    best_macro_f1 = -1.0
    best_epoch = -1
    patience = 0
    best_state_dict: dict[str, torch.Tensor] | None = None

    for epoch in range(1, args.epochs + 1):
        if epoch == args.warmup_epochs + 1:
            freeze_backbone(model, freeze=False)
            optimizer = torch.optim.AdamW(
                gather_trainable_params(model, args.lr_head, args.lr_backbone),
                weight_decay=args.weight_decay,
            )

        train_metrics = run_epoch(
            model, train_loader, criterion, optimizer, device, train=True, scaler=scaler, amp=args.amp
        )
        val_metrics = run_epoch(
            model, val_loader, criterion, optimizer, device, train=False, scaler=None, amp=False
        )
        row = {"epoch": epoch, "train": train_metrics, "val": val_metrics}
        history.append(row)

        if val_metrics["macro_f1"] > best_macro_f1:
            best_macro_f1 = val_metrics["macro_f1"]
            best_epoch = epoch
            patience = 0
            best_state_dict = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

            # Robust Windows-safe checkpoint save path (bypasses safetensors writer).
            checkpoint_payload = {
                "state_dict": best_state_dict,
                "model_id": args.model_id,
                "id2label": id2label,
                "label2id": label2id,
                "num_labels": num_classes,
                "epoch": epoch,
                "val_macro_f1": best_macro_f1,
            }
            best_model_dir = save_best_checkpoint(model, output_dir, checkpoint_payload)
            if preprocess_obj is not None and hasattr(preprocess_obj, "save_pretrained"):
                preprocess_obj.save_pretrained(best_model_dir)
            else:
                with (best_model_dir / "preprocess_fallback.json").open(
                    "w", encoding="utf-8"
                ) as f:
                    json.dump(
                        {
                            "image_size": image_size,
                            "image_mean": image_mean,
                            "image_std": image_std,
                            "source": preprocess_source,
                        },
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )
        else:
            patience += 1

        print(
            f"epoch={epoch} "
            f"train_loss={train_metrics['loss']:.4f} val_loss={val_metrics['loss']:.4f} "
            f"val_macro_f1={val_metrics['macro_f1']:.4f} best={best_macro_f1:.4f}"
        )

        if patience >= args.early_stop_patience:
            print(f"early_stop at epoch={epoch}")
            break

    if best_state_dict is None:
        raise RuntimeError("No best checkpoint state was captured during training.")
    model.load_state_dict(best_state_dict)
    best_model = model

    val_summary = evaluate_and_report(best_model, val_loader, device, class_names, "val", output_dir)
    test_summary = evaluate_and_report(best_model, test_loader, device, class_names, "test", output_dir)

    training_config = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "model_id": args.model_id,
        "dataset_root": str(dataset_root),
        "output_dir": str(output_dir),
        "class_names": class_names,
        "class_to_idx": train_ds.class_to_idx,
        "num_classes": num_classes,
        "train_size": len(train_ds),
        "val_size": len(val_ds),
        "test_size": len(test_ds),
        "args": vars(args),
        "image_size": image_size,
        "image_mean": image_mean,
        "image_std": image_std,
        "best_epoch": best_epoch,
        "best_val_macro_f1": best_macro_f1,
        "val_summary": val_summary,
        "test_summary": test_summary,
    }

    with (output_dir / "training_config.json").open("w", encoding="utf-8") as f:
        json.dump(training_config, f, ensure_ascii=False, indent=2)
    with (output_dir / "train_history.json").open("w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    with (output_dir / "label_mapping.json").open("w", encoding="utf-8") as f:
        json.dump(train_ds.class_to_idx, f, ensure_ascii=False, indent=2)

    print("training_complete")
    print(f"best_epoch={best_epoch}")
    print(f"best_val_macro_f1={best_macro_f1:.4f}")
    print(f"test_macro_f1={test_summary['macro_f1']:.4f}")
    print(f"artifacts={output_dir}")


if __name__ == "__main__":
    main()
