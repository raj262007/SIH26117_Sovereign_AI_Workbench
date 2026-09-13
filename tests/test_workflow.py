"""
End-to-End Integration Test for Sovereign Agentic AI Workbench Workflow.
"""

import os
import unittest
from src.agent.graph import run_workbench_workflow
from src.utils.file_manager import INPUTS_DIR

class TestEndToEndWorkflow(unittest.TestCase):

    def test_full_refinery_inspection_pipeline(self):
        sample_file = os.path.join(INPUTS_DIR, "Piping_UT_Scan_104.txt")
        self.assertTrue(os.path.exists(sample_file))

        result = run_workbench_workflow(
            user_query="Inspect scanned UT piping measurements and verify compliance with API 570",
            file_path=sample_file
        )

        # Verification of state machine execution
        self.assertEqual(result["task_type"], "vision")
        self.assertEqual(result["selected_model"], "vision-engine")
        self.assertEqual(result["calculation_status"], "FAIL - CRITICAL BREACH")
        self.assertIsNotNone(result["generated_report_path"])
        self.assertTrue(os.path.exists(result["generated_report_path"]))
        self.assertGreater(len(result["execution_logs"]), 3)

        # Agentic Loop Verification
        self.assertGreater(len(result["plan"]), 2)
        self.assertGreater(len(result["completed_steps"]), 2)
        self.assertGreater(len(result["retrieved_context"]), 0)
        self.assertIn("docx", result["deliverables"])
        self.assertIn("xlsx", result["deliverables"])
        self.assertIn("pptx", result["deliverables"])
        self.assertTrue(os.path.exists(result["deliverables"]["pptx"]))

    def test_custom_rg_series_inspection_pipeline(self):
        import tempfile
        rg_content = """REFINERY PIPING INSPECTION REPORT - ULTRASONIC THICKNESS (UT) MEASUREMENTS
Report ID: UT-SCAN-2026-ARDS-RECYCLE-GAS
Facility: National Petrochemical Complex / ARDS-1
Applicable Standards: API 570 / ASME B31.3

PIPE SPECIFICATION & SERVICE:
Line Identifier: 12"-RG-3301-CS-NACE (High-Pressure Sour Hydrogen Recycle Gas)
Nominal Original Wall Thickness: 10.31 mm

MINIMUM REGULATORY THRESHOLDS (API 570):
Minimum Structural Retirement Thickness (T_min): 3.60 mm
Mandatory Corrosion Safety Allowance (Margin): 0.90 mm
Critical Retirement Threshold (T_threshold = T_min + Margin): 4.50 mm

ULTRASONIC THICKNESS (UT) MEASUREMENT POINTS:
Point ID   Location Description                 Nominal (mm)  Prev 2024 (mm)  Measured (mm)  Condition
---------------------------------------------------------------------------------------------------------
RG-01      Absorber Tower Overhead Nozzle       10.31         9.80            9.50           ACCEPTABLE
RG-02      Lean Amine Contactor Tie-In Spool    10.31         7.20            5.10           MONITOR
RG-03      Compressor 2nd Stage Suction Tee     10.31         5.20            4.15           ACTION REQ
RG-04      Knockout Drum Inlet Reducer          10.31         8.40            7.90           ACCEPTABLE
RG-05      High-Pressure Bypass Orifice Flange  10.31         4.80            3.40           CRITICAL
"""
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write(rg_content)
            rg_path = f.name

        try:
            result = run_workbench_workflow(
                user_query="Verify ultrasonic piping thickness scan and issue executive memo per API 570",
                file_path=rg_path
            )

            self.assertEqual(result["calculation_status"], "FAIL - CRITICAL BREACH")
            self.assertIn("12\"-RG-3301-CS-NACE", result["sandbox_output"])
            self.assertIn("RG-05", result["sandbox_output"])
            self.assertIn("CRITICAL BREACH", result["final_memo_text"])
            self.assertIn("RG-05", result["final_memo_text"])
            self.assertIn("RG-03", result["final_memo_text"])
        finally:
            if os.path.exists(rg_path):
                os.remove(rg_path)


if __name__ == "__main__":
    unittest.main()


