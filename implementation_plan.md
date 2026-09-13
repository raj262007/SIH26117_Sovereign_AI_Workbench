# Implementation Plan: 100% Offline Sovereign Execution with Local Ollama Models

Strictly configure and verify that the Sovereign Agentic AI Workbench executes 100% locally and offline without external WAN or cloud dependencies. Bind the system exclusively to the two designated open-weight Ollama models:
- **Vision & Schematics Engine**: `"qwen2.5vl:3b"`
- **Analytical & Reasoning Engine**: `"qwen2.5:7b"`

---

## User Review Required

> [!IMPORTANT]
> - All cloud API keys and cloud endpoints (e.g. Groq, LiteLLM WAN calls) will be completely disabled in runtime defaults in favor of the local Ollama endpoint (`http://localhost:11434/v1`).
> - When a local model has not yet been pulled into Ollama, the system will explicitly output a local advisory notice (`[SOVEREIGN LOCAL ADVISORY: Model not yet pulled locally]`) and execute the deterministic offline rule/math engine, strictly preventing any fallback to external cloud APIs.

---

## Proposed Changes

### Model Routing & Registry Layer

#### [MODIFY] [router.py](file:///e:/Sih_final-main/src/agent/router.py)
- Update `MODEL_REGISTRY` to point all tasks to local models via `http://localhost:11434/v1`:
  - `vision_document`: `"qwen2.5vl:3b"`
  - `coding`: `"qwen2.5:7b"`
  - `document_qa`: `"qwen2.5:7b"`
  - `general_reasoning`: `"qwen2.5:7b"`
- Ensure `auto_select_model` strictly dispatches between `qwen2.5vl:3b` and `qwen2.5:7b`.
- Ensure Stage 2 fallback in `classify_two_stage` calls the local Ollama endpoint rather than any cloud service.

---

### LLM Gateway Layer

#### [MODIFY] [llm_client.py](file:///e:/Sih_final-main/src/agent/llm_client.py)
- Enforce `WORKBENCH_MODE=local` default behavior.
- Bind the two local model constants:
  - `SOVEREIGN_VISION_MODEL = "qwen2.5vl:3b"`
  - `SOVEREIGN_ANALYTICAL_MODEL = "qwen2.5:7b"`
- Update `_call_ollama` to interface with `http://localhost:11434/v1` (OpenAI-compatible) or `http://localhost:11434/api/generate` with strictly these two tags.
- Update error and fallback handling: If Ollama reports the model is not found (HTTP 404 or connection error), report clearly that the model must be pulled (`ollama pull <model>`) and proceed with the local deterministic engine instead of calling any external cloud API.

---

### Multimodal Vision & OCR Layer

#### [MODIFY] [ocr_tool.py](file:///e:/Sih_final-main/src/tools/ocr_tool.py)
- Verify that `extract_visual_telemetry` and `parse_image_with_vision_model` strictly call `"qwen2.5vl:3b"` at `http://localhost:11434/v1/chat/completions`.
- Ensure failure reporting cleanly informs the user to run `ollama pull qwen2.5vl:3b` without WAN data egress.

---

### API Server & Health Check Layer

#### [MODIFY] [server.py](file:///e:/Sih_final-main/src/server.py)
- Clean up duplicate root route definitions.
- Implement `GET /api/models-status`:
  - Queries `http://localhost:11434/api/tags`.
  - Checks presence of `"qwen2.5vl:3b"` and `"qwen2.5:7b"`.
  - Returns detailed status including installation readiness, missing models, and pull commands.
- Verify `GET /api/auto-select-model` and other endpoints reflect the local model bindings.

---

### Health-Check Verification Utility

#### [NEW] [check_models.py](file:///e:/Sih_final-main/scripts/check_models.py)
- A CLI script to probe local Ollama health and verify local availability of both `"qwen2.5vl:3b"` and `"qwen2.5:7b"`.

---

## Verification Plan

### Automated Tests
1. Run existing test suite:
   ```powershell
   python -m unittest tests/test_sovereign_workbench.py
   ```
2. Run model health-check script:
   ```powershell
   python scripts/check_models.py
   ```
3. Test new API endpoint via curl / requests:
   ```powershell
   python -c "import requests; print(requests.get('http://localhost:8000/api/models-status').json())"
   ```
4. Verify routing tests:
   ```powershell
   python -c "from src.agent.router import auto_select_model; print(auto_select_model('Evaluate P&ID schematic')); print(auto_select_model('Calculate API 570 remaining life'))"
   ```
