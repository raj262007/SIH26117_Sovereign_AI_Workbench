"""
Temporal Worker for the Sovereign Agentic AI Workbench.
Connects to the Temporal server, registers workflows and activities,
and processes tasks from the 'sovereign-workbench' task queue.

Usage:
    python3 -m src.orchestration.worker
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

load_dotenv()

# Ensure workspace root is in sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


async def start_worker():
    """Connect to Temporal and start processing workflow tasks."""
    from temporalio.client import Client
    from temporalio.worker import Worker
    from src.orchestration.workflows import InspectionWorkflow
    from src.orchestration.activities import run_langgraph_pipeline, compile_deliverables

    temporal_host = os.environ.get("TEMPORAL_HOST", "localhost:7233")
    task_queue = os.environ.get("TEMPORAL_TASK_QUEUE", "sovereign-workbench")

    print(f"[WORKER] Connecting to Temporal at '{temporal_host}'...")
    client = await Client.connect(temporal_host)

    print(f"[WORKER] Starting worker on task queue '{task_queue}'...")
    print(f"[WORKER] Registered workflow: InspectionWorkflow")
    print(f"[WORKER] Registered activities: run_langgraph_pipeline, compile_deliverables")

    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[InspectionWorkflow],
        activities=[run_langgraph_pipeline, compile_deliverables],
    )
    await worker.run()


if __name__ == "__main__":
    print("[WORKER] Sovereign Agentic AI Workbench — Temporal Worker")
    print("[WORKER] Press Ctrl+C to stop.")
    asyncio.run(start_worker())
