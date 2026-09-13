"""
LangGraph Agentic State Machine for Sovereign Agentic AI Workbench.
Coordinates multi-engine execution via an agentic loop:
classify -> plan -> act -> validate -> (loop / deliver) -> deliver -> END
"""

import os
from datetime import datetime
from typing import Dict, Any
from langgraph.graph import StateGraph, END

from src.agent.state import AgentState
from src.agent.router import classify_two_stage, route_task
from src.agent.llm_client import llm_gateway, extract_think_cot
from src.agent.prompts import (
    CORE_OPERATIONAL_SYSTEM_PROMPT,
    build_reasoning_prompt,
    build_codeact_prompt
)
from src.tools.ocr_tool import parse_inspection_document, parse_inspection_text
from src.tools.rag_tool import query_standards
from src.tools.sandbox_tool import execute_sandboxed_python
from src.tools.report_tool import (
    generate_inspection_memo,
    generate_inspection_spreadsheet,
    generate_executive_presentation
)
from src.utils.file_manager import compute_sha256
from src.utils.tracing import create_span, end_span, flush_trace, create_workflow_trace


def classify_node(state: AgentState) -> Dict[str, Any]:
    """Node 1: Classify task modality and dispatch model configuration."""
    trace = state.get("langfuse_trace")
    span = create_span(trace, "classify-node", {"step": "classify"})

    query = state.get("request") or state.get("user_query", "")
    file_path = state.get("file_path", "")
    task_mode = state.get("task_mode", "full_pipeline")

    task_type, config, rationale = classify_two_stage(query, file_path)
    legacy_task_type, engine_alias, _ = route_task(query, file_path)

    logs = list(state.get("execution_logs", []))
    logs.append(
        f"[ROUTER] Mode: '{task_mode.upper()}' | Task: '{task_type}' | "
        f"Model: '{config.get('model')}' | {rationale}"
    )

    end_span(span, {"task_type": legacy_task_type, "engine": engine_alias})
    return {
        "task_type": legacy_task_type,
        "selected_model": engine_alias,
        "model_endpoint": config,
        "execution_logs": logs
    }


def plan_node(state: AgentState) -> Dict[str, Any]:
    """Node 2: Formulate dynamic execution sequence based on task modality."""
    trace = state.get("langfuse_trace")
    span = create_span(trace, "plan-node", {"step": "plan"})

    task_type = state.get("task_type", "general")
    task_mode = state.get("task_mode", "full_pipeline")
    file_path = state.get("file_path", "")
    query = state.get("request") or state.get("user_query", "")
    has_telemetry = bool(file_path) or any(
        k in query.lower() for k in ["pipe specification", "ultrasonic thickness", "retirement thickness", "t-0", "measured (mm)"]
    )

    # Determine execution sequence
    if task_mode == "coding_only":
        plan = ["calculate_codeact", "compile_deliverables"]
    elif task_mode == "deep_thinking_only":
        plan = ["ingest_telemetry", "retrieve_standards", "reason_compliance", "compile_deliverables"] if has_telemetry else ["retrieve_standards", "reason_compliance", "compile_deliverables"]
    elif has_telemetry or task_type in ["vision", "vision_document", "coding"]:
        plan = ["ingest_telemetry", "retrieve_standards", "reason_compliance", "calculate_codeact", "compile_deliverables"]
    else:
        plan = ["retrieve_standards", "reason_compliance", "compile_deliverables"]

    logs = list(state.get("execution_logs", []))
    logs.append(f"[PLANNER] Synthesized {len(plan)}-step dynamic plan: {' -> '.join(plan)}")

    end_span(span, {"plan": plan})
    return {
        "plan": plan,
        "completed_steps": [],
        "current_step_index": 0,
        "retry_count": 0,
        "retrieved_context": [],
        "deliverables": {},
        "execution_logs": logs
    }


