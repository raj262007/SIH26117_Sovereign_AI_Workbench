"""
Unit tests for the Dynamic Task Classifier & Model Router.
"""

import unittest
from src.agent.router import route_task

class TestModelRouter(unittest.TestCase):

    def test_vision_routing_by_file_extension(self):
        task_type, engine, _ = route_task("Inspect this diagram", "drawing_104.pdf")
        self.assertEqual(task_type, "vision")
        self.assertEqual(engine, "vision-engine")

    def test_vision_routing_by_query_intent(self):
        task_type, engine, _ = route_task("Look at the scanned P&ID drawing and find valves")
        self.assertEqual(task_type, "vision")
        self.assertEqual(engine, "vision-engine")

    def test_coding_routing_by_query(self):
        task_type, engine, _ = route_task("Calculate the piping retirement thickness using Python formula")
        self.assertEqual(task_type, "coding")
        self.assertEqual(engine, "coding-engine")

    def test_reasoning_routing_by_query(self):
        task_type, engine, _ = route_task("Draft an executive compliance memo for the board per SOP")
        self.assertEqual(task_type, "reasoning")
        self.assertEqual(engine, "reasoning-engine")

    def test_two_stage_classifier_model_registry(self):
        from src.agent.router import classify_two_stage, MODEL_REGISTRY
        
        # Test vision_document classification
        tt, cfg, rat = classify_two_stage("Analyze scanned P&ID drawing", "piping.pdf")
        self.assertEqual(tt, "vision_document")
        self.assertIn("endpoint", cfg)
        self.assertEqual(cfg["model"], "qwen2.5-vl-7b")

        # Test coding classification
        tt, cfg, rat = classify_two_stage("Verify corrosion rate using python script", "calc.py")
        self.assertEqual(tt, "coding")
        self.assertEqual(cfg["model"], "qwen2.5-coder-7b")

        # Test document_qa classification
        tt, cfg, rat = classify_two_stage("Review regulatory compliance memo per API 570 clause 7")
        self.assertEqual(tt, "document_qa")
        self.assertEqual(cfg["model"], "qwen3-8b")

        # Verify all registry keys exist
        for key in ["coding", "document_qa", "vision_document", "general_reasoning"]:
            self.assertIn(key, MODEL_REGISTRY)
            self.assertIn("endpoint", MODEL_REGISTRY[key])

if __name__ == "__main__":
    unittest.main()

