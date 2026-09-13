"""
Unit tests for FastAPI Backend and React Serving Endpoints.
"""

import unittest
from fastapi.testclient import TestClient
from src.server import app

class TestServerAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_endpoint(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "online")
        self.assertEqual(data["airgap_status"], "SECURE")

    def test_samples_endpoint(self):
        res = self.client.get("/api/samples")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Piping_UT_Scan_104.txt", res.json()["samples"])

    def test_react_root_serving(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Sovereign On-Premise Agentic AI Workbench", res.text)
        self.assertIn('id="root"', res.text)

    def test_run_workflow_endpoint(self):
        res = self.client.post(
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
        self.assertEqual(data["task_mode"], "full_pipeline")
        self.assertEqual(data["status"], "FAIL - CRITICAL BREACH")
        self.assertTrue(data["docx_download_url"].startswith("/api/download/"))

    def test_run_workflow_modes(self):
        # Test deep_thinking_only mode
        res = self.client.post(
            "/api/run-workflow",
            data={
                "query": "Reason through failure modes under API 570",
                "sample_name": "Piping_UT_Scan_104.txt",
                "task_mode": "deep_thinking_only"
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
    def test_upload_file_endpoint(self):
        file_content = b"Report ID: TEST-999\nPoint ID: T-12 Measured: 3.20"
        res = self.client.post(
            "/api/upload-file",
            files={"file": ("test_upload.txt", file_content, "text/plain")}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["filename"], "test_upload.txt")
        self.assertIn("TEST-999", data["preview"])

    def test_run_workflow_with_raw_text(self):
        sample_text = """Report ID: UT-CUSTOM-TEST
Line Number: 06"-CW-1010
Applicable Standard: API 570
Critical Retirement Threshold: 3.30
T-05 Heat Exchanger Inlet 8.00 3.10 ACTION REQ"""
        res = self.client.post(
            "/api/run-workflow",
            data={
                "query": "Verify custom scan",
                "raw_text": sample_text,
                "task_mode": "full_pipeline"
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["status"], "FAIL - CRITICAL BREACH")
        self.assertIn("pptx_download_url", data)
        self.assertIn("plan", data)
        self.assertIn("completed_steps", data)
        self.assertIn("retrieved_context", data)

    def test_network_egress_endpoint(self):
        res = self.client.get("/api/network-egress")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "AIR_GAPPED_VERIFIED")
        self.assertEqual(data["egress_bytes"], 0)
        self.assertEqual(data["wan_bytes_out"], 0)
        self.assertTrue(data["zero_wan_egress"])
        self.assertEqual(data["team"], "rv2")

    def test_rag_search_endpoint(self):
        res = self.client.get("/api/rag/search?query=API+570+retirement+thickness")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(data["count"], 1)
        first = data["results"][0]
        self.assertIn("clause", first)
        self.assertIn("source_doc", first)

    def test_chat_memory_multi_turn(self):
        """Test multi-turn conversation memory with chat_history."""
        import json
        # Turn 1: User introduces asset tag
        history = [
            {"role": "user", "content": "I am inspecting line 12-RG-3301 today."},
            {"role": "assistant", "content": "Understood. Line 12-RG-3301 is recorded for inspection."}
        ]
        # Turn 2: User asks to recall which line was discussed
        res = self.client.post(
            "/api/run-workflow",
            data={
                "query": "What line did I say I was inspecting earlier?",
                "chat_history": json.dumps(history)
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["is_general_chat"])
        self.assertIn("12-RG-3301", data["reasoning_summary"])

if __name__ == "__main__":
    unittest.main()