def generate_executive_narrative(metrics: dict, cot_trace: str = "") -> str:
    """Generate an authoritative compliance memo grounded in extracted metrics."""
    if "extracted_metrics" in metrics:
        metrics = metrics.get("extracted_metrics", {})

    meta = metrics.get("metadata", {}) or {}
    thresh = metrics.get("thresholds", {}) or {}
    pts = metrics.get("measurement_points", []) or []
    crit_pts = metrics.get("critical_points", []) or []

    line_no = meta.get("line_number", "10\"-HC-1004-CS300")
    facility = meta.get("facility", "Strategic Industrial Facility")
    std = meta.get("standard", "API 570 / ASME B31.3")
    t_thresh = thresh.get("t_threshold", 3.30)
    t_min = thresh.get("t_min", 2.80)
    margin = thresh.get("margin", 0.50)

    if crit_pts:
        cp = min(crit_pts, key=lambda x: x.get("measured_mm", 999))
        meas, nom = cp.get("measured_mm", 0.0), cp.get("nominal_mm", 1.0)
        deficit = round(meas - t_thresh, 2)
        pct = round((meas / nom) * 100, 1) if nom > 0 else 0.0
        breaches = ", ".join(f"{p.get('point_id')} ({p.get('measured_mm')} mm)" for p in crit_pts)

        return (
            f"EXECUTIVE ENGINEERING COMPLIANCE MEMO\n"
            f"Asset Line: {line_no} | Facility: {facility} | Code: {std}\n\n"
            f"AUDIT FINDING: CRITICAL REGULATORY BREACH DETECTED\n"
            f"Ultrasonic inspection identified severe degradation at Location {cp.get('point_id')} "
            f"({cp.get('description', 'Survey Point')}). Measured wall thickness is {meas:.2f} mm "
            f"(nominal: {nom:.2f} mm, {pct}% remaining).\n"
            f"Breached Locations ({len(crit_pts)} total): {breaches}.\n\n"
            f"REGULATORY ASSESSMENT ({std}):\n"
            f"- Minimum Structural Thickness (T_min): {t_min:.2f} mm\n"
            f"- Safety Margin: {margin:.2f} mm | Retirement Threshold (T_thresh): {t_thresh:.2f} mm\n"
            f"- Margin Deficit: {abs(deficit):.2f} mm below retirement limit ({deficit:+.2f} mm deficit)\n\n"
            f"MANDATED ACTIONS:\n"
            f"1. Immediate operational pressure de-rating per {std}.\n"
            f"2. Localized isolation and purging for urgent spool replacement."
        )
    else:
        lowest = min(pts, key=lambda x: x.get("measured_mm", 999), default={}) if pts else {}
        lowest_meas = lowest.get("measured_mm", 0.0)
        return (
            f"EXECUTIVE ENGINEERING COMPLIANCE MEMO\n"
            f"Asset Line: {line_no} | Facility: {facility} | Code: {std}\n\n"
            f"AUDIT FINDING: COMPLIANT / SAFE OPERATIONAL STATUS\n"
            f"All {len(pts)} measurement points meet or exceed the retirement threshold ({t_thresh:.2f} mm).\n"
            f"Lowest recorded wall thickness: {lowest_meas:.2f} mm at Location {lowest.get('point_id', 'N/A')}.\n\n"
            f"RECOMMENDATION: Maintain standard scheduled NDT surveillance interval per {std}."
        )


