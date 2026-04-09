# Olive Agriculture Copilot (Worker Radar)

An end-to-end AI system for olive agriculture that combines:
- a transfer-learned leaf classifier,
- a grounded agronomy knowledge layer,
- and an LLM-powered multilingual chat experience.

This project was built as a practical field tool, not a generic chatbot.  
Target users are farmers, technicians, and agronomists who need actionable, safe, and transparent guidance.

## Version Scope

This release is Version 1 (V1).

- V1 classification scope: olive tree and olive leaf disease/pest classes.
- Additional project data exists for soil-related context, but soil classification is out of scope for V1.
- Soil intelligence is planned for future versions as an extended module.

---

## Why This Project Is Special

Most demos stop at "a model predicts a class."  
This system goes further:

1. It classifies olive leaf images with a tuned transfer-learning pipeline.
2. It grounds explanations in curated olive knowledge with source attribution.
3. It uses an ontology-driven bridge between model classes and agronomy concepts.
4. It applies confidence gating and selective routing to reduce risky overconfident decisions.
5. It delivers everything through a production-style API and chat UI.

In short: vision + knowledge + safe decision logic + multilingual UX.

---

## Project Story

Built a production-oriented Olive Agriculture Copilot that transforms raw model predictions into grounded, user-ready agronomy decisions.

- Started from fragmented data and unified it into a clean 7-class olive dataset.
- Fine-tuned a pretrained plant disease model and reached strong validation/test performance.
- Designed a hybrid pipeline where image understanding is connected to verified domain knowledge.
- Added ontology policies and selective confidence gating so the system behaves safely under uncertainty.
- Delivered a reusable chat interface that supports photo upload + multilingual advice with traceability.

The result is a practical "AI copilot" architecture ready to be integrated into real agriculture applications.

---

## Dataset Collection and Preparation

Unified dataset location:
- `backend/data/datasets/olive_unified_v1`

Final class distribution:
- `healthy`: 1589
- `peacock_spot`: 2460
- `aculus_olearius`: 882
- `anthracnose`: 530
- `blackscale`: 583
- `psyllid`: 478
- `tuberculosis`: 627

Total:
- `7149` labeled images

Data work included:
- merge and harmonization of multiple sources,
- class normalization and cleanup,
- manifest/split hygiene checks,
- and removal of ambiguous "unspecified" labels.

---

## Transfer Learning Pipeline

Base checkpoint:
- `mesabo/agri-plant-disease-resnet50` (Hugging Face)

Training scripts:
- `scripts/train_olive_transfer.py`
- `scripts/run_transfer_training.py`

Common commands:

```bash
python scripts/run_transfer_training.py count
python scripts/run_transfer_training.py smoke
python scripts/run_transfer_training.py full --full-epochs 12 --full-workers 0
python scripts/run_transfer_training.py list-full
```

Artifacts:
- `backend/models/olive_transfer_mesabo_resnet50/`
- `backend/models/olive_transfer_mesabo_resnet50/best_model/best_model.pt`
- `backend/models/olive_transfer_mesabo_resnet50/evaluation_test.json`

Latest reported result snapshot:
- best validation macro-F1: `0.8746`
- test macro-F1: `0.8460`
- test accuracy: `0.8815`

---

## Hybrid Diagnosis Setup (Current Production Logic)

### 1) Classifier-first with ontology mapping
When an image is provided, the model predicts leaf class + confidence.

Then the system maps model labels (for example `tuberculosis`, `blackscale`) to agronomy knowledge entries through ontology rules.

### 2) Confidence-aware routing
- High-confidence healthy signal routes to a conservative healthy/monitoring response.
- Confident disease/pest signal routes directly to matched knowledge entries.
- Low-confidence or uncertain signal triggers fallback logic.

### 3) LLM fallback for ambiguous photos
If prediction is uncertain:
- LLM first describes visible leaf patterns,
- system retrieves similar disease descriptions from knowledge entries,
- final answer stays structured and grounded.

