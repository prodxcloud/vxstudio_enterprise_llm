# vxstudio_enterprise_llm

**Generic FAISS-backed SLM template. Bring your own corpus. Serve via OpenAI-compatible endpoints.**

A single Small Language Model behind FastAPI on **port 8001**. No multi-model orchestration, no DB, no task queue, no auth — just one fine-tuned causal LM, one FAISS index over your corpus, and three endpoints any OpenAI client SDK already knows how to talk to.

Drop your data in [`app/data/datasets/slm/`](app/data/datasets/slm/) (CSV / JSON / TXT), set a system prompt, run. Sample corpus is 100 customer-support Q&A rows so the template is testable out-of-the-box, but the codebase has nothing customer-support–specific in it.

## Layout

```
vxstudio_enterprise_llm/
├── app/
│   ├── app.py                              # FastAPI lifespan + /health + router include
│   ├── core/                               # logger, settings, cors (only what's needed)
│   ├── data/
│   │   └── datasets/slm/corpus.csv         # the corpus — replace with yours
│   └── services/ai/ml/
│       ├── specialist_base.py              # shared HF causal-LM load/generate
│       ├── train.py                        # shared trainer
│       ├── precompute.py                   # FAISS indexer
│       ├── embeddings.py
│       ├── cache.py
│       └── slm/
│           ├── backend.py                  # SLMBackend (subclass of SpecialistBackend)
│           ├── routes.py                   # OpenAI-compatible /v1 router
│           └── train.py                    # train entrypoint for this template's corpus
├── Dockerfile
├── requirements.txt
└── README.md
```

## Endpoints (OpenAI Chat Completions convention)

| Method | Path | Returns |
|---|---|---|
| `GET`  | `/health`              | `{status, model, model_loaded, device, corpus_dir}` — Kubernetes liveness probe |
| `GET`  | `/v1/models`           | OpenAI `model` list with one entry (the loaded SLM) |
| `POST` | `/v1/chat/completions` | OpenAI `chat.completion` response shape (non-streaming) |

