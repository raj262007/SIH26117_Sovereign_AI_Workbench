"""
Core Operational Prompts & Directives for Sovereign Agentic AI Workbench.
Enforces zero-hallucination contextual grounding, dynamic document branching,
strict <think> chain-of-thought protocol, and CodeAct sandbox specifications.
"""

CORE_OPERATIONAL_SYSTEM_PROMPT = """You are the core intelligence engine of the Sovereign On-Premise Agentic AI Workbench, deployed in an air-gapped, zero-WAN industrial and defense environment.

### CORE OPERATIONAL DIRECTIVES

1. STRICT CONTEXTUAL GROUNDING (ZERO HALLUCINATION POLICY)
- Base all reasoning, summaries, and calculations exclusively on the provided "EXTRACTED DOCUMENT CONTEXT" and "USER DIRECTIVE".
- NEVER assume or inject refinery piping contexts, API 570 standards, ultrasonic thickness readings, or placeholder measurement points unless those exact elements exist within the extracted context.
- If the extracted context describes a flowchart, organizational process, software diagram, or administrative document, analyze that specific topic exclusively.
- If the document is missing critical fields or is unreadable, report the gap explicitly; never synthesize substitute metrics or fallback numbers.

2. DYNAMIC DOCUMENT CLASSIFICATION
Inspect the extracted input and classify it into one of the following branches:
- BRANCH A: Industrial NDT / Asset Inspection Logs (Piping, pressure vessels, UT survey sheets, corrosion monitoring).
  -> Analyze structural limits, remaining life, minimum retirement thickness, and regulatory compliance (e.g., API 570, ASME B31.3).
- BRANCH B: Technical Diagrams, Flowcharts & Schematics (P&IDs, agent architectures, process loops, network topologies).
  -> Analyze visual topology, step-by-step node sequences, directional arrows, system bottlenecks, and functional interfaces.
- BRANCH C: Pure Mathematical, Coding, or Advisory Queries.
  -> Solve the user's objective directly without forcing an inspection format.

3. CHAIN-OF-THOUGHT REASONING PROTOCOL (<think>)
Before issuing your final recommendations or code actions, execute a rigorous internal reasoning trace inside <think>...</think> tags:
- Step 1: Identify document modality, origin, and core subject matter.
- Step 2: Extract explicit variables, table rows, or flowchart nodes without dropping edge values.
- Step 3: Validate physical units, numeric values, and logical flows.
- Step 4: Cross-check against relevant statutory codes or logic gates only if requested or present in the text.
- Step 5: Draft the technical conclusion and outline deterministic verification scripts where math is involved.

4. CODEACT SANDBOX MATH SPECIFICATION
When numeric calculations, tolerance checks, or tabular aggregations are required:
- Never calculate floating-point margins directly in prose.
- Generate a standalone, executable Python 3 script enclosed in a ```python ... ``` block.
- The script must use only standard libraries (math, json), contain zero network requests, run deterministically, and print its final result as a structured JSON object to stdout.

5. OUTPUT DELIVERABLE FORMATTING
Structure your final response cleanly:
- Executive Classification & Modality
- Detailed Findings & Structural Analysis
- Deterministic Verification Payload (if computation is required)
- Corrective Engineering / Actionable Recommendations
"""

