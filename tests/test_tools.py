"""
Unit tests for OCR, Sandboxed Code Execution, and Report Generation tools.
"""

import os
import unittest
from src.tools.ocr_tool import parse_inspection_document
from src.tools.sandbox_tool import execute_sandboxed_python
from src.tools.report_tool import generate_inspection_memo, generate_inspection_spreadsheet
from src.utils.file_manager import INPUTS_DIR, OUTPUTS_DIR

class TestWorkbenchTools(unittest.TestCase):

    def setUp(self):
        self.sample_file = os.path.join(INPUTS_DIR, "Piping_UT_Scan_104.txt")

    def test_ocr_parser(self):
        self.assertTrue(os.path.exists(self.sample_file))
        data = parse_inspection_document(self.sample_file)
        self.assertEqual(data["metadata"]["line_number"], "10\"-HC-1004-CS300")
        self.assertEqual(data["thresholds"]["t_min"], 2.80)
        self.assertEqual(data["thresholds"]["margin"], 0.50)
        self.assertGreaterEqual(len(data["measurement_points"]), 1)

    def test_sandbox_execution(self):
        code = """
t_actual = 3.20
t_threshold = 3.30
status = "FAIL - CRITICAL BREACH" if t_actual < t_threshold else "PASS"
print(status)
"""
        res = execute_sandboxed_python(code)
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "FAIL - CRITICAL BREACH")
        self.assertIn("FAIL - CRITICAL BREACH", res["stdout"])

    def test_report_generation(self):
        data = parse_inspection_document(self.sample_file)
        sandbox_res = {"status": "FAIL - CRITICAL BREACH", "stdout": "Deficit: -0.10 mm", "duration_sec": 0.02}
        memo_path = generate_inspection_memo(data, sandbox_res, filename="Test_Memo.docx")
        self.assertTrue(os.path.exists(memo_path))
        self.assertTrue(memo_path.endswith(".docx"))

        xlsx_path = generate_inspection_spreadsheet(data, filename="Test_Log.xlsx")
        self.assertTrue(os.path.exists(xlsx_path))
        self.assertTrue(xlsx_path.endswith(".xlsx"))

        # Test Executive PPTX presentation generation
        from src.tools.report_tool import generate_executive_presentation
        pptx_path = generate_executive_presentation(data, sandbox_res, filename="Test_Brief.pptx")
        self.assertTrue(os.path.exists(pptx_path))
        self.assertTrue(pptx_path.endswith(".pptx"))

    def test_sovereign_rag_standards(self):
        from src.tools.rag_tool import query_standards
        chunks = query_standards("retirement threshold 3.30 mm API 570")
        self.assertGreaterEqual(len(chunks), 1)
        first = chunks[0]
        self.assertIn("text", first)
        self.assertIn("source_doc", first)
        self.assertIn("page", first)
        self.assertIn("clause", first)
        self.assertEqual(first["standard"], "API 570")

if __name__ == "__main__":
    unittest.main()

