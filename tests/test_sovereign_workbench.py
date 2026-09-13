"""
Comprehensive unit tests for the Sovereign Industrial AI Workbench:
1. Dynamic Model Router (auto_select_model): qwen2.5vl:3b vs qwen2.5:7b.
2. Local Ollama Vision Telemetry Tool (extract_visual_telemetry & strip_json_fences).
3. Real-time Air-Gap Network Monitor (get_airgap_status).
4. FastAPI sovereign API endpoints (/api/airgap-status, /api/auto-select-model).
"""

import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.agent.router import (
    auto_select_model,
    SOVEREIGN_VISION_MODEL,
    SOVEREIGN_ANALYTICAL_MODEL
)
from src.tools.ocr_tool import strip_json_fences, extract_visual_telemetry
from src.utils.airgap_monitor import get_airgap_status
from src.server import app


class TestSovereignModelRouter(unittest.TestCase):
    """Test suite for autonomous model selection without UI dropdowns."""

    def test_image_extension_routes_to_vision_model(self):
        result = auto_select_model("Inspect this pipe", "scan_report.png")
        self.assertEqual(result["selected_model"], SOVEREIGN_VISION_MODEL)
        self.assertEqual(result["task_type"], "MULTIMODAL_VISION")
        self.assertIn("routing_reason", result)

    def test_jpg_extension_routes_to_vision_model(self):
        result = auto_select_model("Review drawing", "piping_schematic.jpg")
        self.assertEqual(result["selected_model"], SOVEREIGN_VISION_MODEL)
        self.assertEqual(result["task_type"], "MULTIMODAL_VISION")

    def test_base64_payload_routes_to_vision_model(self):
        result = auto_select_model("Check this", "data:image/png;base64,iVBORw0KGgo...")
        self.assertEqual(result["selected_model"], SOVEREIGN_VISION_MODEL)
        self.assertEqual(result["task_type"], "MULTIMODAL_VISION")

    def test_pid_and_schematic_keywords_route_to_vision_model(self):
        prompts = [
            "Analyze the scanned P&ID drawing and extract valve tags",
            "Evaluate this schematic for pressure safety valves",
            "Examine this blueprint for pipe schedule",
            "Review corrosion photo on asset 10-HC-1004"
        ]
        for p in prompts:
            res = auto_select_model(p)
            self.assertEqual(res["selected_model"], SOVEREIGN_VISION_MODEL, f"Failed on prompt: {p}")
            self.assertEqual(res["task_type"], "MULTIMODAL_VISION")

    def test_analytical_keywords_route_to_analytical_model(self):
        prompts = [
            "Calculate the piping retirement thickness using Python formula",
            "Execute python script to verify API 570 corrosion deficit",
            "Audit compliance against API 570 SOP clauses",
            "Draft executive approval memo for chief inspector"
        ]
        for p in prompts:
            res = auto_select_model(p)
            self.assertEqual(res["selected_model"], SOVEREIGN_ANALYTICAL_MODEL, f"Failed on prompt: {p}")
            self.assertEqual(res["task_type"], "ANALYTICAL_REASONING")

    def test_code_file_payload_routes_to_analytical_model(self):
        result = auto_select_model("Verify integrity math", "calc_corrosion.py")
        self.assertEqual(result["selected_model"], SOVEREIGN_ANALYTICAL_MODEL)
        self.assertEqual(result["task_type"], "ANALYTICAL_REASONING")

    def test_router_returns_expected_contract(self):
        result = auto_select_model("General evaluation")
        self.assertIsInstance(result, dict)
        self.assertIn("selected_model", result)
        self.assertIn("task_type", result)
        self.assertIn("routing_reason", result)


class TestOllamaVisionTelemetryTool(unittest.TestCase):
    """Test suite for local Ollama vision extraction and strict JSON fence stripping."""

    def test_strip_json_fences_with_markdown_fence(self):
        raw = "```json\n{\"equipment_tag\": \"10-HC-1004\", \"measured_thickness_mm\": 3.12}\n```"
        cleaned = strip_json_fences(raw)
        self.assertEqual(cleaned, '{"equipment_tag": "10-HC-1004", "measured_thickness_mm": 3.12}')

    def test_strip_json_fences_with_conversational_text(self):
        raw = "Here is the extracted telemetry:\n```json\n{\"equipment_tag\": \"10-HC-1004\"}\n```\nHope that helps!"
        cleaned = strip_json_fences(raw)
        self.assertEqual(cleaned, '{"equipment_tag": "10-HC-1004"}')

    def test_strip_json_fences_plain_json(self):
        raw = '{"equipment_tag": "P-101", "measured_thickness_mm": 4.5}'
        self.assertEqual(strip_json_fences(raw), raw)

    @patch("src.tools.ocr_tool.requests.post")
    def test_extract_visual_telemetry_mocked_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": (
                        "```json\n"
                        "{\n"
                        '  "equipment_tag": "10-HC-1004-CS300",\n'
                        '  "measured_thickness_mm": 3.15,\n'
                        '  "design_pressure_bar": 21.5,\n'
                        '  "inspection_notes": "Significant localized wall loss near weld elbow."\n'
                        "}\n"
                        "```"
                    )
                }
            }]
        }
        mock_post.return_value = mock_response

        # Call with mock base64
        result = extract_visual_telemetry("fake_base64_string")
        self.assertEqual(result["equipment_tag"], "10-HC-1004-CS300")
        self.assertEqual(result["measured_thickness_mm"], 3.15)
        self.assertEqual(result["design_pressure_bar"], 21.5)
        self.assertIn("localized wall loss", result["inspection_notes"])
        self.assertIsInstance(result["measured_thickness_mm"], float)
        self.assertIsInstance(result["design_pressure_bar"], float)

    def test_extract_visual_telemetry_missing_file_raises_error(self):
        with self.assertRaises(FileNotFoundError):
            extract_visual_telemetry("non_existent_file_path_12345.png")


