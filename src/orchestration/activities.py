"""
Temporal Activity definitions for the Sovereign Agentic AI Workbench.
Each activity wraps a discrete unit of work (LangGraph pipeline, deliverable compilation)
that Temporal can retry, timeout, and cache independently.
"""

from typing import Dict, Any
from temporalio import activity


@activity.defn
async def run_langgraph_pipeline(query: str, file_path: str,
                                  task_mode: str, workflow_id: str) -> Dict[str, Any]:
    """
    Execute the full LangGraph agentic state machine as a Temporal activity.
    Temporal handles retries and timeouts; the activity just calls the existing workflow.
    """
    activity.logger.info(
        f"[TEMPORAL ACTIVITY] Starting LangGraph pipeline: "
        f"query='{query[:60]}...', mode='{task_mode}', workflow_id='{workflow_id}'"
    )

    # Dynamically reload modules so long-running worker processes always execute latest code on disk
    import sys
    import importlib
    for mod_name in [
        "src.tools.ocr_tool",
        "src.agent.llm_client",
        "src.agent.prompts",
        "src.tools.sandbox_tool",
        "src.tools.report_tool",
        "src.agent.graph"
    ]:
        if mod_name in sys.modules:
            try:
                importlib.reload(sys.modules[mod_name])
            except Exception as e:
                activity.logger.warning(f"Could not reload {mod_name}: {e}")

    # Import here to avoid circular imports at module level
    from src.agent.graph import run_workbench_workflow

    # Run the existing LangGraph workflow (synchronous call inside async activity)
    result = run_workbench_workflow(
        user_query=query,
        file_path=file_path,
        task_mode=task_mode,
        workflow_id=workflow_id,
    )

    # Convert AgentState (TypedDict) to a plain serializable dict for Temporal
    serializable = _make_serializable(result)

    activity.logger.info(
        f"[TEMPORAL ACTIVITY] Pipeline complete. Status: {serializable.get('calculation_status', 'N/A')}"
    )
    return serializable


@activity.defn
async def compile_deliverables(result_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure all deliverables (.docx, .xlsx, .pptx) are generated.
    Runs as a separate activity so Temporal can retry it independently from the LLM pipeline.
    """
    activity.logger.info("[TEMPORAL ACTIVITY] Compiling final deliverables...")

    from src.tools.report_tool import (
        generate_inspection_memo,
        generate_inspection_spreadsheet,
        generate_executive_presentation
    )

    metrics = result_dict.get("extracted_metrics", {})
    sandbox_res = {
        "status": result_dict.get("calculation_status", "PASS"),
        "stdout": result_dict.get("sandbox_output", ""),
        "duration_sec": 0.02
    }

    deliverables = dict(result_dict.get("deliverables", {}))
    if "docx" not in deliverables:
        deliverables["docx"] = generate_inspection_memo(metrics, sandbox_res)
    if "xlsx" not in deliverables:
        deliverables["xlsx"] = generate_inspection_spreadsheet(metrics)
    if "pptx" not in deliverables:
        deliverables["pptx"] = generate_executive_presentation(metrics, sandbox_res)

    result_dict["deliverables"] = deliverables
    result_dict["generated_report_path"] = deliverables.get("docx", "")

    activity.logger.info(
        f"[TEMPORAL ACTIVITY] Deliverables ready: {list(deliverables.keys())}"
    )
    return result_dict


def _make_serializable(state: dict) -> dict:
    """
    Convert AgentState to a JSON-safe dict by removing non-serializable objects
    (e.g., Langfuse trace objects) and ensuring all values are primitive types.
    """
    skip_keys = {"langfuse_trace"}  # Langfuse trace objects can't be serialized
    output = {}
    for k, v in state.items():
        if k in skip_keys:
            continue
        # Convert non-serializable values to strings
        try:
            import json
            json.dumps(v)
            output[k] = v
        except (TypeError, ValueError):
            output[k] = str(v)
    return output
