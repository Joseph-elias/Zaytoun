# AGENTS.md — Olive Agriculture Copilot (Worker Radar)

## Project Context

You are working on a production-grade AI system called **Olive Agriculture Copilot**.

This system is part of a real application (FastAPI backend + frontend) used by:
- olive farmers,
- field workers,
- and agronomists.

The goal is NOT to build a generic chatbot.

The goal is to build the **best practical AI system for olive agriculture**, including:
1. disease diagnosis from photos,
2. multilingual agronomy Q&A (Arabic / French / English),
3. grounded recommendations using structured knowledge,
4. integration into a FastAPI production application.

---

## Core Architecture Vision

The system must follow a **multi-layer architecture**:

### Layer 1 — Multimodal AI
- Accept image + text input
- Understand olive leaves, trees, and symptoms
- Handle multilingual input/output

### Layer 2 — Olive Knowledge Layer (RAG + Tools)
- Use structured agronomy knowledge (NOT generic hallucinations)
- Includes:
  - disease guides
  - pruning calendars
  - irrigation rules
  - harvest timing
  - nutrient deficiencies
  - regional climate rules
  - internal app data (land pieces, records, labor, etc.)

### Layer 3 (optional, future) — Specialist Olive Classifier
- Predict disease shortlist:
  - healthy
  - peacock spot
  - aculus
  - fumagina
  - deficiency
  - unknown
- Used as a tool, NOT as a standalone system

---

## Critical Constraints

- NEVER hallucinate agronomy advice
- NEVER claim certainty
- ALWAYS return structured JSON (not free text)
- ALWAYS include uncertainty, alternatives, and next steps
- ALWAYS be safe and conservative
- ALWAYS support Arabic, French, and English
- ALWAYS prioritize actionable guidance for real users

---

## Expected AI Output Format

All AI responses MUST follow a structured schema like:

```json
{
  "probable_issue": "...",
  "confidence_band": "low | medium | high",
  "alternative_causes": [],
  "why_it_thinks_that": [],
  "what_to_check_next": [],
  "urgency": "low | medium | high",
  "safe_actions": [],
  "when_to_call_agronomist": "...",
  "recommended_followup_questions": [],
  "language": "...",
  "model_trace_summary": "short reasoning explanation"
}

---

## Current Project Direction (Session Notes)

We are building a **hybrid olive diagnosis pipeline**:

1. If user sends **text only**:
   - Use knowledge-grounded retrieval from `backend/data/olive_knowledge/knowledge_entries.json`.
   - Return structured JSON with safe, conservative recommendations.

2. If user sends **text + photo**:
   - Run a **leaf disease classifier** first (image model).
   - Use classifier output (top class + confidence) as additional context.
   - Combine image signal + symptom text + grounded knowledge entries.
   - Return structured JSON with uncertainty and alternatives.

Important: no free-hallucination advice. Every recommendation must be grounded in known entries/sources.

---

## Next Session Plan (Pretrained Model + Retraining)

### Phase A - Select pretrained vision model and training code

Goal: choose a model that is practical for retraining on our current dataset.

Candidate families to evaluate:
- `EfficientNet-B0/B2` (good speed/accuracy tradeoff)
- `MobileNetV3` (lightweight deployment)
- `ResNet18/34` (strong baseline, easy to train)
- Optional later: `ConvNeXt-Tiny` or `ViT-Tiny` if compute allows

Selection criteria:
- Availability of stable PyTorch code
- Simple fine-tuning workflow
- Works well for small/medium class counts
- Export/deployment feasibility for FastAPI inference

Deliverable:
- One selected baseline model + one fallback model
- Exact training script path and reproducible command

### Phase B - Prepare dataset for training

Primary dataset path:
- `backend/data/datasets/olive_unified_v1`

Expected classes currently:
- `healthy`
- `peacock_spot`
- `aculus_olearius`
- `diseased_unspecified`

Tasks:
- Verify split integrity (`train/val/test`)
- Confirm label mapping and class balance
- Define augmentation strategy (flip/rotate/color jitter/light blur)
- Document final class-to-index mapping used by model

Deliverable:
- Locked dataset config and preprocessing pipeline

### Phase C - Fine-tune and evaluate classifier

Training objectives:
- Fine-tune pretrained backbone on olive leaf classes
- Track metrics per class (precision/recall/F1 + confusion matrix)
- Save best checkpoint by validation metric

Minimum artifacts to produce:
- `best_model.pt` (or equivalent)
- training config JSON/YAML
- evaluation report (including confusion matrix)
- label mapping file (json)

### Phase D - Integrate classifier into backend hybrid flow

Integration objective:
- On image input, run classifier and inject result into diagnosis reasoning.

Expected behavior:
- High confidence class -> stronger matching boost in knowledge retrieval
- Medium/low confidence class -> weak hint only, preserve alternatives
- No/failed image inference -> fallback to text-only retrieval

Output rules:
- Keep existing structured schema
- Include classifier trace in `model_trace_summary`
- Keep conservative language and uncertainty bands

### Phase E - Safety and quality gates

Before production usage:
- Validate no overconfident claims from low-confidence image predictions
- Ensure Arabic/French/English response quality is preserved
- Verify evidence grounding is still present when image is used

---

## Immediate To-Do at Next Work Session

1. Pick pretrained baseline model and training repo/code pattern.
2. Create/confirm classifier training script for `olive_unified_v1`.
3. Train first baseline and generate eval report.
4. Decide deployment format for inference (`.pt` first, export later if needed).
5. Wire classifier output into hybrid diagnosis service.
