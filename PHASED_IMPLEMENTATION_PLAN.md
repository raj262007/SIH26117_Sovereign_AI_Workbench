# Sovereign On-Premise Agentic AI Workbench: Phased Roadmap

This phased roadmap allows you to develop and validate the **entire system architecture** at high speed using cloud-hosted open-weight models (Phase 1), followed by seamlessly migrating the backend to **100% local, air-gapped quantized models** (Phase 2) for the hackathon demonstration.

---

## High-Level Phasing Strategy

```
+---------------------------------------------------------------------------------------------------+
|  APPLICATION LAYER (IDENTICAL ACROSS BOTH PHASES)                                                 |
|  • Web UI (Streamlit / Open-WebUI)                                                                |
|  • Cognitive Loop (LangGraph ReAct + Error Correction)                                            |
|  • Tool Suite (Docling OCR, Sandboxed Code Execution, python-docx Memo Generator)                |
|  • Knowledge Base (Qdrant Hybrid Vector Store)                                                    |
+---------------------------------------------------------------------------------------------------+
                                                  │
                                                  ▼
+---------------------------------------------------------------------------------------------------+
|  UNIFIED GATEWAY (LiteLLM Proxy Router)                                                           |
|  Routes tasks dynamically to "vision-model" or "coding-model" via a single config toggle          |
+---------------------------------------------------------------------------------------------------+
                                  │                                   │
              PHASE 1 (Development & Speed)                           │ PHASE 2 (Demo & Air-Gap)
                                  ▼                                   ▼
+--------------------------------------------------+  +---------------------------------------------+
| CLOUD OPEN-WEIGHT APIS                           |  | LOCAL ON-DEVICE INFERENCE                   |
| • Groq / Together AI (Free/Low-cost)             |  | • Ollama / llama.cpp (Localhost:11434)      |
| • Qwen2.5-Coder-32B                              |  | • Qwen2.5-Coder-1.5B (~1.2 GB VRAM/RAM)     |
| • Llama-3.2-11B-Vision / Qwen2.5-VL-72B          |  | • Qwen2.5-VL-3B (~2.2 GB VRAM/RAM)          |
| • Zero PC hardware strain during dev             |  | • 100% Offline with Wi-Fi Disconnected      |
+--------------------------------------------------+  +---------------------------------------------+
```

---

## Phase 1: Full-Architecture Rapid Prototyping (Cloud Open-Weight Models)

### Objectives
1. Build the complete end-to-end agentic pipeline without hardware or memory bottlenecks.
2. Establish the multi-model router, OCR/document parsing, sandboxed calculation, and Word/Excel generation.
3. Validate the complete refinery inspection scenario per the problem statement.

### Step 1.1: Environment & LiteLLM Gateway Setup
Configure LiteLLM as an OpenAI-compatible reverse proxy pointing to cloud-hosted open-weight models (e.g., via Groq, which offers free high-speed inference for open models):
* **Coding / Math Model:** `groq/qwen-2.5-coder-32b` or `groq/llama-3.3-70b-versatile`
* **Vision / Layout Model:** `groq/llama-3.2-11b-vision-preview` or `together_ai/Qwen/Qwen2.5-VL-72B-Instruct`

```yaml
# config/litellm_phase1.yaml
model_list:
  - model_name: vision-engine
    litellm_params:
      model: groq/llama-3.2-11b-vision-preview
      api_key: os.environ/GROQ_API_KEY

  - model_name: coding-engine
    litellm_params:
      model: groq/qwen-2.5-coder-32b
      api_key: os.environ/GROQ_API_KEY

  - model_name: reasoning-engine
    litellm_params:
      model: groq/deepseek-r1-distill-llama-70b
      api_key: os.environ/GROQ_API_KEY
```

### Step 1.2: Build the LangGraph Multi-Engine Agent
Construct the stateful reasoning graph:
1. **Task Classifier Node:** Inspects user input or file payload.
   * If input contains images/scans $\rightarrow$ dispatch to `vision-engine`.
   * If input requires engineering math or code $\rightarrow$ dispatch to `coding-engine`.
2. **Tool Execution Loop (ReAct / CodeAct):**
   * Tool 1: `parse_document` (uses Docling / PyMuPDF to extract tables and measurements).
   * Tool 2: `run_sandbox_code` (executes Python verification script in an isolated subprocess).
   * Tool 3: `generate_docx_memo` (formats findings into an executive `.docx` report with corporate banners).
3. **Reflection & Self-Correction Node:** If the generated Python code errors or fails unit tests, re-prompt the model to fix the syntax autonomously.

### Step 1.3: End-to-End Scenario Test (Refinery UT Piping Inspection)
Create sample input data (`Piping_UT_Scan_104.pdf` or `.png`) with tabular data:
* Measured wall thickness at Location T-12: **3.2 mm** (Nominal: 8.0 mm).
* API 570 Code Retirement Threshold: **3.3 mm** ($T_{\text{min}} = 2.8\text{ mm} + \text{Corrosion Margin } 0.5\text{ mm}$).
* Verify that the agent generates executable Python code, runs the check, detects the $-0.1\text{ mm}$ critical deficit, and automatically outputs `Refinery_Inspection_Approval_Memo.docx`.

