# AIR - GAPPED DEFENCE & PSU TECHNICAL ARCHITECTURE SPECIFICATION
## Sovereign On-Premise Agentic AI Workbench
**Architecture, Tooling Ecosystem, Multi-Engine Orchestration, and Complete Implementation Blueprint for Confidential Industrial Work Using Open-Weight Multimodal LLMs**

---

## 1. Executive Summary & Problem Statement

Refineries, Public Sector Undertakings (PSUs), defence-linked manufacturing facilities, and strategic government directorates execute mission-critical knowledge work involving high-liability engineering drawings, Piping & Instrumentation Diagrams (P&IDs), proprietary financials, and sensitive vendor negotiations. These operational records cannot egress to public commercial AI providers (such as OpenAI or Anthropic) without catastrophic security and regulatory violations. Consequently, personnel are trapped in an operational dilemma: either conduct grueling manual reviews—impeding operational agility—or succumb to "Shadow IT" by covertly pasting confidential telemetry into public models.

### Strategic Objective
Deploy a hardened, self-hosted, strictly air-gapped Agentic AI Workbench running entirely on on-premise GPU infrastructure. The platform dynamically routes heterogeneous tasks across specialized open-weight models, autonomously orchestrates multi-step reasoning with verifiable tool execution (OCR, sandboxed code execution, RAG), adheres to human-in-the-loop governance gates, and delivers real corporate deliverables (`.docx`, `.xlsx`) while providing mathematical and network proof of zero WAN egress.

---

## 2. End-to-End System Architecture

The architecture implements a multi-tier defense-in-depth model separating presentation, durable workflow orchestration, cognitive reasoning, dynamic inference routing, secure sandboxing, and offline knowledge retrieval.

```
+---------------------------------------------------------------------------------------------------+
|                                1. PRESENTATION & SECURITY LAYER                                   |
|  [Open-WebUI / LibreChat] <---> [Keycloak (LDAP/RBAC)] <---> [Microsoft Presidio (Redaction)]     |
+---------------------------------------------------------------------------------------------------+
                                                  │
                                                  ▼
+---------------------------------------------------------------------------------------------------+
|                               2. ORCHESTRATION & OBSERVABILITY PLANE                              |
|  Temporal.io Cluster: Distributed Worker Queues | Crash-Proof Workflows | Long-Lived HITL Gates    |
|  Langfuse (Self-Hosted): Zero-Telemetry OpenTelemetry Traces | Nested Spans | Audit Logs          |
+---------------------------------------------------------------------------------------------------+
                                                  │
                                                  ▼
+---------------------------------------------------------------------------------------------------+
|                                3. COGNITIVE ENGINE & GATEWAY LAYER                                |
|  LangGraph: Stateful micro-agent reasoning loop (ReAct, cyclical planning, tool reflection)       |
|  LiteLLM Proxy: Unified OpenAI-compatible gateway with dynamic task classification & dispatch     |
+---------------------------------------------------------------------------------------------------+
                                  │                                   │
              Activity: Cognitive Reasoning            Activity: Ingestion & Verification
                                  ▼                                   ▼
+--------------------------------------------------+  +---------------------------------------------+
| 4A. LOCAL INFERENCE PLANE                        |  | 4B. EXECUTION & INGESTION SUBSYSTEM         |
| • vLLM / llama.cpp (PagedAttention, AWQ/FP8)     |  | • Docling / Surya OCR: Layout & Table Parser|
| • Qwen2.5-VL-7B/32B: Visual & P&ID Inspection    |  | • gVisor (runsc): Kernel-Isolated CodeAct   |
| • Qwen2.5-Coder-14B: Engineering Calculations    |  | • Qdrant: Hybrid Dense (BGE-M3) + BM25 RAG  |
| • DeepSeek-R1-Distill-14B/32B: Policy Reasoning  |  | • python-docx / openpyxl: Document Builder  |
+--------------------------------------------------+  +---------------------------------------------+
```

### 1. Presentation & Security Layer
* **Open-WebUI / LibreChat:** Fully self-hosted interfaces providing role-based access control (RBAC), multi-tenant isolation, file upload preview, and artifact drawers.
* **Keycloak:** Internal LDAP/Active Directory SSO integration with departmental clearance tags and attribute-based access control (ABAC).
* **Microsoft Presidio:** Local CPU-based PII, classified asset tag, and clearance level redaction pipeline before prompt ingestion.