def build_reasoning_prompt(user_directive: str, extracted_context: str, metrics: dict, retrieved_standards: list = None) -> str:
    """Build grounded reasoning prompt for Qwen3.6-27B Deep Thinking Engine with RAG standards citations."""
    context_str = extracted_context.strip() if extracted_context else "[No document attached. Direct user advisory query.]"
    
    # Extract structured ground truth if available
    pts = metrics.get("measurement_points", []) if isinstance(metrics, dict) else []
    worst_point = min(pts, key=lambda x: x.get("measured_mm", 999), default={}) if pts else {}
    thresh = metrics.get("thresholds", {}) if isinstance(metrics, dict) else {}
    meta = metrics.get("metadata", {}) if isinstance(metrics, dict) else {}
    t_thresh = thresh.get("t_threshold")
    line_no = meta.get("line_number")
    std_name = meta.get("standard", "API 570 / ASME B31.3")

    ground_truth_section = ""
    if pts and worst_point:
        pt_summaries = ", ".join(f"{p.get('point_id')}: {p.get('measured_mm')}mm" for p in pts)
        ground_truth_section = f"""

ACTUAL VERIFIED ASSET TELEMETRY (GROUND TRUTH):
- Asset / Line Number: {line_no}
- Governing Standard: {std_name}
- Regulatory Retirement Threshold (T_thresh): {t_thresh} mm
- Critical Lowest Measured Point: {worst_point.get('point_id')} ({worst_point.get('description')}) -> Measured: {worst_point.get('measured_mm')} mm
- All Measured Survey Points: {pt_summaries}
STRICT RULE: Do NOT use example point IDs like T-12. Reference ONLY the actual verified points above (specifically {worst_point.get('point_id')})."""

    standards_section = ""
    if retrieved_standards:
        standards_lines = []
        for s in retrieved_standards:
            doc = s.get("source_doc", "Standard")
            page = s.get("page", 1)
            clause = s.get("clause", "")
            txt = s.get("text", "")[:400]
            standards_lines.append(f"[{doc} (p. {page}) - {clause}]:\n{txt}")
        standards_section = "\n\nRETRIEVED SOVEREIGN STANDARDS CONTEXT (Citations):\n\"\"\"\n" + "\n---\n".join(standards_lines) + "\n\"\"\""

    return f"""USER DIRECTIVE:
{user_directive}
{ground_truth_section}

EXTRACTED DOCUMENT CONTEXT:
\"\"\"
{context_str}
\"\"\"{standards_section}

Follow the CORE OPERATIONAL DIRECTIVES:
1. Ground all analysis strictly in the verified points and retrieved standards above. Never use placeholder IDs or numbers.
2. Perform the 5-step Chain-of-Thought inside <think>...</think>.
3. After the </think> closing tag, provide a natural-language executive engineering compliance narrative (do NOT output Python code in this reasoning step)."""


def build_codeact_prompt(user_directive: str, extracted_context: str, reasoning_summary: str, metrics: dict = None) -> str:
    """Build Python code generation prompt for Qwen3.8-27B CodeAct Engine with verified ground truth telemetry."""
    ground_truth_block = ""
    if metrics and isinstance(metrics, dict):
        meta = metrics.get("metadata", {})
        thresh = metrics.get("thresholds", {})
        pts = metrics.get("measurement_points", [])
        line_no = meta.get("line_number", "Asset Component")
        std_name = meta.get("standard", "API 570")
        t_thresh = thresh.get("t_threshold", 3.30)
        t_min = thresh.get("t_min", 2.80)
        pts_str = "\n".join(
            f"  - {p.get('point_id')}: Location '{p.get('description')}', Nominal: {p.get('nominal_mm')} mm, Measured: {p.get('measured_mm')} mm"
            for p in pts
        )
        ground_truth_block = f"""
VERIFIED GROUND TRUTH METRICS:
- Asset Line: {line_no}
- Standard: {std_name}
- Structural Minimum (T_min): {t_min} mm
- Critical Retirement Threshold (T_threshold): {t_thresh} mm
- Measurement Points:
{pts_str}
"""

    return f"""USER DIRECTIVE:
{user_directive}
{ground_truth_block}
EXTRACTED CONTEXT & REASONING:
\"\"\"
{extracted_context[:3000]}
{reasoning_summary[:2000]}
\"\"\"

TASK:
Write a standalone, executable Python 3 verification script.
- Only use standard libraries (`math`, `json`, `sys`).
- Zero network or file I/O outside current directory.
- Perform all required numerical computations, tolerance checks, or tabular aggregations deterministically.
- Compare each measured wall thickness against the Critical Retirement Threshold (T_threshold).
- If any point is below T_threshold, output:
  Status: FAIL - CRITICAL BREACH
- If all points meet or exceed T_threshold, output:
  Status: PASS - COMPLIANT
- Also print the asset line, breached locations, actual thicknesses, and deficit margins.
Return ONLY executable python code enclosed in ```python ``` blocks."""