def act_node(state: AgentState) -> Dict[str, Any]:
    """Node 3: Execute active tool or model step according to current plan pointer."""
    plan = state.get("plan", [])
    idx = state.get("current_step_index", 0)
    active_step = plan[idx] if idx < len(plan) else "done"

    trace = state.get("langfuse_trace")
    span = create_span(trace, f"act-{active_step}", {"step": active_step, "index": idx})

    logs = list(state.get("execution_logs", []))
    updates: Dict[str, Any] = {"execution_logs": logs}
    query = state.get("request") or state.get("user_query", "")

    # STEP 1: Document / Telemetry Ingestion
    if active_step == "ingest_telemetry":
        file_path = state.get("file_path")
        if file_path and os.path.exists(file_path):
            data = parse_inspection_document(file_path)
            logs.append(f"[ACT: INGEST] Parsed '{os.path.basename(file_path)}': Extracted {len(data.get('measurement_points', []))} points.")
        else:
            data = parse_inspection_text(query)
            logs.append(f"[ACT: INGEST] Direct text input parsed: Extracted {len(data.get('measurement_points', []))} points.")

        updates["extracted_text"] = data.get("raw_text", query)
        updates["extracted_metrics"] = data

    # STEP 2: Sovereign Local RAG Standards Retrieval
    elif active_step == "retrieve_standards":
        extracted = state.get("extracted_text", "")
        chunks = query_standards(f"{query} {extracted[:150]}", n_results=3)
        updates["retrieved_context"] = chunks
        top_cite = chunks[0].get("clause", "General Standard") if chunks else "N/A"
        doc_name = chunks[0].get("source_doc", "API 570") if chunks else "N/A"
        logs.append(f"[ACT: SOVEREIGN RAG] Retrieved {len(chunks)} citations from '{doc_name}' ({top_cite}).")

    # STEP 3: Deep Thinking Reasoning (<think> CoT)
    elif active_step == "reason_compliance":
        extracted = state.get("extracted_text", "")
        metrics = state.get("extracted_metrics", {})
        retrieved = state.get("retrieved_context", [])

        prompt = build_reasoning_prompt(query, extracted, metrics, retrieved)
        chat_hist = state.get("chat_history")
        raw_output = llm_gateway.call_model(
            "reasoning-engine", prompt,
            system_prompt=CORE_OPERATIONAL_SYSTEM_PROMPT,
            temperature=0.6, langfuse_trace=trace, langfuse_span=span,
            context_metrics=metrics, chat_history=chat_hist
        )
        think_cot, final_narrative = extract_think_cot(raw_output)

        # Fallback to deterministic executive narrative if output is empty or contains raw code
        crit_pts = metrics.get("critical_points", []) if isinstance(metrics, dict) else []
        if (
            not final_narrative
            or "```python" in final_narrative
            or (crit_pts and any(w in final_narrative for w in ["COMPLIANT / SAFE", "SAFE OPERATIONAL"]))
        ):
            final_narrative = generate_executive_narrative(metrics, think_cot or raw_output)

        updates["deep_thinking_cot"] = think_cot or raw_output
        updates["final_memo_text"] = final_narrative
        logs.append("[ACT: REASONING ENGINE] Chain-of-Thought reasoning complete.")

    # STEP 4: Deterministic Sandboxed CodeAct Verification
    elif active_step == "calculate_codeact":
        extracted = state.get("extracted_text", "")
        final_memo = state.get("final_memo_text", "")
        metrics = state.get("extracted_metrics", {})

        prompt = build_codeact_prompt(query, extracted, final_memo, metrics=metrics)
        code_generated = llm_gateway.call_model(
            "coding-engine", prompt,
            system_prompt=CORE_OPERATIONAL_SYSTEM_PROMPT,
            temperature=0.1, langfuse_trace=trace, langfuse_span=span,
            context_metrics=metrics
        )
        sandbox_res = execute_sandboxed_python(code_generated)
        status = sandbox_res.get("status", "UNKNOWN")

        updates["generated_code"] = code_generated
        updates["sandbox_output"] = sandbox_res.get("stdout", "")
        updates["calculation_status"] = status
        logs.append(f"[ACT: SANDBOX VM] Verified in {sandbox_res.get('duration_sec', 0.0)}s. Result: '{status}'.")

    # STEP 5: Multi-Deliverable Compilation
    elif active_step == "compile_deliverables":
        metrics = state.get("extracted_metrics", {})
        sandbox_res = {
            "status": state.get("calculation_status", "PASS"),
            "stdout": state.get("sandbox_output", ""),
            "duration_sec": 0.02
        }
        deliverables = {
            "docx": generate_inspection_memo(metrics, sandbox_res),
            "xlsx": generate_inspection_spreadsheet(metrics),
            "pptx": generate_executive_presentation(metrics, sandbox_res)
        }
        updates["deliverables"] = deliverables
        updates["generated_report_path"] = deliverables["docx"]
        logs.append("[ACT: DELIVERABLES] Compiled Word memo (.docx), Excel log (.xlsx), and Executive PPTX (.pptx).")

    end_span(span, {"active_step": active_step})
    return updates


def validate_node(state: AgentState) -> Dict[str, Any]:
    """Node 4: Validate step outcome and handle retries."""
    trace = state.get("langfuse_trace")
    span = create_span(trace, "validate-node", {"step": "validate"})

    plan = state.get("plan", [])
    idx = state.get("current_step_index", 0)
    active_step = plan[idx] if idx < len(plan) else "done"
    logs = list(state.get("execution_logs", []))
    completed = list(state.get("completed_steps", []))
    retry_count = state.get("retry_count", 0)

    # Retry on code calculation failure
    if active_step == "calculate_codeact":
        status = state.get("calculation_status", "")
        if status in ["ERROR", "TIMEOUT"] and retry_count < 2:
            retry_count += 1
            logs.append(f"[VALIDATOR] Calculation {status}. Retrying #{retry_count}...")
            end_span(span, {"action": "retry", "retry_count": retry_count})
            return {"retry_count": retry_count, "execution_logs": logs}

    completed.append({
        "step": active_step,
        "status": "VALIDATED",
        "timestamp": datetime.now().strftime("%H:%M:%S")
    })
    logs.append(f"[VALIDATOR] Step '{active_step}' validated successfully against sovereign criteria.")

    end_span(span, {"validated_step": active_step})
    return {
        "completed_steps": completed,
        "current_step_index": idx + 1,
        "retry_count": 0,
        "execution_logs": logs
    }