### 2. Orchestration & Observability Plane
* **Temporal.io:** Macro-orchestration providing durable execution, distributed worker queues, server-crash recovery, and zero-resource human sign-off gates.
* **Langfuse (Self-Hosted):** Zero-telemetry OpenTelemetry tracing, nested execution spans, latency auditing, and compliance scoring backed by PostgreSQL / ClickHouse.

### 3. Cognitive Engine & Gateway Layer
* **LangGraph:** Stateful micro-agent reasoning loop handling cyclical planning, tool reflection, and error recovery. Runs as an isolated Temporal activity.
* **LiteLLM Proxy:** Unified OpenAI-compatible gateway with dynamic task classification and automated model dispatch.

### 4. Execution & Ingestion Subsystems
* **vLLM / llama.cpp:** Quantized, local GPU inference serving with PagedAttention and continuous batching on local NVIDIA/AMD hardware.
* **Docling / Surya OCR:** Layout-aware visual document parsing preserving complex tables, reading order, and technical schematics.
* **gVisor (`runsc`):** Kernel-isolated container sandboxing with zero network access (`--network none`) and RAM-only `tmpfs`.
* **Qdrant:** Hybrid dense (BAAI/bge-m3) and sparse (BM25) vector database with cross-encoder reranking.
* **Office Deliverables & Visual Analytics:** Programmatic generation of native formatted `.docx`, `.xlsx`, and `.pptx` files, combined with **Microsoft Data Formulator** for interactive spreadsheet exploration and degradation curve charting.

---

## 3. Comprehensive Tooling & Infrastructure Matrix

| Subsystem | Primary Tool | Fallback / Alternative | Role in Sovereign Industrial Deployment |
| :--- | :--- | :--- | :--- |
| **Macro Orchestration** | **TEMPORAL.IO** | Hatchet / Inngest | Durable execution state across GPU OOMs and server reboots; manages asynchronous human approval gates across days without compute waste. |
| **Micro-Agent Engine** | **LANGGRAPH** | LlamaIndex Workflows | Non-deterministic prompt reasoning, tool-calling cycles, and dynamic branching. Runs as an isolated Temporal activity. |
| **Observability & Trace** | **LANGFUSE (SELF-HOSTED)** | Arize Phoenix | Self-hosted tracing with ClickHouse/PostgreSQL; provides full forensic audit logs of all prompt steps and tool outputs for compliance. |
| **Model Gateway** | **LITELLM PROXY** | vLLM Semantic Router | Dynamic prompt classification and task routing between coding, vision, and reasoning models without client code changes. |
| **Local Inference** | **vLLM (Multi-GPU)** | llama.cpp / Ollama | PagedAttention memory management, AWQ/FP8/GGUF quantization, continuous batching on local NVIDIA/AMD hardware. |
| **Document / P&ID OCR** | **DOCLING (IBM)** | Surya OCR / PaddleOCR | Layout-aware visual parsing; extracts reading order, tabular geometries, and structural captions from scanned technical drawings. |
| **Secure Sandbox** | **gVISOR (runsc)** | Docker Rootless / Firecracker | User-space virtualized kernel intercepting system calls; blocks lateral host exploits with `--network none`. |
| **Hybrid Vector DB** | **QDRANT** | Milvus / pgvector | Offline dense (`BAAI/bge-m3`) and sparse BM25 indexing with departmental metadata filtering for SOPs and plant manuals. |
| **Office Deliverables** | **PYTHON-DOCX / OPENPYXL** | python-pptx / ReportLab | Direct programmatic generation of native, formatted executive memos, calculation spreadsheets, and board slides. |
| **Visual Spreadsheet Studio** | **MICROSOFT DATA FORMULATOR** | Perspective / Marimo | Natural-language and UI-driven tabular data transformation and visualization running locally via LiteLLM/Ollama. |


---

## 4. Dual-Engine Orchestration: Temporal.io + LangGraph

Industrial operations demand strict operational resilience. Typical agent scripts fail in production because a Python runtime crash or GPU out-of-memory error destroys the in-memory execution state, forcing a total restart of long-running OCR or reasoning pipelines. This architecture pairs Temporal with LangGraph to decouple macro-level durability from micro-level reasoning:

