"""
Langfuse Observability Client for Sovereign Agentic AI Workbench.
Provides tracing of LLM calls, agent nodes, and workflow runs with nested spans.
Gracefully degrades to no-ops when Langfuse is not configured.
"""

import os
import time
from typing import Optional, Any, Dict
from dotenv import load_dotenv

load_dotenv()


def _is_langfuse_configured() -> bool:
    """Check if Langfuse credentials are present in environment."""
    return bool(os.environ.get("LANGFUSE_PUBLIC_KEY")) and bool(os.environ.get("LANGFUSE_SECRET_KEY"))


def get_langfuse():
    """
    Return a Langfuse client singleton, or None if not configured.
    Safe to call repeatedly — only initializes once.
    """
    if not _is_langfuse_configured():
        return None

    if not hasattr(get_langfuse, "_instance"):
        try:
            from langfuse import Langfuse
            get_langfuse._instance = Langfuse(
                public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
                secret_key=os.environ["LANGFUSE_SECRET_KEY"],
                host=os.environ.get("LANGFUSE_HOST", "http://localhost:3000"),
            )
        except Exception:
            get_langfuse._instance = None

    return get_langfuse._instance


def create_workflow_trace(query: str, task_mode: str = "full_pipeline",
                          workflow_id: Optional[str] = None) -> Optional[Any]:
    """
    Create a top-level Langfuse trace for an entire workflow run.
    Returns the trace object or None if Langfuse is unavailable.
    """
    client = get_langfuse()
    if client is None:
        return None

    try:
        trace = client.trace(
            name="sovereign-workbench-workflow",
            input={"query": query, "task_mode": task_mode},
            metadata={"workflow_id": workflow_id or "direct"},
            tags=["sovereign-workbench", task_mode],
        )
        return trace
    except Exception:
        return None


def create_span(trace, name: str, input_data: Optional[Dict] = None) -> Optional[Any]:
    """
    Create a child span under a trace for a LangGraph node.
    Returns (span, start_time) or (None, start_time) if tracing is unavailable.
    """
    if trace is None:
        return None

    try:
        span = trace.span(
            name=name,
            input=input_data or {},
        )
        return span
    except Exception:
        return None


def end_span(span, output_data: Optional[Dict] = None) -> None:
    """End a span with output data."""
    if span is None:
        return
    try:
        span.end(output=output_data or {})
    except Exception:
        pass


def create_generation(trace, name: str, model: str, input_text: str,
                      output_text: str, duration_ms: float = 0,
                      usage: Optional[Dict] = None,
                      parent_span=None) -> None:
    """
    Record an LLM generation (prompt → response) in Langfuse.
    Attaches to parent_span if provided, otherwise directly to the trace.
    """
    if trace is None:
        return

    parent = parent_span if parent_span else trace
    try:
        parent.generation(
            name=name,
            model=model,
            input=input_text[:4000],  # Truncate to avoid payload bloat
            output=output_text[:4000],
            metadata={"duration_ms": duration_ms},
            usage=usage or {},
        )
    except Exception:
        pass


def flush_trace(trace) -> None:
    """Flush pending trace data to Langfuse server."""
    if trace is None:
        return
    try:
        client = get_langfuse()
        if client:
            client.flush()
    except Exception:
        pass
"""Langfuse tracing utilities for the Sovereign Agentic AI Workbench."""