**Why OpenAI-compatible:** any standard client SDK works against this server by changing `base_url`. Same contract used by [vLLM](https://docs.vllm.ai/), [Ollama](https://github.com/ollama/ollama), [LM Studio](https://lmstudio.ai/), [Text Generation Inference](https://huggingface.co/docs/text-generation-inference), and [llama.cpp's server](https://github.com/ggml-org/llama.cpp). No new client code to write.

```python
# Using the official openai Python SDK against this server
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8001/v1", api_key="not-needed")
resp = client.chat.completions.create(
    model="vxstudio-enterprise-slm",
    messages=[{"role": "user", "content": "How do I reset my password?"}],
)
print(resp.choices[0].message.content)
```

```python
# Using LangChain ChatOpenAI
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(base_url="http://localhost:8001/v1", api_key="not-needed",
                 model="vxstudio-enterprise-slm")
llm.invoke("How do I reset my password?")
```

```bash
# curl — works the same as it would against api.openai.com
curl -s http://localhost:8001/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "vxstudio-enterprise-slm",
    "messages": [{"role": "user", "content": "How do I reset my password?"}]
  }' | jq
```

## Run it

```bash
python -m venv venv
venv\Scripts\activate              # Windows  (or: source venv/bin/activate on Unix)
pip install -r requirements.txt

# First run auto-builds the FAISS index and fine-tunes against the corpus —
# can take several minutes (downloads sentence-transformers + a small base model).
python -m app.app
```

Server listens on **port 8001**.

For production:

```bash
uvicorn app.app:app --host 0.0.0.0 --port 8001 --workers 4

# Or Docker:
docker run -p 8001:8001 vxstudio_enterprise_llm:latest
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `SLM_AUTO_PRECOMPUTE` | `true` | Build FAISS index from corpus if missing |
| `SLM_AUTO_TRAIN` | `true` | Fine-tune SLM from corpus if no weights present |
| `USE_CUDA` | `false` | GPU inference (only if `torch.cuda.is_available()`) |
| `SLM_MODEL_PATH` | `app/data/models/slm` | Where trained weights are written/read |
| `SLM_DATASET_DIR` | `app/data/datasets/slm` | Where your corpus lives |
| `SLM_PRECOMPUTE_DIR` | `app/data/precompute/slm` | Where the FAISS index is persisted |
| `SLM_DISPLAY_NAME` | `vxstudio-enterprise-slm` | The `model` field returned by `/v1/models` |
| `SLM_FALLBACK_BASE_MODEL` | `distilgpt2` | HF id loaded when no fine-tuned weights exist |
| `SLM_SYSTEM_PROMPT` | *(generic)* | System prompt baked into every generation |
| `SLM_LOG_LEVEL` | `INFO` | Python logger level |

## Bringing your own corpus

The trainer reads anything under [`app/data/datasets/slm/`](app/data/datasets/slm/) by default — CSV, JSON, TXT. The "primary CSV" is `corpus.csv` and uses three columns:

```csv
question,answer,category
"How do I reset my password?","Open the login page, click Forgot password ...","account"
```

To specialise this template for a vertical (compliance, legal, healthcare, sales) you only need to:

1. Replace `corpus.csv` with your domain corpus (same column convention).
2. Set `SLM_SYSTEM_PROMPT` for the vertical's tone and constraints.
3. Set `SLM_FALLBACK_BASE_MODEL` to a larger base if `distilgpt2` is too small for your domain.
4. Optionally set `SLM_DISPLAY_NAME` so `/v1/models` returns something meaningful.

No Python edits required.

## Conventions & references

This template tries to follow the conventions you already know rather than invent new ones:

- **API shape** — [OpenAI Chat Completions](https://platform.openai.com/docs/api-reference/chat) and [Models](https://platform.openai.com/docs/api-reference/models) endpoints.
- **In-process serving pattern** — same load/generate flow as [HuggingFace Transformers](https://huggingface.co/docs/transformers/llm_tutorial) (`AutoTokenizer.from_pretrained` + `AutoModelForCausalLM.from_pretrained` + `model.generate`).
- **Retrieval** — [sentence-transformers](https://www.sbert.net/) embeddings (`all-MiniLM-L6-v2` by default) + [FAISS](https://github.com/facebookresearch/faiss) `IndexFlatIP` for cosine similarity.
- **Fine-tuning** — [HuggingFace Trainer](https://huggingface.co/docs/transformers/main_classes/trainer) over a causal-LM head, same recipe as the official [`run_clm.py`](https://github.com/huggingface/transformers/blob/main/examples/pytorch/language-modeling/run_clm.py) example.
- **Service template** — FastAPI lifespan ([docs](https://fastapi.tiangolo.com/advanced/events/)), uvicorn for ASGI ([docs](https://www.uvicorn.org/)), single-file `app.py` keeps it close to the FastAPI starter.

Compatible alternatives if you outgrow this template:

- [vLLM](https://docs.vllm.ai/) — same OpenAI-compatible API, much higher throughput.
- [Ollama](https://github.com/ollama/ollama) — same OpenAI-compatible API, local-first model management.
- [Text Generation Inference (TGI)](https://huggingface.co/docs/text-generation-inference) — same API, production-grade from HuggingFace.
- [LangChain](https://python.langchain.com/) / [LangServe](https://python.langchain.com/docs/langserve/) — agent and chain orchestration around this server.

## Pairing

This repo is the **LLM brain**. The companion [vxstudio_enterprise_agent](https://github.com/prodxcloud/vxstudio_enterprise_agent) repo is the **agent orchestrator** — a LangChain ReAct agent (Customer Onboarding + Customer Training) that calls this server's `/v1/chat/completions` as a tool.

## Lineage

Forked from [vxthinkingllm](https://github.com/prodxcloud) (the internal multi-SLM platform), then stripped to a single-model template: the four specialists, multi-model dispatcher, auth, ORM, Celery, Kafka, Redis, Web search, NLP v2 extractors, and CI configs were removed. ~35 folders/files and ~1200 lines of `app.py` deleted to get from "multi-model platform" to "one SLM behind OpenAI-compatible endpoints."
