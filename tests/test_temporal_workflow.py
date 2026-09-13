"""
Tests for Temporal workflow integration.
Verifies that workflow/activity definitions are importable and well-formed,
and that the server correctly falls back to direct execution when Temporal is unavailable.
"""

import unittest
import os


class TestTemporalDefinitions(unittest.TestCase):
    """Test that Temporal workflow and activity definitions are properly structured."""

    def test_activities_importable(self):
        """Activity functions can be imported without errors."""
        from src.orchestration.activities import run_langgraph_pipeline, compile_deliverables
        self.assertTrue(callable(run_langgraph_pipeline))
        self.assertTrue(callable(compile_deliverables))

    def test_workflow_importable(self):
        """InspectionWorkflow class can be imported without errors."""
        from src.orchestration.workflows import InspectionWorkflow
        self.assertTrue(hasattr(InspectionWorkflow, "run"))
        self.assertTrue(hasattr(InspectionWorkflow, "approval_signal"))
        self.assertTrue(hasattr(InspectionWorkflow, "get_status"))

    def test_retry_policy_imported_correctly(self):
        """Verify RetryPolicy is imported from temporalio.common, not temporalio.workflow."""
        from temporalio.common import RetryPolicy
        from src.orchestration.workflows import RetryPolicy as WFRetryPolicy
        self.assertIs(WFRetryPolicy, RetryPolicy)
        policy = WFRetryPolicy(maximum_attempts=2)
        self.assertEqual(policy.maximum_attempts, 2)

    def test_worker_module_importable(self):
        """Worker module can be imported without errors."""
        from src.orchestration import worker
        self.assertTrue(hasattr(worker, "start_worker"))

    def test_make_serializable_strips_trace(self):
        """_make_serializable removes non-serializable Langfuse trace objects."""
        from src.orchestration.activities import _make_serializable

        mock_state = {
            "request": "test query",
            "task_type": "coding",
            "plan": ["step1", "step2"],
            "langfuse_trace": object(),  # Non-serializable object
            "workflow_id": "test-123",
        }
        result = _make_serializable(mock_state)

        self.assertNotIn("langfuse_trace", result)
        self.assertEqual(result["request"], "test query")
        self.assertEqual(result["workflow_id"], "test-123")
        self.assertEqual(result["plan"], ["step1", "step2"])


class TestTemporalFallback(unittest.TestCase):
    """Test that the server gracefully falls back when Temporal is unavailable."""

    def test_direct_execution_fallback(self):
        """Workflow runs via direct LangGraph call when Temporal server is offline."""
        from fastapi.testclient import TestClient
        from src.server import app

        client = TestClient(app)
        res = client.post(
            "/api/run-workflow",
            data={
                "query": "Verify piping scan per API 570",
                "sample_name": "Piping_UT_Scan_104.txt",
                "task_mode": "full_pipeline"
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        # Should fall back to direct mode since Temporal is not running
        self.assertEqual(data["execution_mode"], "direct")

    def test_workflow_state_includes_new_fields(self):
        """AgentState includes the new langfuse_trace and workflow_id fields."""
        from src.agent.graph import run_workbench_workflow
        from src.utils.file_manager import INPUTS_DIR

        sample_file = os.path.join(INPUTS_DIR, "Piping_UT_Scan_104.txt")
        result = run_workbench_workflow(
            user_query="Test workflow",
            file_path=sample_file,
            task_mode="full_pipeline",
            workflow_id="test-wf-001",
        )
        # workflow_id should be preserved through the state
        self.assertEqual(result.get("workflow_id"), "test-wf-001")

    def test_approve_endpoint_returns_503_without_temporal(self):
        """HITL approval endpoint returns 503 when Temporal is not running."""
        from fastapi.testclient import TestClient
        from src.server import app

        client = TestClient(app)
        res = client.post(
            "/api/approve/fake-workflow-id",
            data={"note": "test approval"}
        )
        self.assertEqual(res.status_code, 503)

    def test_workflow_status_returns_503_without_temporal(self):
        """Workflow status endpoint returns 503 when Temporal is not running."""
        from fastapi.testclient import TestClient
        from src.server import app

        client = TestClient(app)
        res = client.get("/api/workflow-status/fake-workflow-id")
        self.assertEqual(res.status_code, 503)


if __name__ == "__main__":
    unittest.main()