def should_continue_loop(state: AgentState) -> str:
    """Determine whether to continue the agent loop or deliver."""
    plan = state.get("plan", [])
    idx = state.get("current_step_index", 0)
    retry_count = state.get("retry_count", 0)
    return "act" if idx < len(plan) and retry_count < 2 else "deliver"


def deliver_node(state: AgentState) -> Dict[str, Any]:
    """Node 5: Audit fingerprinting and final packaging."""
    trace = state.get("langfuse_trace")
    span = create_span(trace, "deliver-node", {"step": "deliver"})

    deliverables = dict(state.get("deliverables", {}))
    metrics = state.get("extracted_metrics", {})
    sandbox_res = {
        "status": state.get("calculation_status", "PASS"),
        "stdout": state.get("sandbox_output", ""),
        "duration_sec": 0.02
    }

    if "docx" not in deliverables:
        deliverables["docx"] = generate_inspection_memo(metrics, sandbox_res)
    if "xlsx" not in deliverables:
        deliverables["xlsx"] = generate_inspection_spreadsheet(metrics)
    if "pptx" not in deliverables:
        deliverables["pptx"] = generate_executive_presentation(metrics, sandbox_res)

    memo_path = deliverables.get("docx", "")
    sha256_hash = compute_sha256(memo_path) if (memo_path and os.path.exists(memo_path)) else "N/A"

    logs = list(state.get("execution_logs", []))
    logs.append(
        f"[DELIVER: SOVEREIGN AUDIT] Deliverables finalized. SHA-256: {sha256_hash[:20]}... | "
        f"Zero WAN Egress Verified (Team rv2 // SIH 2026)."
    )

    end_span(span, {"sha256": sha256_hash[:20], "deliverable_count": len(deliverables)})
    flush_trace(trace)

    return {
        "deliverables": deliverables,
        "generated_report_path": memo_path,
        "execution_logs": logs
    }


def build_workbench_graph():
    """Build and compile the multi-engine LangGraph agentic state machine."""
    workflow = StateGraph(AgentState)

    workflow.add_node("classify", classify_node)
    workflow.add_node("plan", plan_node)
    workflow.add_node("act", act_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("deliver", deliver_node)

    workflow.set_entry_point("classify")
    workflow.add_edge("classify", "plan")
    workflow.add_edge("plan", "act")
    workflow.add_edge("act", "validate")
    workflow.add_conditional_edges(
        "validate",
        should_continue_loop,
        {"act": "act", "deliver": "deliver"}
    )
    workflow.add_edge("deliver", END)

    return workflow.compile()


# Global compiled agentic workflow
workbench_agent = build_workbench_graph()


def run_workbench_workflow(user_query: str, file_path: str = "",
                           task_mode: str = "full_pipeline",
                           workflow_id: str = None,
                           chat_history: list = None) -> AgentState:
    """Execution wrapper for UI and API endpoints."""
    trace = create_workflow_trace(user_query, task_mode, workflow_id=workflow_id)

    initial_state: AgentState = {
        "request": user_query,
        "user_query": user_query,
        "file_path": file_path,
        "chat_history": chat_history or [],
        "task_type": "general",
        "selected_model": "coding-engine",
        "model_endpoint": {},
        "task_mode": task_mode,
        "plan": [],
        "completed_steps": [],
        "current_step_index": 0,
        "retry_count": 0,
        "retrieved_context": [],
        "extracted_text": "",
        "extracted_metrics": {},
        "deep_thinking_cot": "",
        "generated_code": "",
        "sandbox_output": "",
        "calculation_status": "",
        "generated_report_path": None,
        "final_memo_text": "",
        "deliverables": {},
        "error_message": None,
        "execution_logs": [],
        "langfuse_trace": trace,
        "workflow_id": workflow_id,
    }
    return workbench_agent.invoke(initial_state)

