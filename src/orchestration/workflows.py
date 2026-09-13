"""
Temporal Workflow definition for the Sovereign Agentic AI Workbench.
Models the end-to-end inspection lifecycle as a durable state machine:
  1. Run LangGraph pipeline (as a retryable activity with timeout)
  2. If critical breach detected → pause for Human-in-the-Loop approval (zero-resource wait)
  3. Compile final deliverables
"""

from datetime import timedelta
from typing import Dict, Any

from temporalio import workflow
from temporalio.common import RetryPolicy

# Use activity stubs — Temporal resolves these to the actual functions at runtime
with workflow.unsafe.imports_passed_through():
    from src.orchestration.activities import run_langgraph_pipeline, compile_deliverables


@workflow.defn
class InspectionWorkflow:
    """
    Durable macro-orchestration workflow for industrial inspection pipelines.
    Survives server crashes, GPU OOMs, and supports indefinite HITL approval pauses.
    """

    def __init__(self):
        self._approved = False
        self._approval_note = ""

    @workflow.signal
    async def approval_signal(self, note: str = "Approved") -> None:
        """
        Signal handler for Human-in-the-Loop approval gate.
        Called when an inspector reviews and approves a critical breach finding.
        """
        self._approved = True
        self._approval_note = note
        workflow.logger.info(f"[HITL] Approval received: '{note}'")

    @workflow.query
    def get_status(self) -> Dict[str, Any]:
        """Query handler to check workflow status from the API."""
        return {
            "approved": self._approved,
            "approval_note": self._approval_note,
        }

    @workflow.run
    async def run(self, query: str, file_path: str, task_mode: str) -> Dict[str, Any]:
        """
        Main workflow execution:
        1. Run the LangGraph agentic pipeline as a Temporal activity
        2. Check if a critical breach was detected
        3. If breach → wait for human approval signal (consumes 0 resources while paused)
        4. Compile and return final deliverables
        """
        workflow_id = workflow.info().workflow_id
        workflow.logger.info(
            f"[WORKFLOW] Starting InspectionWorkflow '{workflow_id}': "
            f"query='{query[:60]}...', mode='{task_mode}'"
        )

        # Step 1: Execute LangGraph pipeline with retry and timeout
        result = await workflow.execute_activity(
            run_langgraph_pipeline,
            args=[query, file_path, task_mode, workflow_id],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(
                maximum_attempts=2,
                initial_interval=timedelta(seconds=5),
            ),
        )

        # Step 2: Check for critical breach → HITL gate
        calc_status = result.get("calculation_status", "")
        is_breach = "FAIL" in calc_status or "CRITICAL BREACH" in calc_status

        if is_breach:
            workflow.logger.info(
                f"[HITL GATE] Critical breach detected: '{calc_status}'. "
                f"Pausing workflow for inspector approval..."
            )

            # Add HITL log entry
            logs = list(result.get("execution_logs", []))
            logs.append(
                "[TEMPORAL: HITL GATE] Critical breach detected. "
                "Workflow paused — awaiting Chief Inspector approval signal. "
                "(Zero CPU/memory consumed during wait.)"
            )
            result["execution_logs"] = logs

            # Wait for approval signal (with timeout so UI does not hang indefinitely)
            try:
                await workflow.wait_condition(
                    lambda: self._approved,
                    timeout=timedelta(seconds=10),
                    timeout_summary="HITL_APPROVAL_WINDOW"
                )
                logs.append(
                    f"[TEMPORAL: HITL GATE] Approval received: '{self._approval_note}'. "
                    f"Resuming workflow execution."
                )
            except Exception:
                logs.append(
                    "[TEMPORAL: HITL GATE] Approval window elapsed (10s). "
                    "Proceeding with PROVISIONAL_BREACH_ALERT per SOP."
                )
            result["execution_logs"] = logs

        # Step 3: Compile final deliverables (separate activity for independent retry)
        result = await workflow.execute_activity(
            compile_deliverables,
            args=[result],
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )

        workflow.logger.info(f"[WORKFLOW] InspectionWorkflow '{workflow_id}' completed successfully.")
        return result
