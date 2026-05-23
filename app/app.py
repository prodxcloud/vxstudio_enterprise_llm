"""
vxstudio_enterprise_llm — generic single-SLM serve.

FastAPI app exposing one fine-tuned small language model behind
OpenAI-compatible endpoints (`/v1/models`, `/v1/chat/completions`).
FAISS retrieval and HF causal-LM generation run in-process — no vLLM,
no OpenAI-compatible sidecar, no DB.

Boot order:
    1. AUTO_PRECOMPUTE: build FAISS index from app/data/datasets/slm/corpus.csv
       if app/data/precompute/slm/faiss_index.bin is missing.
    2. AUTO_TRAIN: fine-tune base model from the same corpus if
       app/data/models/slm/config.json is missing.
    3. Load model + tokenizer into the SLMBackend, bind to app.state.slm.

Endpoints follow the OpenAI Chat Completions convention so any standard
client SDK (Python `openai`, LangChain `ChatOpenAI`, curl examples) works
against this server by setting `base_url=http://host:8001/v1`.
"""

from __future__ import annotations

import os
import sys
import logging
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

import torch
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# Project root on sys.path so `python app/app.py` works as well as `python -m app.app`.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.services.ai.ml.slm import SLMBackend, build_slm_config, router as slm_router  # noqa: E402


# ── configuration ──────────────────────────────────────────────────────────

AUTO_PRECOMPUTE = os.getenv("SLM_AUTO_PRECOMPUTE", "true").lower() == "true"
AUTO_TRAIN = os.getenv("SLM_AUTO_TRAIN", "true").lower() == "true"
USE_CUDA = os.getenv("USE_CUDA", "false").lower() == "true"


# ── logging ────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=os.getenv("SLM_LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("vxstudio_enterprise_llm")


# ── boot helpers ───────────────────────────────────────────────────────────

def _bootstrap_corpus(cfg) -> None:
    """Build the FAISS index from the corpus if the index file is missing.

    Skipped silently if AUTO_PRECOMPUTE=false. Non-fatal if it fails — the
    server still boots; /v1/chat/completions just won't have retrieval
    grounding until you run the precompute step yourself.
    """
    if not AUTO_PRECOMPUTE:
        return
    index_file = cfg.precompute_dir / "faiss_index.bin"
    if index_file.exists():
        logger.info("FAISS index present at %s — skipping precompute", index_file)
        return
    cfg.precompute_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Building FAISS index from %s ...", cfg.dataset_dir)
    try:
        subprocess.check_call([
            sys.executable, "-m", "app.services.ai.ml.precompute",
            "--dataset-dir", str(cfg.dataset_dir),
            "--output-dir", str(cfg.precompute_dir),
        ])
    except subprocess.CalledProcessError as e:  # pragma: no cover
        logger.warning("Precompute failed (%s) — continuing without index", e)


def _bootstrap_training(cfg) -> None:
    """Fine-tune the SLM from the corpus if no trained weights exist.

    First-run only. After training completes, weights live at cfg.model_path
    and subsequent boots skip this. Set SLM_AUTO_TRAIN=false to disable
    auto-training (useful in production where you bake weights into the image).
    """
    if not AUTO_TRAIN:
        return
    if (cfg.model_path / "config.json").exists():
        logger.info("Trained weights present at %s — skipping training", cfg.model_path)
        return
    logger.info("No trained weights at %s — running fine-tune (this can take a while)", cfg.model_path)
    try:
        subprocess.check_call(
            [sys.executable, "-m", "app.services.ai.ml.slm.train", "--num-train-epochs", "1"]
        )
    except subprocess.CalledProcessError as e:  # pragma: no cover
        logger.warning(
            "Auto-train failed (%s) — backend will fall back to %s",
            e, cfg.fallback_base_model,
        )


# ── FastAPI lifespan ──────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    device = "cuda" if (USE_CUDA and torch.cuda.is_available()) else "cpu"
    cfg = build_slm_config(device=device)

    _bootstrap_corpus(cfg)
    _bootstrap_training(cfg)

    backend = SLMBackend(cfg)
    backend.load()
    app.state.slm = backend
    logger.info(
        "SLM ready — model=%s loaded=%s device=%s loaded_from=%s",
        cfg.display_name, backend.loaded, backend.effective_device, backend.loaded_from,
    )
    yield
    logger.info("Shutting down SLM server")


# ── app ────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="vxstudio_enterprise_llm",
    description=(
        "Generic FAISS-backed SLM template. OpenAI-compatible endpoints "
        "(/v1/models, /v1/chat/completions) over a single fine-tuned causal LM."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(slm_router)


@app.get("/health")
async def health(req: Request) -> dict:
    backend = getattr(req.app.state, "slm", None)
    if backend is None:
        return {"status": "starting", "model_loaded": False}
    return {
        "status": "ok" if backend.loaded else "degraded",
        "model": backend.cfg.display_name,
        "model_loaded": backend.loaded,
        "loaded_from": backend.loaded_from,
        "device": backend.effective_device,
        "corpus_dir": str(backend.cfg.dataset_dir),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
