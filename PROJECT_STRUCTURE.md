# Project Structure & Architecture Guide

This document outlines the directory structure, file responsibilities, and architectural boundaries for the **Sovereign On-Premise Agentic AI Workbench**.

---

## Directory Tree

```text
sih_final/
├── AGENTS.md                               # Permanent coding and simplicity rules for AI agents
├── PROJECT_STRUCTURE.md                    # Detailed guide to project layout and file roles (this file)
├── README.md                               # Project overview, installation, and quickstart
├── PHASED_IMPLEMENTATION_PLAN.md           # Roadmap: Phase 1 (Cloud Open Models) -> Phase 2 (Air-Gapped)
├── SOVEREIGN_AGENTIC_AI_WORKBENCH_SPEC.md  # Comprehensive technical architecture specification
├── requirements.txt                        # Python dependencies
├── .env.example                            # Template for local environment variables
├── .gitignore                              # Git ignore rules for virtual environments, outputs, and secrets
├── sync_to_notion.py                       # Automated sync utility for Notion documentation
│
├── config/                                 # Centralized system configurations
│   └── litellm_config.yaml                 # LiteLLM routing matrix (Cloud & Local Ollama)
│
├── src/                                    # Core backend application logic
│   ├── __init__.py
│   ├── agent/                              # Agent orchestration and reasoning engine
│   │   ├── __init__.py
│   │   ├── state.py                        # TypedDict schema defining agent memory and artifacts
│   │   ├── router.py                       # Task classification (Vision vs Coding vs Reasoning)
│   │   └── graph.py                        # LangGraph cyclical ReAct / CodeAct state machine
│   │
│   ├── tools/                              # Discrete, single-purpose deterministic tools
│   │   ├── __init__.py
│   │   ├── ocr_tool.py                     # Document/table extraction from scanned inspection reports
│   │   ├── sandbox_tool.py                 # Isolated Python execution for math verification
│   │   └── report_tool.py                  # Programmatic .docx and .xlsx report generator
│   │
│   ├── utils/                              # Shared helper utilities
│   │   ├── __init__.py
│   │   └── file_manager.py                 # Safe file saving, hash verification, and path resolution
│   └── server.py                           # FastAPI backend serving REST API and React frontend
│
├── static/                                 # Production-ready React Single-Page Application
│   └── index.html                          # Enterprise dark-theme React dashboard (served at :8000)
│
├── frontend/                               # Vite + React source workspace
│   ├── package.json
│   ├── vite.config.js
│   └── src/ (App.jsx, main.jsx, index.css) # Modular React components
│
├── data/                                   # Data storage (git-ignored for confidentiality)
│   ├── sample_inputs/                      # Mock industrial reports (UT scans, P&ID samples)
│   └── outputs/                            # Generated executive memos (.docx) and spreadsheets (.xlsx)
│
├── tests/                                  # Fast unit tests for tools and router
│   ├── __init__.py
│   ├── test_router.py                      # Verifies task auto-selection between models
│   └── test_tools.py                       # Verifies sandbox execution and report generation
│
└── .agents/                                # Custom agent skills and guidelines
    └── skills/
        └── clean-and-simple-code/
            └── SKILL.md                    # Simplicity, anti-overengineering, and clean structure rules
```

---

## Component Responsibilities

### 1. Configuration (`config/`)
* **`litellm_config.yaml`**: The single source of truth for model endpoints.
  * In **Phase 1**, it routes `vision-engine` and `coding-engine` to cloud-hosted open-weight models (Groq / Together AI).
  * In **Phase 2**, it redirects the exact same model aliases to `http://localhost:11434` (Ollama).
  * **Rule:** No application code outside this folder should have hardcoded model names or API URLs.

### 2. Cognitive Agent (`src/agent/`)
* **`state.py`**: Defines the `AgentState` object containing:
  * `task_type`: Visual, Coding, or Multi-step reasoning.
  * `extracted_data`: Tabular metrics extracted from inspection scans.
  * `calculation_result`: Deterministic results from the sandbox.
  * `generated_report_path`: Path to the final `.docx` or `.xlsx` file.
* **`router.py`**: Evaluates prompt/file metadata to pick the appropriate specialized model.
* **`graph.py`**: Constructs the state graph with nodes:
  * `classify_input` $\rightarrow$ `extract_document` $\rightarrow$ `run_sandboxed_math` $\rightarrow$ `generate_deliverable`.

### 3. Tool Suite (`src/tools/`)
* Every tool is a pure, independent Python module with its own input/output contract.
* **`ocr_tool.py`**: Handles PDF/image reading using PyMuPDF / Docling.
* **`sandbox_tool.py`**: Executes Python calculation code in an isolated subprocess with strict timeouts and memory caps.
* **`report_tool.py`**: Takes structured JSON and produces formal PSU memos using `python-docx`.

### 4. User Interface (`ui/`)
* **`app.py`**: Streamlit-based interface designed to clearly demonstrate:
  1. Multi-model auto-routing.
  2. Live step-by-step reasoning and sandbox code execution.
  3. One-click download of generated executive deliverables.

### 5. Interactive Spreadsheet & Visual Analytics Engine (`Microsoft Data Formulator`)
* **`data-formulator`** (`http://localhost:5567`):
  * MIT-licensed visual data exploration and transformation workbench from Microsoft Research.
  * Connects to LiteLLM / Ollama (`qwen2.5-coder`) for natural language and UI-driven tabular analysis.
  * Allows plant engineers to visually inspect multi-point ultrasonic degradation curves, run branching "what-if" data threads, and export presentation-ready charts.

### 6. Data Directory (`data/`)
* **`sample_inputs/`**: Contains reproducible test documents (e.g., `Piping_UT_Scan_104.pdf`).
* **`outputs/`**: Working directory where the agent writes `.docx` and `.xlsx` files.

