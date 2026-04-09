import base64
import io
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import torch
from PIL import Image
from transformers import AutoConfig, AutoFeatureExtractor, AutoImageProcessor, AutoModelForImageClassification

from backend.app.models.diagnosis import DiagnosisRequest


MODEL_CKPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "models"
    / "olive_transfer_mesabo_resnet50"
    / "best_model"
    / "best_model.pt"
)


@dataclass(frozen=True)
class ClassifierPrediction:
    label: str
    score: float
    confidence_band: str
    source: str
    top_k: list[dict[str, float | str]]
    trace: str


def _confidence_band(score: float) -> str:
    if score >= 0.80:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


def _get_image_size(preprocess_obj) -> int:
    size = getattr(preprocess_obj, "size", None)
    if isinstance(size, dict):
        if "shortest_edge" in size:
            return int(size["shortest_edge"])
        if "height" in size:
            return int(size["height"])
    if isinstance(size, int):
        return int(size)
    return 224


def _load_preprocess(model_id: str):
    defaults = {"size": 224, "mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225], "source": "fallback"}

    try:
        proc = AutoImageProcessor.from_pretrained(model_id)
        return {
            "size": _get_image_size(proc),
            "mean": list(getattr(proc, "image_mean", defaults["mean"])),
            "std": list(getattr(proc, "image_std", defaults["std"])),
            "source": "auto_image_processor",
        }
    except Exception:
        pass

    try:
        feat = AutoFeatureExtractor.from_pretrained(model_id)
        return {
            "size": _get_image_size(feat),
            "mean": list(getattr(feat, "image_mean", defaults["mean"])),
            "std": list(getattr(feat, "image_std", defaults["std"])),
            "source": "auto_feature_extractor",
        }
    except Exception:
        pass

    try:
        cfg = AutoConfig.from_pretrained(model_id)
        defaults["size"] = int(getattr(cfg, "image_size", defaults["size"]))
    except Exception:
        pass

    return defaults


@lru_cache(maxsize=1)
def _load_runtime() -> dict:
    if not MODEL_CKPT_PATH.exists():
        raise FileNotFoundError(f"Classifier checkpoint not found: {MODEL_CKPT_PATH}")

    payload = torch.load(MODEL_CKPT_PATH, map_location="cpu")
    model_id = payload.get("model_id", "mesabo/agri-plant-disease-resnet50")
    id2label = payload["id2label"]
    label2id = payload["label2id"]
    num_labels = int(payload["num_labels"])

    model = AutoModelForImageClassification.from_pretrained(
        model_id,
        num_labels=num_labels,
        ignore_mismatched_sizes=True,
        id2label=id2label,
        label2id=label2id,
    )
    model.load_state_dict(payload["state_dict"], strict=True)
    model.eval()

    preprocess_fallback = MODEL_CKPT_PATH.parent / "preprocess_fallback.json"
    if preprocess_fallback.exists():
        pconf = json.loads(preprocess_fallback.read_text(encoding="utf-8"))
    else:
        pconf = _load_preprocess(model_id)

    return {"model": model, "id2label": id2label, "preprocess": pconf}


def _image_from_base64(raw: str) -> Image.Image:
    clean = raw.split(",", 1)[1] if raw.startswith("data:") and "," in raw else raw
    decoded = base64.b64decode(clean)
    return Image.open(io.BytesIO(decoded)).convert("RGB")


def _resolve_local_image_path(payload: DiagnosisRequest) -> tuple[Path | None, str]:
    if payload.image_path:
        p = Path(payload.image_path)
        if p.exists() and p.is_file():
            return p, "image_path"

    for img_ref in payload.image_urls:
        p = Path(img_ref)
        if p.exists() and p.is_file():
            return p, "image_urls"
    return None, ""


def _preprocess_image(img: Image.Image, preprocess: dict) -> torch.Tensor:
    size = int(preprocess.get("size", 224))
    mean = torch.tensor(preprocess.get("mean", [0.485, 0.456, 0.406]), dtype=torch.float32).view(3, 1, 1)
    std = torch.tensor(preprocess.get("std", [0.229, 0.224, 0.225]), dtype=torch.float32).view(3, 1, 1)

    img = img.resize((size, size), resample=Image.BILINEAR)
    arr = torch.from_numpy(__import__("numpy").array(img)).permute(2, 0, 1).float() / 255.0
    arr = (arr - mean) / std
    return arr.unsqueeze(0)


def predict_from_request(payload: DiagnosisRequest) -> ClassifierPrediction | None:
    try:
        if payload.image_base64:
            image = _image_from_base64(payload.image_base64)
            source = "image_base64"
        else:
            resolved, source = _resolve_local_image_path(payload)
            if resolved is None:
                return None
            image = Image.open(resolved).convert("RGB")

        runtime = _load_runtime()
        model = runtime["model"]
        id2label = runtime["id2label"]
        preprocess = runtime["preprocess"]
        x = _preprocess_image(image, preprocess)

        with torch.no_grad():
            logits = model(pixel_values=x).logits
            probs = torch.softmax(logits, dim=1)[0]
            idx = int(torch.argmax(probs).item())
            score = float(probs[idx].item())
            label = str(id2label[idx])
            top_vals, top_idxs = torch.topk(probs, k=min(5, probs.shape[0]))
            top_k = [
                {"label": str(id2label[int(k.item())]), "score": float(v.item())}
                for v, k in zip(top_vals, top_idxs, strict=False)
            ]

        band = _confidence_band(score)
        trace = (
            f"classifier=olive_transfer_mesabo_resnet50; predicted={label}; "
            f"score={score:.4f}; confidence_band={band}; input_source={source}; "
            f"preprocess_source={preprocess.get('source','fallback')}."
        )
        return ClassifierPrediction(
            label=label,
            score=score,
            confidence_band=band,
            source=source,
            top_k=top_k,
            trace=trace,
        )
    except Exception as exc:
        return ClassifierPrediction(
            label="unknown",
            score=0.0,
            confidence_band="low",
            source="error",
            top_k=[],
            trace=f"classifier_error={type(exc).__name__}: {exc}",
        )