### Step 1.4: Interactive Spreadsheet Analytics Studio (Microsoft Data Formulator)
Deploy Microsoft Data Formulator (`localhost:5567`) alongside the Workbench:
* Connect Data Formulator to LiteLLM's `coding-engine` (`qwen-2.5-coder-32b`).
* Ingest multi-point ultrasonic piping thickness measurements.
* Allow users to visually explore data, plot degradation curves across pipe coordinates, and formulate charts with natural language.

### Step 1.5: Frontend UI (Streamlit or Open-WebUI)
A clean, interactive dashboard:
* Upload area for scanned PDFs / engineering drawings.
* Live Agent Execution Drawer showing:
  * Model chosen (`vision-engine` vs `coding-engine`).
  * Step-by-step reasoning trace.
  * Code executed in sandbox with output.
* Download button for generated `.docx` / `.xlsx` deliverables and deep link to the Data Formulator studio.


---

## Phase 2: Local Sovereign Transition (100% Air-Gapped Demo)

### Objectives
1. Replace cloud API endpoints with **locally running, quantized open-weight models** using Ollama or llama.cpp.
2. Ensure the entire suite fits within standard laptop / mid-range PC specs (**under 4 GB – 6 GB total VRAM/RAM**).
3. Execute the Air-Gap Verification Protocol (physically disconnect Wi-Fi and verify zero network packets).

### Step 2.1: Local Model Selection & Installation (Via Ollama)
Download ultra-compact, high-capability quantized open-weight models:
```bash
# 1. Vision model (extracts text, tables, and visual schematics) ~2.2 GB
ollama run qwen2.5-vl:3b

# 2. Code & Math model (generates and verifies calculation scripts) ~1.2 GB
ollama run qwen2.5-coder:1.5b

# Optional: Ultra-compact reasoning model ~1.1 GB
ollama run deepseek-r1:1.5b
```

> **Resource Consumption:**
> * `qwen2.5-vl:3b` + `qwen2.5-coder:1.5b` = **~3.4 GB combined memory.**
> * Easily runs on a 4GB/6GB/8GB GPU or directly on CPU RAM with zero crashes.

### Step 2.2: LiteLLM Configuration Switch (Zero App Code Changes)
Simply point your LiteLLM configuration to your local Ollama port (`11434`):

```yaml
# config/litellm_phase2.yaml
model_list:
  - model_name: vision-engine
    litellm_params:
      model: ollama/qwen2.5-vl:3b
      api_base: http://localhost:11434

  - model_name: coding-engine
    litellm_params:
      model: ollama/qwen2.5-coder:1.5b
      api_base: http://localhost:11434

  - model_name: reasoning-engine
    litellm_params:
      model: ollama/deepseek-r1:1.5b
      api_base: http://localhost:11434
```

Because your LangGraph agent talks to LiteLLM via generic model aliases (`vision-engine`, `coding-engine`), **not a single line of your agent code needs to change!**

### Step 2.3: Offline RAG with Local Qdrant
* Configure Qdrant in offline mode with a local lightweight embedding model (`BAAI/bge-small-en-v1.5` or `all-MiniLM-L6-v2` via `fastembed` / HuggingFace offline cache).
* Index the sample API 570 piping standard and internal plant SOPs locally.

### Step 2.4: Offline Spreadsheet & Chart Studio (Microsoft Data Formulator)
* Run Data Formulator offline (`localhost:5567`) pointing directly to local Ollama (`qwen2.5-coder:1.5b` or `7b`).
* Demonstrates interactive UI-driven data wrangling and chart generation without any external internet connection.

### Step 2.5: Sovereign Proof Demonstration Protocol
On presentation day:
1. Open a terminal tab and launch the packet monitor:
   ```bash
   sudo tcpdump -i any "not host 127.0.0.1 and not port 11434 and not port 8501 and not port 5567" -v
   ```
2. **Turn off the laptop's Wi-Fi / disconnect the LAN cable in front of the jury.**
3. Ingest `Piping_UT_Scan_104.pdf` in the web UI.
4. Watch the agent:
   * Auto-select `qwen2.5-vl:3b` for OCR.
   * Auto-select `qwen2.5-coder:1.5b` for the thickness calculation in the sandbox.
   * Generate `Approval_Memo.docx` natively on the filesystem.
5. Open Data Formulator (`localhost:5567`) and explore the measurement points interactively with zero internet connection.
6. Highlight the `tcpdump` terminal: **0 packets captured outside localhost**.


---

## Comparison Summary Table

| Feature | Phase 1: Cloud Open-Source Prototyping | Phase 2: On-Premise Air-Gapped Sovereign |
| :--- | :--- | :--- |
| **Primary Goal** | Fast feature development & agent logic validation | Air-gap sovereignty compliance & demo proof |
| **Inference Location** | Cloud APIs (Groq / Together AI) | Local machine (Ollama / llama.cpp) |
| **Models Used** | Qwen2.5-Coder-32B, Llama-3.2-11B-Vision | Qwen2.5-Coder-1.5B/7B, Qwen2.5-VL-3B |
| **Local Hardware Load** | None (Runs on any machine) | ~3.5 GB – 5 GB RAM/VRAM |
| **Agent / UI Code Changes** | None (Base architecture is identical) | None (Only 1 config YAML toggle in LiteLLM) |
| **Air-Gap Compliance** | Development only | **100% Air-gapped (Wi-Fi disconnected)** |