* **Macro-Orchestration (Temporal):** Models the end-to-end industrial lifecycle as an auditable state machine. Temporal manages worker queues (dispatching OCR to high-RAM CPU nodes and LLM inference to GPU nodes), enforces activity timeouts, and executes durable Human-in-the-Loop (HITL) gates. An approval workflow can pause indefinitely for a Chief Inspector's digital signature while consuming zero active CPU or memory.
* **Micro-Agent Reasoning (LangGraph):** Operates as a discrete Temporal Activity. LangGraph governs token-by-token reasoning, prompt reflection, dynamic tool evaluation, and local error correction (e.g., re-prompting on Python syntax errors). Temporal guarantees that if the host restarts during document generation, LangGraph's finished analysis is safely reloaded from the activity cache.

---

## 5. Dynamic Model Routing & Hardware Allocation Budget

| Task Domain | Model Selected | Precision | Context Window | Target Hardware Footprint |
| :--- | :--- | :--- | :--- | :--- |
| **Visual Inspection & P&ID Parsing** | Qwen2.5-VL-7B-Instruct | Q4_K_M (GGUF) / AWQ | 8,192 tokens | ~5.5 GB VRAM / 1x RTX 4090 |
| **Engineering Code & Calculations** | Qwen2.5-Coder-14B-Instruct | Q5_K_M (GGUF) / AWQ | 16,384 tokens | ~10.2 GB VRAM / 1x RTX 4090 |
| **Complex Policy, Memos & Reasoning** | DeepSeek-R1-Distill-Qwen-14B | Q4_K_M (GGUF) / FP8 | 16,384 tokens | ~9.0 GB VRAM / 1x RTX 4090 |
| **Enterprise Rack Deployment** | Qwen2.5-VL-32B + DeepSeek-R1-32B | AWQ / FP8 Uncompressed | 32,768 tokens | 2x - 4x RTX A6000 (48GB) or A100 (80GB) |

> [!WARNING]
> **Hardware Sizing Reality Check:**
> Concurrently serving all three models (5.5 GB + 10.2 GB + 9.0 GB = 24.7 GB) exceeds a single 24GB RTX 4090 when factoring in CUDA runtime context (1.2–1.8 GB) and vLLM PagedAttention KV-cache pools. Single-workstation nodes require either:
> 1. A minimum of $2\times \text{RTX 4090}$ GPUs (48GB total), or
> 2. Sequential model eviction via `llama.cpp` with dynamic offloading, or
> 3. Consolidating onto a unified model such as `Qwen2.5-VL-7B-Instruct` or `Qwen2.5-14B`.

---

## 6. Step-by-Step Operational Scenario: Refinery Inspection & Memo Generation

```
[ Plant Engineer ] 
       │ 1. Uploads Piping_UT_Scan_104.pdf
       ▼
[ Open-WebUI / Keycloak ] 
       │ 2. Authenticates clearance, sends file to MinIO Object Storage
       ▼
[ MinIO Object Store ] <════ (Raw File Stored at s3://inspections/104.pdf)
       │
       │ 3. Triggers Workflow execution with S3 URI reference
       ▼
[ Temporal Macro-Orchestration ]
       │ 
       ├─► [ Worker 1: Ingestion Activity (CPU/High-RAM) ]
       │        • Docling extracts tables; custom regex normalizes thickness data
       │        • Writes structured JSON -> s3://inspections/104_parsed.json
       │
       ├─► [ Worker 2: LangGraph Reasoning Activity (GPU) ]
       │        • Self-RAG queries Qdrant (Dense BGE-M3 + Sparse BM25) for API 570
       │        • Formulates CodeAct Python verification script
       │        • Dispatches code to gVisor container (net: none, tmpfs: 64MB)
       │        • Sandbox returns: "FAIL - CRITICAL BREACH (-0.1mm)"
       │
       ├─► [ Temporal Human Approval Gate (Sleeping / 0 resources) ]
       │        • Emits breach alert to Chief Inspector's dashboard
       │        • Inspector audits Langfuse trace and digitally signs authorization
       │
       └─► [ Worker 3: Document Compilation Activity (CPU) ]
                • python-docx builds formatted PSU approval memo with SHA-256 audit trail
                • Final deliverable deposited to secure plant storage
```