class TestAirgapMonitor(unittest.TestCase):
    """Test suite for live air-gap network throughput sampling."""

    def test_get_airgap_status_structure(self):
        status = get_airgap_status(sample_interval=0.05)
        self.assertIsInstance(status, dict)
        self.assertIn("outbound_kb_s", status)
        self.assertIn("is_airgapped", status)
        self.assertIn("status", status)
        self.assertIsInstance(status["outbound_kb_s"], float)
        self.assertIsInstance(status["is_airgapped"], bool)
        self.assertIsInstance(status["status"], str)

    @patch("psutil.net_io_counters")
    def test_get_airgap_status_zero_egress(self, mock_net):
        # Return identical counters -> delta is 0
        counter = MagicMock()
        counter.bytes_sent = 100000
        mock_net.return_value = counter

        status = get_airgap_status(sample_interval=0.01)
        self.assertEqual(status["outbound_kb_s"], 0.0)
        self.assertTrue(status["is_airgapped"])
        self.assertEqual(status["status"], "AIR-GAPPED (0.0 KB/s)")


class TestFastAPISovereignEndpoints(unittest.TestCase):
    """Test suite for FastAPI endpoints serving air-gap status and router."""

    def setUp(self):
        self.client = TestClient(app)

    def test_api_airgap_status_endpoint(self):
        response = self.client.get("/api/airgap-status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("outbound_kb_s", data)
        self.assertIn("is_airgapped", data)
        self.assertIn("status", data)

    def test_api_auto_select_model_endpoint(self):
        # Multimodal Vision
        res_vis = self.client.get("/api/auto-select-model?prompt=Review%20scanned%20P%26ID%20drawing")
        self.assertEqual(res_vis.status_code, 200)
        data_vis = res_vis.json()
        self.assertEqual(data_vis["selected_model"], SOVEREIGN_VISION_MODEL)
        self.assertEqual(data_vis["task_type"], "MULTIMODAL_VISION")

        # Analytical Reasoning
        res_ana = self.client.get("/api/auto-select-model?prompt=Calculate%20retirement%20thickness%20under%20API%20570")
        self.assertEqual(res_ana.status_code, 200)
        data_ana = res_ana.json()
        self.assertEqual(data_ana["selected_model"], SOVEREIGN_ANALYTICAL_MODEL)
        self.assertEqual(data_ana["task_type"], "ANALYTICAL_REASONING")

    def test_api_models_status_endpoint(self):
        response = self.client.get("/api/models-status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("ollama_online", data)
        self.assertIn("all_required_models_ready", data)
        self.assertIn("models", data)
        self.assertIn("missing_models", data)
        self.assertIn("zero_wan_egress", data)
        self.assertTrue(data["zero_wan_egress"])
        self.assertEqual(data["airgap_status"], "SECURE")

    @patch("requests.get")
    def test_api_models_status_mocked_installed(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "models": [
                {"name": "qwen2.5vl:3b"},
                {"name": "qwen2.5:7b"}
            ]
        }
        mock_get.return_value = mock_resp

        response = self.client.get("/api/models-status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ollama_online"])
        self.assertTrue(data["all_required_models_ready"])
        self.assertEqual(len(data["missing_models"]), 0)
        self.assertEqual(data["models"]["vision"]["status"], "READY")
        self.assertEqual(data["models"]["analytical"]["status"], "READY")


class TestSovereignOfflineAdvisory(unittest.TestCase):
    """Test suite ensuring zero cloud fallback and clean sovereign local advisory notices."""

    @patch("requests.post")
    def test_llm_gateway_advisory_when_model_404(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_post.return_value = mock_resp

        # Call llm_gateway in local mode
        from src.agent.llm_client import llm_gateway
        output = llm_gateway.call_model("reasoning-engine", "Hello, audit this pipe")
        self.assertIn("[SOVEREIGN LOCAL ADVISORY: Model not yet pulled locally]", output)
        self.assertIn("ollama pull", output)

    @patch("requests.post")
    def test_extract_visual_telemetry_advisory_when_model_404(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_post.return_value = mock_resp

        with self.assertRaises(RuntimeError) as ctx:
            extract_visual_telemetry("fake_image_base64")
        self.assertIn("[SOVEREIGN LOCAL ADVISORY: Model not yet pulled locally]", str(ctx.exception))
        self.assertIn("ollama pull qwen2.5vl:3b", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
