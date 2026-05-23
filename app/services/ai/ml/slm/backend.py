"""
SLMBackend — generic single-model SLM backend.

Thin subclass of `SpecialistBackend` configured for one corpus. Swap the
dataset under `app/data/datasets/slm/` and the model behaves accordingly —
the class itself is topic-agnostic.

Default system prompt is intentionally neutral. Override via env var
`SLM_SYSTEM_PROMPT` or by editing this file when you specialise the template
for a vertical (compliance, legal, customer-support, etc.).
"""

from __future__ import annotations

import os

try:
    from ..specialist_base import (
        SpecialistBackend,
        SpecialistConfig,
        resolve_model_path,
        resolve_dataset_dir,
    )
except ImportError:
    from app.services.ai.ml.specialist_base import (
        SpecialistBackend,
        SpecialistConfig,
        resolve_model_path,
        resolve_dataset_dir,
    )


DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant grounded in a private knowledge base. "
    "Answer the user's question using ONLY the retrieved context below when "
    "relevant. If the context does not contain the answer, say so plainly "
    "rather than guessing. Quote source titles when you cite a fact."
)


def build_slm_config(device: str = "cuda") -> SpecialistConfig:
    return SpecialistConfig(
        slug="slm",
        display_name=os.getenv("SLM_DISPLAY_NAME", "vxstudio-enterprise-slm"),
        model_path=resolve_model_path(
            "SLM_MODEL_PATH",
            "app/data/models/slm",
        ),
        dataset_dir=resolve_dataset_dir(
            "SLM_DATASET_DIR",
            "app/data/datasets/slm",
        ),
        precompute_dir=resolve_dataset_dir(
            "SLM_PRECOMPUTE_DIR",
            "app/data/precompute/slm",
        ),
        # distilgpt2 (~82M) is a safety-net base model used only when the
        # fine-tuned weights at `model_path` are missing. Override with
        # SLM_FALLBACK_BASE_MODEL to pick a larger HF causal LM
        # (e.g. Qwen/Qwen2.5-0.5B, TinyLlama/TinyLlama-1.1B-Chat-v1.0).
        fallback_base_model=os.getenv("SLM_FALLBACK_BASE_MODEL", "distilgpt2"),
        system_prompt=os.getenv("SLM_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT),
        device=device,
        prefix="/v1",
    )


class SLMBackend(SpecialistBackend):
    pass
