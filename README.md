# Sovereign On-Premise Agentic AI Workbench

An air-gapped, self-hosted Agentic AI Workbench designed for refineries, PSUs, defence-linked manufacturing units, and strategic government directorates to execute confidential industrial knowledge work without data egress.

---

## 🌟 Key Features

1. **Zero WAN Egress (Sovereign by Design):** Engineered to run 100% on-premise on local GPU/CPU hardware with mathematical/packet-level proof of no outbound telemetry.
2. **Multi-Model Dynamic Routing:** Automatically routes heterogeneous tasks (engineering calculations, scanned technical drawings, policy reasoning) to specialized open-weight models (`Qwen2.5-VL`, `Qwen2.5-Coder`, `DeepSeek-R1`).
3. **Deterministic Sandboxed Execution:** Mathematical verification and code actions execute inside an isolated Linux sandbox (gVisor/subprocess) to eliminate arithmetic hallucinations.
4. **Real Office Deliverables & Visual Analytics:** Directly compiles formal executive memos (`.docx`) with regulatory alert banners and calculation workbooks (`.xlsx`), supplemented by **Microsoft Data Formulator** for interactive spreadsheet exploration and degradation curve charting.
5. **Two-Phase Architecture:**
   * **Phase 1 (Development):** High-speed prototyping using cloud-hosted open-weight models (Groq / Together AI).
   * **Phase 2 (Hackathon Demo):** 100% on-device quantized models via Ollama/llama.cpp (under 4GB RAM footprint) with Wi-Fi disconnected.

---

## 🚀 Quickstart Guide

### 1. Prerequisites
* Python 3.10+
* (Optional for Phase 2) [Ollama](https://ollama.com/) for local model serving

### 2. Installation
```bash
# 1. Clone or navigate to the repository
cd sih_final

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install core dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy the example environment file:
```bash
cp .env.example .env
```
Edit `.env` and configure your API key for Phase 1 (e.g., `GROQ_API_KEY=your_key_here`).

### 4. Running the Applications
```bash
# A. Launch the Enterprise React Workbench (FastAPI backend + React frontend)
python3 src/server.py
# Opens at http://localhost:8000

# B. Launch Microsoft Data Formulator (Interactive Spreadsheet & Charting Studio)
python -m data_formulator
# Opens at http://localhost:5567
```



---

## 📂 Project Navigation

* [Architecture Specification](SOVEREIGN_AGENTIC_AI_WORKBENCH_SPEC.md): Full 8-tier technical architecture and academic foundations.
* [Phased Implementation Plan](PHASED_IMPLEMENTATION_PLAN.md): Step-by-step roadmap from cloud prototyping to air-gapped demo.
* [Project Structure Guide](PROJECT_STRUCTURE.md): Detailed module-by-module breakdown.
* [Coding Rules & Standards](AGENTS.md): Mandatory simplicity, anti-overengineering, and clean architecture rules.

---

## 🛡️ Air-Gap Sovereignty Verification

During evaluation/demonstration:
1. Launch packet capture on the physical host interface:
   ```bash
   sudo tcpdump -i any "not host 127.0.0.1 and not port 8000" -v
   ```
2. Turn off the laptop's Wi-Fi.
3. Ingest a scanned ultrasonic piping thickness report and generate the approval `.docx` memo.
4. Confirm `0 packets captured` outside localhost.
