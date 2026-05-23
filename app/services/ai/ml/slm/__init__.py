"""Single SLM backend — FAISS-retrieval + HF causal LM, served via OpenAI-compatible routes."""
from .backend import SLMBackend, build_slm_config  # noqa: F401
from .routes import router  # noqa: F401