### 4) Transparent debug output
API response includes `classifier_debug`:
- predicted label
- gated label
- score
- margin (top1-top2)
- top-k classes
- trace

This makes debugging and threshold tuning straightforward.

---

## Why Ontology Was Added (Key Innovation)

Ontology is the control layer that aligns AI components:

- Consistency: classifier labels and knowledge terminology stay synchronized.
- Configurability: thresholds and mappings are data-driven (JSON), not hardcoded.
- Safety: routing policies are explicit and auditable.
- Multilingual clarity: display names are normalized for `en/fr/ar`.

Core file:
- `backend/data/olive_knowledge/ontology.json`

Knowledge files:
- `backend/data/olive_knowledge/knowledge_entries.json`
- `backend/data/olive_knowledge/sources.json`

---

## Why Confidence Gating Was Added (Key Innovation)

Confidence gating reduces false-positive cascades in hybrid systems.

Instead of blindly trusting top-1 class, the system checks:
- confidence score,
- top1-top2 separation margin,
- policy thresholds from ontology.

This follows selective prediction / reject-option principles:
- Geifman and El-Yaniv (2019), SelectiveNet (ICML): https://proceedings.mlr.press/v97/geifman19a.html
- Geifman and El-Yaniv (2017), Selective Classification for DNNs: https://arxiv.org/abs/1705.08500

In practice, this prevents brittle behavior like over-committing to a disease when signal is weak or ambiguous.

---

## LLM Integration

LLM is used as a controlled reasoning layer, not a free generator:

- model configured via `.env` (default: `gpt-4.1-mini`)
- grounded generation from retrieved knowledge context
- image-description fallback when classifier confidence is low
- strict structured response schema

Environment variables:

```env
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4.1-mini
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_TIMEOUT_SECONDS=45
CORS_ORIGINS=https://your-frontend.com,https://staging-frontend.com
INTERNAL_API_KEY=shared-secret-with-zaytoun-backend
```

---

## API Surface

- `POST /api/v1/chat` -> primary hybrid chat endpoint (text + optional image)
- `POST /api/v1/diagnose` -> diagnosis endpoint
- `GET /api/v1/knowledge/sources` -> source registry
- `GET /health` -> health check

If `frontend/` exists:
- `/` redirects to `/ui`
- `/ui` serves the chat widget

---

## Frontend Chat Widget

Files:
- `frontend/index.html`
- `frontend/olive-chat-widget.js`
- `frontend/olive-chat-widget.css`

Capabilities:
- chat-style UX
- optional leaf photo upload (base64)
- response rendering with safety + trace context
- configurable API base URL and headers for integration into existing apps

Embed pattern:

```html
<div id="olive-chat-root"></div>
<script type="module">
  import { mountOliveChatWidget } from "/ui/olive-chat-widget.js";
  mountOliveChatWidget("#olive-chat-root", {
    apiBaseUrl: "https://your-backend-domain.com",
    endpointPath: "/api/v1/chat",
    language: "en",
    requestHeaders: {
      Authorization: "Bearer <your-app-token>"
    }
  });
</script>
```

---

## Quick Start

```bash
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
python -m uvicorn backend.app.main:app --reload
```

Open:
- API docs: `http://127.0.0.1:8000/docs`
- Chat UI: `http://127.0.0.1:8000/ui`

---

## Knowledge/Ontology Quality Checks

Validation script:
- `scripts/validate_knowledge_integrity.py`

Checks include:
- source references integrity,
- ontology field validity,
- classifier label mapping integrity,
- classifier policy range checks.

Run:

```bash
python scripts/validate_knowledge_integrity.py
```

---

## Final Note

This repository demonstrates a practical pattern for high-stakes domain AI:
predict -> map -> ground -> gate -> explain.

That architecture is what turns a strong model into a reliable copilot.