### Detailed Execution Steps
1. **Ingestion:** A plant engineer uploads a scanned ultrasonic thickness report (`Piping_UT_Scan_104.pdf`). Docling extracts tabular thickness measurements, noting Location T-12 wall thickness is $3.2\text{ mm}$ against a nominal $8.0\text{ mm}$.
2. **Sovereign RAG Retrieval:** LangGraph invokes the Qdrant tool to query API 570 piping standards and internal refinery limits. The retriever pulls the minimum retirement threshold ($2.8\text{ mm}$) and required corrosion safety allowance ($0.5\text{ mm}$).
3. **Sandboxed Calculation:** The agent writes a verification script and dispatches it to the gVisor container sandbox:
   ```python
   T_actual = 3.2
   T_min = 2.8
   Margin = 0.5
   T_threshold = T_min + Margin  # 3.3 mm
   Status = "FAIL - CRITICAL BREACH" if T_actual < T_threshold else "PASS"
   Deficit = T_actual - T_threshold  # -0.1 mm
   print(f"Status: {Status}, Deficit: {Deficit:.2f} mm")
   ```
   The sandbox executes and returns: `FAIL - CRITICAL BREACH (Deficit: -0.10 mm)`.
4. **Human-in-the-Loop Approval Gate:** Temporal receives the breach event and triggers an approval signal, pausing the workflow. A notification appears on the Chief Inspector's dashboard. The inspector reviews the trace in Langfuse and digitally authorizes the de-rating recommendation.
5. **Artifact Generation:** LangGraph invokes the `python-docx` builder. A formal PSU approval memo is generated with executive warning banners, structured tabular findings, and regulatory citations.
6. **Visual Analytics & Chart Formulation:** The inspection team launches **Microsoft Data Formulator** (`localhost:5567`) to interactively explore multi-point thickness degradation across all points ($T\text{-01}$ to $T\text{-13}$), formulate degradation curves via natural language, and export charts for board presentations with zero WAN egress.

---


## 7. Air-Gap Sovereignty Verification Protocol

To prove sovereign compliance to defence auditors, all containers are bound to a custom bridge network stripped of default routing:
```bash
docker network create --driver bridge --internal --opt com.docker.network.bridge.enable_icc=true airgap_net
```

During live execution, an auditor executes an external packet monitor on the physical host interface:
```bash
sudo tcpdump -i eth0 -n "ip and not net 127.0.0.0/8" -c 100 -v
```
Throughout document parsing, multi-model inference, and Word file compilation, the monitor records `0 packets captured`, establishing absolute air-gap sovereignty.

---

## 8. Foundational Academic Research Literature

| Paper & Authors | Key Theoretical Contribution | Application to Sovereign Workbench |
| :--- | :--- | :--- |
| **ReAct**<br>Yao et al., ICLR 2023 (Google/Princeton) | Synergizes Chain-of-Thought reasoning with real-world tool execution (Thought → Action → Observation). | Structures the agent's iterative reasoning loops when validating refinery readings against regulatory thresholds. |
| **Self-RAG**<br>Asai et al., ICLR 2024 | Introduces self-reflection tokens to dynamically govern when retrieval is necessary and evaluate context relevance. | Eliminates hallucinated SOP citations and prevents polluting prompts with unneeded corporate manuals. |
| **PagedAttention / vLLM**<br>Kwon et al., SOSP 2023 (UC Berkeley) | Treats LLM Key-Value cache memory like OS virtual memory pages to eliminate KV fragmentation. | Enables high-throughput concurrent inference of large engineering documents on constrained GPU VRAM. |
| **CodeAct**<br>Wang et al., ICML 2024 | Proves executable Python code actions drastically outperform JSON strings for complex agentic tool calls. | Drives computational reliability by running sandboxed code for all mathematical verifications. |
| **DocLayNet**<br>Pfitzmann et al., KDD 2022 (IBM) | Introduces layout-segmented multimodal annotations for complex multi-column documents and schematics. | Forms the algorithmic basis of Docling, allowing extraction of tabular data from scanned inspection logs. |

---

## 9. Architectural Hardening Blueprint & Enterprise Enhancements

### A. The Claim-Check Pattern with Internal Object Storage (MinIO)
Temporal activity payloads must stay below 2 MB to prevent event history bloat and gRPC size exhaustion. Large engineering drawings and OCR results must never be passed directly inside workflow arguments.
* **Implementation:** Deploy an internal, air-gapped MinIO instance on `airgap_net`. Workers upload raw documents, high-res scans, and Docling JSONs to S3 buckets and pass typed URIs (`s3://bucket/key`) through Temporal.

### B. Engineering CAD & Topological Schematic Parser
DocLayNet is primarily trained on commercial/academic document layouts. P&ID diagrams contain directional flowlines, instrument bubbles, and ISA-5.1 symbols.
* **Enhancement:** Add a CAD vector extraction step (`PyMuPDF` / `pdfplumber`) to extract native line coordinates, supplemented by an offline symbol detector (YOLOv8 fine-tuned on P&ID symbols) to construct a topological graph before LLM reasoning.

### C. Industrial-Tuned Redaction Pipeline (Presidio Enhancement)
Default Presidio recognizes personal PII (SSN, credit card, phone).
* **Enhancement:** Inject custom regex and spaCy pattern recognizers for:
  * Plant Unit Codes (`CDU-1`, `FCCU-2`, `VDU-3`)
  * Equipment Tagging Schemes per KKS / ISA-5.1 (`10-MOV-104`, `PT-802`)
  * Defence Project Identifiers and Procurement Contract Codes.

### D. Day-2 Airlock & Supply Chain Attestation
* **Data Diode Ingestion:** One-way physical fiber data diode for ingesting model weights and security updates.
* **Private Mirrors:** Air-gapped Harbor registry for Docker images, private Wheel repository for Python, and offline Hugging Face directory (`HF_HUB_OFFLINE=1`).
* **SBOM Verification:** Automated Trivy / Grype scanning and Cosign signature verification on all artifacts entering the airlock.

---

## 10. Sample Air-Gapped Docker Compose Deployment Blueprint

```yaml
version: '3.8'

networks:
  airgap_net:
    driver: bridge
    internal: true # STRICT AIR-GAP: Disables outbound WAN routing
    ipam:
      config:
        - subnet: 172.28.0.0/16

volumes:
  minio_data:
  qdrant_data:
  langfuse_db:
  temporal_db:

services:
  # Internal Object Storage (Claim-Check Pattern)
  minio:
    image: minio/minio:RELEASE.2024-05-10T01-41-38Z
    container_name: airgap_minio
    networks:
      - airgap_net
    environment:
      MINIO_ROOT_USER: sovereign_admin
      MINIO_ROOT_PASSWORD: HardenedSecretPassword123!
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"

  # Hybrid Vector Database
  qdrant:
    image: qdrant/qdrant:v1.9.2
    container_name: airgap_qdrant
    networks:
      - airgap_net
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      QDRANT__SERVICE__ENABLE_STATIC_CONTENT: 0

  # Model Gateway (LiteLLM Proxy)
  litellm:
    image: ghcr.io/berriai/litellm:main-v1.35.0
    container_name: airgap_litellm
    networks:
      - airgap_net
    environment:
      - STORE_MODEL_IN_DB=False
    volumes:
      - ./config/litellm_config.yaml:/app/config.yaml
    command: ["--config", "/app/config.yaml", "--port", "4000"]

  # Local vLLM Inference Engine
  vllm_engine:
    image: vllm/vllm-openai:v0.4.2
    container_name: airgap_vllm
    networks:
      - airgap_net
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    volumes:
      - /opt/models/Qwen2.5-Coder-14B-Instruct:/model
    command: >
      --model /model
      --dtype auto
      --max-model-len 16384
      --gpu-memory-utilization 0.90
      --enforce-eager
      --port 8000

  # Temporal Macro-Orchestrator
  temporal:
    image: temporalio/auto-setup:1.23.1
    container_name: airgap_temporal
    networks:
      - airgap_net
    environment:
      - DB=postgresql
      - POSTGRES_USER=temporal
      - POSTGRES_PWD=temporal_pass
      - POSTGRES_SEEDS=temporal_db
    depends_on:
      - temporal_db

  temporal_db:
    image: postgres:15-alpine
    container_name: airgap_temporal_db
    networks:
      - airgap_net
    environment:
      - POSTGRES_USER=temporal
      - POSTGRES_PASSWORD=temporal_pass
      - POSTGRES_DB=temporal
    volumes:
      - temporal_db:/var/lib/postgresql/data

  # Self-Hosted Observability (Langfuse)
  langfuse:
    image: ghcr.io/langfuse/langfuse:2
    container_name: airgap_langfuse
    networks:
      - airgap_net
    environment:
      - DATABASE_URL=postgresql://langfuse:langfuse_pass@langfuse_db:5432/langfuse
      - NEXTAUTH_SECRET=AirgapSecretSuperKey9876543210!
      - TELEMETRY_ENABLED=false
    depends_on:
      - langfuse_db

  langfuse_db:
    image: postgres:15-alpine
    container_name: airgap_langfuse_db
    networks:
      - airgap_net
    environment:
      - POSTGRES_USER=langfuse
      - POSTGRES_PASSWORD=langfuse_pass
      - POSTGRES_DB=langfuse
    volumes:
      - langfuse_db:/var/lib/postgresql/data
```
